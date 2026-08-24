from rest_framework.decorators import api_view, permission_classes, parser_classes, throttle_classes
from rest_framework.response import Response
from rest_framework import status, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend

from django.db.models import Count, Q, Sum
from django.core.cache import cache

import logging

logger = logging.getLogger("application")
error_logger = logging.getLogger("django.request")
ai_logger = logging.getLogger("ai_events")


import os
import re

import razorpay
from django.conf import settings
from decimal import Decimal
from uuid import uuid4

from PyPDF2 import PdfReader
from docx import Document

from reportlab.pdfgen import canvas
from django.http import HttpResponse
from .utils import (
    extract_skills,
    extract_experience,
    extract_education,
)

from .services import (calculate_ats_score, auto_shortlist, AIBridgeService,)
from .email_utils import send_notification_email
from .reminder_service import send_interview_reminders


from .eligibility import check_candidate_eligibility
from django.utils import timezone
from datetime import datetime, timedelta

from .serializers import (
    UserSignupSerializer,
    CandidateProfileSerializer,
    CandidateListSerializer,
    EmployerProfileSerializer,
    JobSerializer,
    ApplicationSerializer,
    AuditLogSerializer,
    QuestionTemplateSerializer,
    QuestionFlowSerializer,
    InterviewStateSerializer,
    AIAnswerSerializer,
    AvailabilitySlotSerializer,
    InterviewScheduleSerializer,
)
from .permissions import IsAdminUser, IsEmployerUser, IsCandidateUser, HasActiveSubscription, HasAIAnalyticsAccess, IsPremiumEmployer
from .models import (
    CandidateProfile,
    EmployerProfile,
    Job,
    Application,
    CustomUser,
    AuditLog,
    AICall,
    QuestionTemplate,
    QuestionFlow,
    InterviewState,
    AIAnswer,
    AIQuestion,
    AIInterviewSession,
    AvailabilitySlot,
    InterviewSchedule,
    InterviewReminder,
    SubscriptionPlan,
    UserSubscription,
    PaymentTransaction,
    BillingHistory,
)

@api_view(['POST'])
def signup(request):
    logger.info(f"Signup request received from {request.META.get('REMOTE_ADDR')}")
    serializer = UserSignupSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    return Response({
        "message": "Welcome!",
        "username": request.user.username,
        "email": request.user.email,
        "role": request.user.role,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_dashboard(request):
    return Response({"message": "Welcome Admin"})

@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def approve_employer(request, employer_id):

    try:
        employer = CustomUser.objects.get(
            id=employer_id,
            role="Employer"
        )
    except CustomUser.DoesNotExist:
        return Response(
            {"message": "Employer not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    employer.is_verified = True
    employer.save()

    AuditLog.objects.create(
        admin=request.user,
        action=f"Approved employer {employer.username}",
        ip_address=request.META.get("REMOTE_ADDR")
    )

    return Response(
        {"message": "Employer approved successfully"}
    )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def block_user(request, user_id):

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            {"message": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    user.is_active = False
    user.save()

    AuditLog.objects.create(
        admin=request.user,
        action=f"Blocked user {user.username}",
        ip_address=request.META.get("REMOTE_ADDR")
    )

    return Response(
        {"message": "User blocked successfully"}
    )  
    
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def unblock_user(request, user_id):

    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            {"message": "User not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    user.is_active = True
    user.save()

    AuditLog.objects.create(
        admin=request.user,
        action=f"Unblocked user {user.username}"
    )

    return Response(
        {"message": "User unblocked successfully"}
    )  

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def audit_logs(request):

    logs = AuditLog.objects.all().order_by('-created_at')

    serializer = AuditLogSerializer(logs, many=True)

    return Response(serializer.data)      

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def employer_dashboard(request):
    return Response({"message": "Welcome Employer"})


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def candidate_dashboard(request):

    candidate = request.user

    applied_jobs = Application.objects.filter(
        candidate=candidate
    ).count()

    interviews = Application.objects.filter(
        candidate=candidate,
        status="Interview Scheduled"
    ).count()

    selected = Application.objects.filter(
        candidate=candidate,
        status="Selected"
    ).count()

    rejected = Application.objects.filter(
        candidate=candidate,
        status="Rejected"
    ).count()

    return Response({
        "candidate": candidate.username,
        "applied_jobs": applied_jobs,
        "interviews": interviews,
        "selected": selected,
        "rejected": rejected
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def recommended_jobs(request):

    try:
        profile = CandidateProfile.objects.get(
            user=request.user,
            is_deleted=False
        )
    except CandidateProfile.DoesNotExist:
        return Response(
            {"message": "Candidate profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    candidate_skills = [
        skill.strip().lower()
        for skill in profile.skills.split(",")
    ]

    jobs = Job.objects.filter(status=True)

    recommended = []

    for job in jobs:
        job_skills = [
            skill.strip().lower()
            for skill in job.skills.split(",")
        ]

        if any(skill in job_skills for skill in candidate_skills):
            recommended.append(job)

    serializer = JobSerializer(recommended, many=True)

    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def match_percentage(request, job_id):

    try:
        profile = CandidateProfile.objects.get(
            user=request.user,
            is_deleted=False
        )
    except CandidateProfile.DoesNotExist:
        return Response(
            {"message": "Candidate profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        job = Job.objects.get(id=job_id, status=True)
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    score = calculate_ats_score(profile, job)

    return Response({
        "candidate": request.user.username,
        "job": job.title,
        "match_percentage": score
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def ranked_candidates(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    applications = Application.objects.filter(job=job)

    ranked_list = []

    for application in applications:

        try:
            profile = CandidateProfile.objects.get(
                user=application.candidate,
                is_deleted=False
            )
        except CandidateProfile.DoesNotExist:
            continue

        score = calculate_ats_score(profile, job)

        ranked_list.append({
            "candidate": application.candidate.username,
            "match_percentage": score
        })

    ranked_list = sorted(
        ranked_list,
        key=lambda x: x["match_percentage"],
        reverse=True
    )

    return Response(ranked_list)        

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def application_timeline(request, application_id):

    try:
        application = Application.objects.get(
            id=application_id,
            candidate=request.user
        )
    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    return Response({
        "application_id": application.id,
        "job": application.job.title,
        "status": application.status,
        "applied_date": application.applied_date,
        "last_updated": application.updated_at
    })


@api_view(['POST', 'GET', 'PUT', 'DELETE'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated, IsCandidateUser])
def candidate_profile(request):

    if request.method == "POST":
        serializer = CandidateProfileSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    profile = CandidateProfile.objects.filter(
        user=request.user,
        is_deleted=False
    ).first()

    if not profile:
        return Response(
            {"message": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        serializer = CandidateProfileSerializer(profile)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = CandidateProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():

            if 'resume' in request.FILES and profile.resume:
                profile.resume.delete(save=False)

            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        profile.is_deleted = True
        profile.save()
        return Response({"message": "Candidate profile deleted successfully"})


@api_view(['POST', 'GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def employer_profile(request):

    if request.method == "POST":
        serializer = EmployerProfileSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    profile = EmployerProfile.objects.filter(
        user=request.user,
        is_deleted=False
    ).first()

    if not profile:
        return Response(
            {"message": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if request.method == "GET":
        serializer = EmployerProfileSerializer(profile)
        return Response(serializer.data)

    if request.method == "PUT":
        serializer = EmployerProfileSerializer(
            profile,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if request.method == "DELETE":
        profile.is_deleted = True
        profile.save()
        return Response({"message": "Employer profile deleted successfully"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def candidate_list(request):

    queryset = CandidateProfile.objects.select_related('user').filter(
        is_deleted=False
    ).order_by('id')

    search = request.GET.get("search")

    if search:
        queryset = queryset.filter(
            user__username__icontains=search
        )

    paginator = PageNumberPagination()
    paginator.page_size = 5

    result = paginator.paginate_queryset(queryset, request)

    serializer = CandidateListSerializer(result, many=True)

    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmployerUser, HasActiveSubscription])
def create_job(request):

    # Check active subscription
    subscription = (
        UserSubscription.objects
        .filter(
            user=request.user,
            status="ACTIVE"
        )
        .select_related("plan")
        .first()
    )

    if not subscription:
        return Response(
            {
                "message": "An active subscription is required to create jobs."
            },
            status=status.HTTP_403_FORBIDDEN
        )

    plan = subscription.plan

    # Check job posting limit
    if not plan.unlimited_job_posts:

        current_job_count = Job.objects.filter(
            employer=request.user
        ).count()

        if current_job_count >= plan.job_post_limit:
            return Response(
                {
                    "message": "Job posting limit reached.",
                    "plan": plan.name,
                    "job_post_limit": plan.job_post_limit,
                    "current_job_count": current_job_count
                },
                status=status.HTTP_403_FORBIDDEN
            )

    serializer = JobSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(employer=request.user)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def apply_job(request, job_id):

    try:
        job = Job.objects.get(id=job_id, status=True)
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found or inactive"},
            status=status.HTTP_404_NOT_FOUND
        )

    
    if Application.objects.filter(
        candidate=request.user,
        job=job
    ).exists():
        return Response(
            {"message": "You have already applied for this job"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get candidate profile
    profile = CandidateProfile.objects.filter(
        user=request.user,
        is_deleted=False
    ).first()

    if not profile:
        return Response(
            {"message": "Candidate profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if not profile.resume:
        return Response(
            {"message": "Please upload your resume before applying"},
            status=status.HTTP_400_BAD_REQUEST
        )

    application = Application.objects.create(
        candidate=request.user,
        job=job,
        resume_snapshot=profile.resume,
    )

    print("Sending email...")

    send_notification_email(
    subject="Job Application Submitted",
    message=f"Hi {request.user.username},\n\nYour application for '{job.title}' has been submitted successfully.\n\nThank you for applying!",
    recipient_email="abinsabu2001@gmail.com",
    )


    serializer = ApplicationSerializer(application)

    return Response(
        {
            "message": "Job applied successfully",
            "data": serializer.data
        },
        status=status.HTTP_201_CREATED
    )
    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def my_applications(request):

    applications = (
    Application.objects
    .select_related("job", "candidate")
    .filter(candidate=request.user)
    .order_by("-applied_date")
)

    serializer = ApplicationSerializer(applications, many=True)

    return Response(serializer.data)

@api_view(['GET'])
def job_list(request):

    jobs = Job.objects.filter(status=True).order_by('-created_at')

    # Skill filter
    skill = request.GET.get('skill')
    if skill:
        jobs = jobs.filter(skills__icontains=skill)

    # Experience filter
    experience = request.GET.get('experience')
    if experience:
        jobs = jobs.filter(experience=experience)

    # Location filter
    location = request.GET.get('location')
    if location:
        jobs = jobs.filter(location__icontains=location)

    # Job Type filter
    job_type = request.GET.get('job_type')
    if job_type:
        jobs = jobs.filter(job_type=job_type)

    # Salary Range
    salary_min = request.GET.get('salary_min')
    salary_max = request.GET.get('salary_max')

    if salary_min:
        jobs = jobs.filter(salary_min__gte=salary_min)

    if salary_max:
        jobs = jobs.filter(salary_max__lte=salary_max)

    # Search
    search = request.GET.get('search')

    if search:
        jobs = jobs.filter(
            title__icontains=search
        ) | Job.objects.filter(
            description__icontains=search
        ) | Job.objects.filter(
            skills__icontains=search
        )

    paginator = PageNumberPagination()
    paginator.page_size = 5

    result = paginator.paginate_queryset(jobs, request)

    serializer = JobSerializer(result, many=True)

    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
def featured_jobs(request):
    jobs = Job.objects.filter(
        status=True,
        featured=True
    ).order_by('-created_at')

    serializer = JobSerializer(jobs, many=True)

    return Response(serializer.data)

@api_view(['GET'])
def latest_jobs(request):

    jobs = Job.objects.filter(
        status=True
    ).order_by('-created_at')[:5]

    serializer = JobSerializer(jobs, many=True)

    return Response(serializer.data)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def update_application_status(request, application_id):

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    new_status = request.data.get("status")

    if new_status not in [
        "Applied",
        "Shortlisted",
        "Interview Scheduled",
        "Rejected",
        "Selected",
    ]:
        return Response(
            {"message": "Invalid status"},
            status=status.HTTP_400_BAD_REQUEST
        )

    allowed_transitions = {
        "Applied": ["Shortlisted", "Rejected"],
        "Shortlisted": ["Interview Scheduled", "Rejected"],
        "Interview Scheduled": ["Selected", "Rejected"],
        "Rejected": [],
        "Selected": [],
    }

    current_status = application.status

    if new_status not in allowed_transitions[current_status]:
        return Response(
            {
                "message": f"Cannot change status from {current_status} to {new_status}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    application.status = new_status
    application.save()

    # Auto trigger AI call for eligible candidates
    if new_status == "Shortlisted":

        try:
            profile = CandidateProfile.objects.get(
                user=application.candidate,
                is_deleted=False
            )

            application.ats_score = calculate_ats_score(
                profile,
                application.job
            )
            application.save()

        except CandidateProfile.DoesNotExist:
            pass

        if check_candidate_eligibility(application):
            AICall.objects.get_or_create(
                application=application,
                defaults={
                    "scheduled_time": timezone.now() + timedelta(minutes=30),
                    "status": "QUEUED",
                }
            )

        send_notification_email(
            subject="Application Shortlisted",
            message=f"Hi {application.candidate.username},\n\n"
                    f"Congratulations! You have been shortlisted for '{application.job.title}'.",
            recipient_email="abinsabu2001@gmail.com",
        )

    elif new_status == "Rejected":

        send_notification_email(
            subject="Application Rejected",
            message=f"Hi {application.candidate.username},\n\n"
                    f"We regret to inform you that your application for '{application.job.title}' has been rejected.",
            recipient_email="abinsabu2001@gmail.com",
        )

    return Response(
        {
            "message": "Application status updated successfully",
            "status": application.status
        }
    )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def employer_jobs(request):

    jobs = Job.objects.filter(
        employer=request.user
    ).order_by('-created_at')

    serializer = JobSerializer(jobs, many=True)

    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def edit_job(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = JobSerializer(
        job,
        data=request.data,
        partial=True
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def close_job(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    job.status = False
    job.save()

    return Response(
        {"message": "Hiring closed successfully"}
    )    

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def applicant_list(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    applications = (
    Application.objects
    .select_related("candidate", "job")
    .filter(job=job)
)
    serializer = ApplicationSerializer(applications, many=True)

    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def filter_applicants(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    status_filter = request.GET.get("status")

    applications = (
    Application.objects
    .select_related("candidate", "job")
    .filter(job=job)
)
    if status_filter:
        applications = applications.filter(status=status_filter)

    serializer = ApplicationSerializer(applications, many=True)

    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def search_applicants(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    applications = (
    Application.objects
    .select_related("candidate", "job")
    .filter(job=job)
)

    search = request.GET.get("search")

    if search:
        applications = applications.filter(
            candidate__username__icontains=search
        )

    serializer = ApplicationSerializer(applications, many=True)

    return Response(serializer.data)    

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def job_analytics(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    applications = Application.objects.filter(job=job)

    total = applications.count()

    applied = applications.filter(
        status="Applied"
    ).count()

    shortlisted = applications.filter(
        status="Shortlisted"
    ).count()

    interviewed = applications.filter(
        status="Interview Scheduled"
    ).count()

    selected = applications.filter(
        status="Selected"
    ).count()

    rejected = applications.filter(
        status="Rejected"
    ).count()

    # Conversion ratios
    shortlist_ratio = 0
    interview_ratio = 0
    selection_ratio = 0

    if total > 0:
        shortlist_ratio = round(
            (shortlisted / total) * 100, 2
        )

    if shortlisted > 0:
        interview_ratio = round(
            (interviewed / shortlisted) * 100, 2
        )

    if interviewed > 0:
        selection_ratio = round(
            (selected / interviewed) * 100, 2
        )

    return Response({
        "job": job.title,
        "job_id": job.id,

        "funnel": {
            "applied": applied,
            "shortlisted": shortlisted,
            "interviewed": interviewed,
            "selected": selected,
            "rejected": rejected
        },

        "conversion_ratios": {
            "application_to_shortlist": f"{shortlist_ratio}%",
            "shortlist_to_interview": f"{interview_ratio}%",
            "interview_to_selection": f"{selection_ratio}%"
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def recruiter_funnel_analytics(request):

    cache_key = f"recruiter_funnel_{request.user.id}"

    cached_data = cache.get(cache_key)

    if cached_data:
        return Response(cached_data)

    applications = Application.objects.filter(
        job__employer=request.user
    )

    funnel_data = {
        "funnel": {
            "applied": applications.filter(
                status="Applied"
            ).count(),

            "shortlisted": applications.filter(
                status="Shortlisted"
            ).count(),

            "interviewed": applications.filter(
                status="Interview Scheduled"
            ).count(),

            "selected": applications.filter(
                status="Selected"
            ).count()
        }
    }

    cache.set(
        cache_key,
        funnel_data,
        timeout=60
    )

    return Response(funnel_data)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsCandidateUser])
def parse_resume(request):

    profile = CandidateProfile.objects.filter(
        user=request.user,
        is_deleted=False
    ).first()

    if not profile or not profile.resume:
        return Response(
            {"message": "Resume not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    file_path = profile.resume.path
    extension = os.path.splitext(file_path)[1].lower()

    text = ""

    try:
        if extension == ".pdf":
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text

        elif extension == ".docx":
            document = Document(file_path)
            for para in document.paragraphs:
                text += para.text + "\n"

        else:
            return Response(
                {"message": "Unsupported file format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Clean extracted text
        cleaned_text = re.sub(r"\s+", " ", text).strip()
        skills = extract_skills(cleaned_text)
        experience = extract_experience(cleaned_text)
        education = extract_education(cleaned_text)

        return Response({
            "message": "Resume parsed successfully",
            "text": cleaned_text,
            "skills": skills,
            "experience": experience,
            "education": education
        }) 

    except Exception as e:
        error_logger.exception("Error while parsing resume")
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )  

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def auto_shortlist_candidates(request, job_id):

    try:
        job = Job.objects.get(
            id=job_id,
            employer=request.user
        )
    except Job.DoesNotExist:
        return Response(
            {"message": "Job not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    applications = Application.objects.filter(job=job)

    for application in applications:

        try:
            profile = CandidateProfile.objects.get(
                user=application.candidate,
                is_deleted=False
            )
        except CandidateProfile.DoesNotExist:
            continue

        application.ats_score = calculate_ats_score(
            profile,
            job
        )

        application.save()

        auto_shortlist(application)

    return Response({
        "message": "Auto shortlisting completed successfully"
    })



@api_view(['GET'])
def test_email(request):
    send_notification_email(
        subject="Django Email Test",
        message="Congratulations! Your email notification is working.",
        recipient_email="abinsabu2001@gmail.com"
    )

    return Response({
        "message": "Email sent successfully"
    })    



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ai_bridge_test(request):
    """
    Test AI Bridge Service.
    """

    try:
        ai_service = AIBridgeService()

        result = ai_service.trigger_voice_call("9567879284")
        ai_logger.info("AI bridge voice call triggered successfully")

        return Response(result)

    except Exception as e:
        ai_logger.exception("AI bridge voice call failed")

        return Response(
            {
                "status": "failed",
                "message": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )    

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def question_templates(request):

    if request.method == "POST":

        serializer = QuestionTemplateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    questions = QuestionTemplate.objects.filter(
        is_active=True
    )

    serializer = QuestionTemplateSerializer(
        questions,
        many=True
    )

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def next_question(request):

    candidate = request.user

    answer = request.data.get("answer")

    state, created = InterviewState.objects.get_or_create(
        candidate=candidate
    )

    if created or state.current_question is None:

        first_question = QuestionTemplate.objects.filter(
            is_active=True
        ).order_by("id").first()

        state.current_question = first_question
        state.save()

        return Response({
            "question": first_question.question
        })

    try:

        flow = QuestionFlow.objects.get(
            current_question=state.current_question,
            answer_value=answer
        )

        state.current_question = flow.next_question
        state.last_answer = answer
        state.save()

        return Response({
            "question": flow.next_question.question
        })

    except QuestionFlow.DoesNotExist:

        state.completed = True
        state.save()

        return Response({
            "message": "Interview Completed"
        })    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate_answer(request):

    answer_id = request.data.get("answer_id")

    try:
        answer = AIAnswer.objects.get(id=answer_id)
    except AIAnswer.DoesNotExist:
        return Response(
            {"message": "Answer not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    text = answer.answer_text.lower()

    relevance = min(len(text.split()) * 2, 100)

    completeness = 100 if len(text) > 100 else len(text)

    keywords = [
        "python",
        "django",
        "api",
        "database",
        "sql"
    ]

    keyword_matches = sum(
        1 for word in keywords if word in text
    )

    keyword_score = (keyword_matches / len(keywords)) * 100

    final_score = (
        relevance * 0.4 +
        completeness * 0.4 +
        keyword_score * 0.2
    )

    answer.relevance_score = relevance
    answer.completeness_score = completeness
    answer.keyword_score = keyword_score
    answer.answer_score = final_score
    answer.confidence = final_score
    answer.annotations = "Answer evaluated successfully."

    answer.save()

    serializer = AIAnswerSerializer(answer)

    return Response(serializer.data)   



@api_view(["POST"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def create_availability_slot(request):

    serializer = AvailabilitySlotSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(employer=request.user)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def schedule_interview(request):

    application_id = request.data.get("application")
    slot_id = request.data.get("slot")

    try:
        application = Application.objects.get(id=application_id)
    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        slot = AvailabilitySlot.objects.get(id=slot_id)
    except AvailabilitySlot.DoesNotExist:
        return Response(
            {"message": "Slot not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if slot.is_booked:
        return Response(
            {"message": "This slot is already booked"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if InterviewSchedule.objects.filter(application=application).exists():
        return Response(
            {"message": "Interview already scheduled for this application"},
            status=status.HTTP_400_BAD_REQUEST
        )

    interview = InterviewSchedule.objects.create(
        application=application,
        slot=slot,
        meeting_link=request.data.get("meeting_link", "")
    )

    # Create reminder schedules

    interview_start = timezone.make_aware(
        datetime.combine(
            slot.date,
            slot.start_time
        )
    )

    # 24-hour reminder

    InterviewReminder.objects.create(
        interview=interview,
        reminder_type="24_HOURS",
        scheduled_time=interview_start - timedelta(hours=24)
    )

    # 1-hour reminder

    InterviewReminder.objects.create(
        interview=interview,
        reminder_type="1_HOUR",
        scheduled_time=interview_start - timedelta(hours=1)
    )

    slot.is_booked = True
    slot.save()

    application.status = "Interview Scheduled"
    application.save()

    email_status = "Email sent successfully"

    try:
        if application.candidate.email:
            send_notification_email(
                subject="Interview Scheduled",
                message=(
                    f"Hi {application.candidate.username},\n\n"
                    f"Your interview for '{application.job.title}' "
                    f"has been scheduled.\n\n"
                    f"Meeting Link: {interview.meeting_link}\n\n"
                    f"Date: {slot.date}\n"
                    f"Time: {slot.start_time} - {slot.end_time}\n\n"
                    "Best of luck!"
                ),
                recipient_email="abinsabu2001@gmail.com",
            )
        else:
            email_status = "Candidate email not found."

    except Exception as e:
        print("Email Error:", e)
        email_status = f"Email failed: {str(e)}"

    serializer = InterviewScheduleSerializer(interview)

    return Response(
        {
            "message": "Interview scheduled successfully",
            "email_status": email_status,
            "data": serializer.data,
        },
        status=status.HTTP_201_CREATED,
    )
    
@api_view(["PUT"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def reschedule_interview(request, interview_id):

    try:
        interview = InterviewSchedule.objects.get(id=interview_id)
    except InterviewSchedule.DoesNotExist:
        return Response(
            {"message": "Interview not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    new_slot_id = request.data.get("slot")

    try:
        new_slot = AvailabilitySlot.objects.get(id=new_slot_id)
    except AvailabilitySlot.DoesNotExist:
        return Response(
            {"message": "Slot not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if new_slot.is_booked:
        return Response(
            {"message": "Selected slot is already booked"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Free the old slot
    old_slot = interview.slot
    old_slot.is_booked = False
    old_slot.save()

    # Book the new slot
    new_slot.is_booked = True
    new_slot.save()

    # Update interview
    interview.slot = new_slot

    if "meeting_link" in request.data:
        interview.meeting_link = request.data["meeting_link"]

    interview.save()

    send_notification_email(
        subject="Interview Rescheduled",
        message=(
            f"Hi {interview.application.candidate.username},\n\n"
            f"Your interview has been rescheduled.\n\n"
            f"Date: {new_slot.date}\n"
            f"Time: {new_slot.start_time} - {new_slot.end_time}\n\n"
            f"Meeting Link: {interview.meeting_link}"
        ),
        recipient_email="abinsabu2001@gmail.com",
    )

    serializer = InterviewScheduleSerializer(interview)

    return Response(
        {
            "message": "Interview rescheduled successfully",
            "data": serializer.data,
        }
    )    


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_reminders_api(request):

    try:
        send_interview_reminders()

        return Response({
            "message": "Interview reminders processed successfully."
        })

    except Exception as e:

        return Response(
            {
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )    


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsEmployerUser, HasAIAnalyticsAccess])
def candidate_ai_report(request, application_id):

    try:
        application = Application.objects.select_related(
            "candidate",
            "job"
        ).get(
            id=application_id,
            job__employer=request.user
        )

    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # ATS score
    ats_score = application.ats_score

    # AI interview data
    ai_call_score = 0
    answer_scores = []
    answer_count = 0

    try:
        session = application.interview_session

        answers = AIAnswer.objects.filter(
            interview_session=session
        )

        answer_count = answers.count()

        for answer in answers:
            answer_scores.append(answer.answer_score)

        if answer_scores:
            ai_call_score = round(
                sum(answer_scores) / len(answer_scores),
                2
            )

    except AIInterviewSession.DoesNotExist:
        pass

    # Candidate strengths and risks
    strengths = []
    risks = []
    if ats_score >= 80:
        strengths.append("Excellent ATS/job profile match")
    elif ats_score >= 70:
        strengths.append("Good ATS/job profile match")
    else:
        risks.append("ATS/job profile match needs improvement")

    if ai_call_score >= 80:
        strengths.append("Excellent AI interview performance")
    elif ai_call_score >= 70:
        strengths.append("Good AI interview performance")
    elif ai_call_score > 0:
        risks.append("AI interview performance needs improvement")
    else:
        risks.append("AI interview score not available")

    # Overall score
    overall_score = round(
        (ats_score + ai_call_score) / 2,
        2
    ) if ai_call_score > 0 else ats_score

    # Recruiter-friendly summary
    summary = (
        f"{application.candidate.username} has an ATS score of "
        f"{ats_score} and an AI interview score of "
        f"{ai_call_score}. Overall evaluation score is "
        f"{overall_score}."
    )

    report = {
        "candidate": application.candidate.username,
        "application_id": application.id,
        "job": application.job.title,

            "scores": {
            "ats_score": ats_score,
            "ai_call_score": ai_call_score,
            "overall_score": overall_score,
            "interview_answers_evaluated": answer_count
        },

        "strengths": strengths,
        "risks": risks,

        "summary": summary,

        "report_status": "Generated"
    }

    return Response(report)   


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsEmployerUser, HasAIAnalyticsAccess])
def candidate_report_summary(request, application_id):

    try:
        application = Application.objects.select_related(
            "candidate",
            "job"
        ).get(
            id=application_id,
            job__employer=request.user
        )

    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    ats_score = application.ats_score

    ai_call_score = 0
    answer_count = 0

    try:
        session = application.interview_session

        answers = AIAnswer.objects.filter(
            interview_session=session
        )

        answer_count = answers.count()

        if answer_count > 0:
            total_score = sum(
                answer.answer_score for answer in answers
            )

            ai_call_score = round(
                total_score / answer_count,
                2
            )

    except AIInterviewSession.DoesNotExist:
        pass

    if ai_call_score > 0:
        overall_score = round(
            (ats_score + ai_call_score) / 2,
            2
        )
    else:
        overall_score = ats_score

    if overall_score >= 80:
        recommendation = "Highly Recommended"
    elif overall_score >= 60:
        recommendation = "Recommended for Review"
    else:
        recommendation = "Needs Improvement"

    return Response({
        "candidate": application.candidate.username,
        "job": application.job.title,
        "ats_score": ats_score,
        "ai_call_score": ai_call_score,
        "overall_score": overall_score,
        "interview_answers_evaluated": answer_count,
        "recommendation": recommendation,
        "summary": (
            f"{application.candidate.username} received an "
            f"overall evaluation score of {overall_score}. "
            f"Recruiter recommendation: {recommendation}."
        )
    })         


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsEmployerUser, HasAIAnalyticsAccess])
def candidate_ai_report_pdf(request, application_id):

    try:
        application = Application.objects.select_related(
            "candidate",
            "job"
        ).get(
            id=application_id,
            job__employer=request.user
        )

    except Application.DoesNotExist:
        return Response(
            {"message": "Application not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    ats_score = application.ats_score

    ai_call_score = 0
    answer_count = 0

    try:
        session = application.interview_session

        answers = AIAnswer.objects.filter(
            interview_session=session
        )

        answer_count = answers.count()

        if answer_count > 0:
            total_score = sum(
                answer.answer_score for answer in answers
            )

            ai_call_score = round(
                total_score / answer_count,
                2
            )

    except AIInterviewSession.DoesNotExist:
        pass

    if ai_call_score > 0:
        overall_score = round(
            (ats_score + ai_call_score) / 2,
            2
        )
    else:
        overall_score = ats_score

    if ats_score >= 70:
        strength = "Good ATS/job profile match"
    else:
        strength = "ATS/job profile match needs improvement"

    if ai_call_score >= 70:
        interview_result = "Good AI interview performance"
    elif ai_call_score > 0:
        interview_result = "AI interview performance needs improvement"
    else:
        interview_result = "AI interview score not available"

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="candidate_report_{application_id}.pdf"'
    )

    pdf = canvas.Canvas(response)

    pdf.setTitle("AI Candidate Evaluation Report")

    pdf.drawString(50, 800, "AI Candidate Evaluation Report")

    pdf.drawString(
        50, 770,
        f"Candidate: {application.candidate.username}"
    )

    pdf.drawString(
        50, 750,
        f"Job: {application.job.title}"
    )

    pdf.drawString(
        50, 710,
        f"ATS Score: {ats_score}"
    )

    pdf.drawString(
        50, 690,
        f"AI Interview Score: {ai_call_score}"
    )

    pdf.drawString(
        50, 670,
        f"Overall Score: {overall_score}"
    )

    pdf.drawString(
        50, 650,
        f"Interview Answers Evaluated: {answer_count}"
    )

    pdf.drawString(50, 610, "Strength / Assessment:")

    pdf.drawString(
        70, 590,
        strength
    )

    pdf.drawString(
        70, 570,
        interview_result
    )

    pdf.drawString(50, 530, "Recruiter Summary:")

    summary = (
        f"{application.candidate.username} received an "
        f"overall evaluation score of {overall_score}."
    )

    pdf.drawString(70, 510, summary)

    pdf.drawString(
        70, 490,
        "This report is intended for recruiter evaluation."
    )

    pdf.save()

    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def recruiter_time_analytics(request):

    now = timezone.now()

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    week_start = today_start - timedelta(
        days=now.weekday()
    )

    month_start = today_start.replace(
        day=1
    )

    applications = Application.objects.filter(
        job__employer=request.user
    )

    today_count = applications.filter(
        applied_date__gte=today_start
    ).count()

    week_count = applications.filter(
        applied_date__gte=week_start
    ).count()

    month_count = applications.filter(
        applied_date__gte=month_start
    ).count()

    return Response({
        "time_based_statistics": {
            "today": today_count,
            "this_week": week_count,
            "this_month": month_count
        }
    })   


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsEmployerUser])
def recruiter_role_analytics(request):

    # Check active subscription
    subscription = (
        UserSubscription.objects
        .filter(
            user=request.user,
            status="ACTIVE"
        )
        .select_related("plan")
        .first()
    )

    if not subscription:
        return Response(
            {
                "message": "An active subscription is required to access AI analytics."
            },
            status=status.HTTP_403_FORBIDDEN
        )

    # Only Enterprise users can access AI analytics
    if not subscription.plan.ai_analytics:
        return Response(
            {
                "message": "AI analytics are available only on the Enterprise plan.",
                "current_plan": subscription.plan.name
            },
            status=status.HTTP_403_FORBIDDEN
        )

    jobs = Job.objects.filter(
        employer=request.user
    )

    role_data = jobs.values(
        "job_type"
    ).annotate(
        application_count=Count("applications"),
        shortlisted=Count(
            "applications",
            filter=Q(
                applications__status="Shortlisted"
            )
        ),
        interviewed=Count(
            "applications",
            filter=Q(
                applications__status="Interview Scheduled"
            )
        ),
        selected=Count(
            "applications",
            filter=Q(
                applications__status="Selected"
            )
        )
    )

    result = {}

    for item in role_data:
        result[item["job_type"]] = {
            "applications": item["application_count"],
            "shortlisted": item["shortlisted"],
            "interviewed": item["interviewed"],
            "selected": item["selected"]
        }

    return Response({
        "role_based_metrics": result
    })
# ==========================================
# Subscription & Payment APIs
# ==========================================

@api_view(['GET'])
def subscription_plans(request):

    plans = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by('price')

    data = []

    for plan in plans:
        data.append({
            "id": plan.id,
            "name": plan.name,
            "description": plan.description,
            "price": str(plan.price),
            "job_post_limit": plan.job_post_limit,
            "unlimited_job_posts": plan.unlimited_job_posts,
            "ai_analytics": plan.ai_analytics,
        })

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_subscription(request):

    subscription = (
        UserSubscription.objects
        .filter(
            user=request.user,
            status="ACTIVE"
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )

    if not subscription:
        return Response({
            "message": "No active subscription found"
        })


    return Response({
        "subscription_id": subscription.id,
        "plan": subscription.plan.name,
        "price": str(subscription.plan.price),
        "status": subscription.status,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
        "job_post_limit": subscription.plan.job_post_limit,
        "unlimited_job_posts": subscription.plan.unlimited_job_posts,
        "ai_analytics": subscription.plan.ai_analytics,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def subscribe(request):

    plan_id = request.data.get("plan_id")

    if not plan_id:
        return Response(
            {"message": "plan_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        plan = SubscriptionPlan.objects.get(
            id=plan_id,
            is_active=True
        )
    except SubscriptionPlan.DoesNotExist:
        return Response(
            {"message": "Subscription plan not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Paid plans must go through Razorpay payment
    if plan.price > Decimal("0"):
        return Response(
            {
                "message": "Please create a Razorpay payment order for this plan",
                "plan_id": plan.id,
                "plan_name": plan.name,
                "amount": str(plan.price)
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Cancel existing active subscription
    UserSubscription.objects.filter(
        user=request.user,
        status="ACTIVE"
    ).update(
        status="CANCELLED",
        end_date=timezone.now()
    )

    # Activate free subscription
    subscription = UserSubscription.objects.create(
        user=request.user,
        plan=plan,
        start_date=timezone.now(),
        status="ACTIVE"
    )

    # Create transaction for free plan
    transaction = PaymentTransaction.objects.create(
        user=request.user,
        subscription=subscription,
        amount=plan.price,
        transaction_id=f"TXN-{request.user.id}-{subscription.id}",
        payment_status="SUCCESS"
    )

    # Create billing history
    BillingHistory.objects.create(
        user=request.user,
        subscription=subscription,
        amount=plan.price,
        invoice_number=f"INV-{request.user.id}-{subscription.id}",
        description=f"{plan.name} subscription"
    )

    return Response(
        {
            "message": "Free subscription activated successfully",
            "subscription": {
                "id": subscription.id,
                "plan": plan.name,
                "price": str(plan.price),
                "status": subscription.status
            },
            "transaction": {
                "transaction_id": transaction.transaction_id,
                "status": transaction.payment_status
            }
        },
        status=status.HTTP_201_CREATED
    )
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_history(request):

    transactions = PaymentTransaction.objects.filter(
        user=request.user
    ).order_by("-payment_date")

    data = []

    for transaction in transactions:
        data.append({
            "transaction_id": transaction.transaction_id,
            "amount": str(transaction.amount),
            "payment_status": transaction.payment_status,
            "payment_date": transaction.payment_date,
        })

    return Response(data)    


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def create_payment_order(request):

    plan_id = request.data.get("plan_id")

    if not plan_id:
        return Response(
            {"message": "plan_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        plan = SubscriptionPlan.objects.get(
            id=plan_id,
            is_active=True
        )
    except SubscriptionPlan.DoesNotExist:
        return Response(
            {"message": "Subscription plan not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Free plans do not need Razorpay payment
    if plan.price <= Decimal("0"):
        return Response(
            {"message": "This plan does not require payment"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Razorpay client
        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        # Razorpay expects amount in paise
        amount_in_paise = int(plan.price * Decimal("100"))

        # Unique receipt
        receipt = f"sub_{request.user.id}_{uuid4().hex[:20]}"

        order_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "user_id": str(request.user.id),
                "plan_id": str(plan.id),
            }
        }

        # Create Razorpay order
        order = client.order.create(data=order_data)

        # Store pending payment in our database
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            amount=plan.price,
            transaction_id=f"TXN-{uuid4().hex}",
            razorpay_order_id=order["id"],
            payment_status="PENDING"
        )

        return Response(
            {
                "message": "Razorpay order created successfully",
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "plan_id": plan.id,
                "plan_name": plan.name,
                "transaction_id": transaction.transaction_id,
                "razorpay_key_id": settings.RAZORPAY_KEY_ID
            },
            status=status.HTTP_201_CREATED
        )

    except Exception as e:
        error_logger.exception("Razorpay order creation failed")

        return Response(
            {
                "message": "Failed to create Razorpay order",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsEmployerUser])
def verify_payment(request):

    razorpay_order_id = request.data.get("razorpay_order_id")
    razorpay_payment_id = request.data.get("razorpay_payment_id")
    razorpay_signature = request.data.get("razorpay_signature")

    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature
    ]):
        return Response(
            {"message": "Payment verification details are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        # Verify Razorpay signature
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        })

        # Find our pending transaction
        transaction = PaymentTransaction.objects.get(
            razorpay_order_id=razorpay_order_id,
            user=request.user
        )

        # Update payment details
        transaction.razorpay_payment_id = razorpay_payment_id
        transaction.razorpay_signature = razorpay_signature
        transaction.payment_status = "SUCCESS"
        transaction.save()

        return Response(
            {
                "message": "Payment verified successfully",
                "transaction_id": transaction.transaction_id,
                "payment_status": transaction.payment_status
            },
            status=status.HTTP_200_OK
        )

    except razorpay.errors.SignatureVerificationError:
        return Response(
            {
                "message": "Payment verification failed",
                "error": "Invalid payment signature"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except PaymentTransaction.DoesNotExist:
        return Response(
            {
                "message": "Payment transaction not found"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    except Exception as e:
        error_logger.exception("Payment verification failed")

        return Response(
            {
                "message": "Payment verification failed",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )        


@api_view(["POST"])
@permission_classes([])
def razorpay_webhook(request):

    try:
        # Get Razorpay webhook signature
        webhook_signature = request.headers.get("X-Razorpay-Signature")

        if not webhook_signature:
            return Response(
                {"message": "Webhook signature is missing"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify webhook signature
        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        client.utility.verify_webhook_signature(
            request.body,
            webhook_signature,
            settings.RAZORPAY_WEBHOOK_SECRET
        )

        event = request.data.get("event")

        if event == "payment.captured":

            payment = request.data.get(
                "payload", {}
            ).get(
                "payment", {}
            ).get(
                "entity", {}
            )

            order_id = payment.get("order_id")
            payment_id = payment.get("id")

            transaction = PaymentTransaction.objects.filter(
                razorpay_order_id=order_id
            ).first()

            if transaction:
                transaction.razorpay_payment_id = payment_id
                transaction.payment_status = "SUCCESS"
                transaction.save()

        elif event == "payment.failed":

            payment = request.data.get(
                "payload", {}
            ).get(
                "payment", {}
            ).get(
                "entity", {}
            )

            order_id = payment.get("order_id")

            transaction = PaymentTransaction.objects.filter(
                razorpay_order_id=order_id
            ).first()

            if transaction:
                transaction.payment_status = "FAILED"
                transaction.save()

        elif event == "refund.created":

            refund = request.data.get(
                "payload", {}
            ).get(
                "refund", {}
            ).get(
                "entity", {}
            )

            payment_id = refund.get("payment_id")

            transaction = PaymentTransaction.objects.filter(
                razorpay_payment_id=payment_id
            ).first()

            if transaction:
                transaction.payment_status = "FAILED"
                transaction.save()

        return Response(
            {"message": "Webhook processed successfully"},
            status=status.HTTP_200_OK
        )

    except razorpay.errors.SignatureVerificationError:

        return Response(
            {
                "message": "Invalid webhook signature"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    except Exception as e:

        error_logger.exception(
            "Razorpay webhook processing failed"
        )

        return Response(
            {
                "message": "Webhook processing failed",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

class PremiumAnalyticsThrottle(UserRateThrottle):
    rate = "5/minute"
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsPremiumEmployer])
@throttle_classes([PremiumAnalyticsThrottle])
def recruiter_premium_analytics(request):

    total_jobs = Job.objects.filter(
        employer=request.user
    ).count()

    total_applications = Application.objects.filter(
        job__employer=request.user
    ).count()

    shortlisted = Application.objects.filter(
        job__employer=request.user,
        status="Shortlisted"
    ).count()

    selected = Application.objects.filter(
        job__employer=request.user,
        status="Selected"
    ).count()

    if total_applications > 0:
        hiring_success_rate = round(
            (selected / total_applications) * 100,
            2
        )
    else:
        hiring_success_rate = 0

    return Response({
        "premium": True,
        "recruiter": request.user.username,
        "analytics": {
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "shortlisted_candidates": shortlisted,
            "selected_candidates": selected,
            "hiring_success_rate": f"{hiring_success_rate}%"
        }
    })        


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsPremiumEmployer])
def recruiter_premium_report(request):

    applications = Application.objects.filter(
        job__employer=request.user
    )

    total = applications.count()

    shortlisted = applications.filter(
        status="Shortlisted"
    ).count()

    interviewed = applications.filter(
        status="Interview Scheduled"
    ).count()

    selected = applications.filter(
        status="Selected"
    ).count()

    rejected = applications.filter(
        status="Rejected"
    ).count()

    # Hiring efficiency
    shortlist_rate = 0
    interview_rate = 0
    selection_rate = 0

    if total > 0:
        shortlist_rate = round(
            (shortlisted / total) * 100,
            2
        )

    if shortlisted > 0:
        interview_rate = round(
            (interviewed / shortlisted) * 100,
            2
        )

    if interviewed > 0:
        selection_rate = round(
            (selected / interviewed) * 100,
            2
        )

    # Candidate success prediction
    success_prediction = []

    for application in applications.select_related(
        "candidate",
        "job"
    ):

        ats_score = application.ats_score or 0

        if ats_score >= 80:
            prediction = "High Success Potential"
        elif ats_score >= 60:
            prediction = "Moderate Success Potential"
        else:
            prediction = "Low Success Potential"

        success_prediction.append({
            "candidate": application.candidate.username,
            "job": application.job.title,
            "ats_score": ats_score,
            "prediction": prediction
        })

    return Response({
        "premium": True,
        "report": {
            "total_applications": total,
            "shortlisted": shortlisted,
            "interviewed": interviewed,
            "selected": selected,
            "rejected": rejected,
            "hiring_efficiency": {
                "application_to_shortlist": f"{shortlist_rate}%",
                "shortlist_to_interview": f"{interview_rate}%",
                "interview_to_selection": f"{selection_rate}%"
            },
            "candidate_success_predictions": success_prediction
        }
    })    


    
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_transactions(request):

    transactions = PaymentTransaction.objects.select_related(
        "user", "subscription", "subscription__plan"
    ).order_by("-payment_date")

    data = []

    for transaction in transactions:
        data.append({
            "transaction_id": transaction.transaction_id,
            "user": transaction.user.username,
            "amount": str(transaction.amount),
            "payment_status": transaction.payment_status,
            "payment_date": transaction.payment_date,
            "plan": (
                transaction.subscription.plan.name
                if transaction.subscription
                else None
            )
        })

    return Response({
        "total_transactions": len(data),
        "transactions": data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_subscription_history(request):

    subscriptions = UserSubscription.objects.select_related(
        "user", "plan"
    ).order_by("-created_at")

    data = []

    for subscription in subscriptions:
        data.append({
            "subscription_id": subscription.id,
            "user": subscription.user.username,
            "plan": subscription.plan.name,
            "price": str(subscription.plan.price),
            "status": subscription.status,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "created_at": subscription.created_at
        })

    return Response({
        "total_subscriptions": len(data),
        "subscriptions": data
    })    



@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_revenue_report(request):

    now = timezone.now()

    # Start of today
    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    # Start of current month
    month_start = today_start.replace(day=1)

    # Successful payments only
    successful_payments = PaymentTransaction.objects.filter(
        payment_status="SUCCESS"
    )

    # Daily revenue
    daily_revenue = successful_payments.filter(
        payment_date__gte=today_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    # Monthly revenue
    monthly_revenue = successful_payments.filter(
        payment_date__gte=month_start
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    # Plan-wise revenue
    plan_revenue = {}

    transactions = successful_payments.select_related(
        "subscription",
        "subscription__plan"
    )

    for transaction in transactions:

        if transaction.subscription:
            plan_name = transaction.subscription.plan.name
        else:
            plan_name = "UNKNOWN"

        if plan_name not in plan_revenue:
            plan_revenue[plan_name] = Decimal("0.00")

        plan_revenue[plan_name] += transaction.amount

    plan_revenue = {
        plan: str(amount)
        for plan, amount in plan_revenue.items()
    }

    return Response({
        "daily_revenue": str(daily_revenue),
        "monthly_revenue": str(monthly_revenue),
        "plan_wise_revenue": plan_revenue
    })    




@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_refund_payment(request):

    transaction_id = request.data.get("transaction_id")
    refund_amount = request.data.get("amount")

    if not transaction_id:
        return Response(
            {"message": "transaction_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        transaction = PaymentTransaction.objects.get(
            transaction_id=transaction_id
        )
    except PaymentTransaction.DoesNotExist:
        return Response(
            {"message": "Transaction not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    if transaction.payment_status != "SUCCESS":
        return Response(
            {
                "message": "Only successful payments can be refunded",
                "payment_status": transaction.payment_status
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not transaction.razorpay_payment_id:
        return Response(
            {
                "message": "Razorpay payment ID not available"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET
            )
        )

        refund_data = {}

        if refund_amount:
            refund_data["amount"] = int(
                Decimal(str(refund_amount)) * Decimal("100")
            )

        refund = client.payment.refund(
            transaction.razorpay_payment_id,
            refund_data
        )

        # Create financial audit log
        AuditLog.objects.create(
            admin=request.user,
            action=(
                f"Refund initiated for transaction "
                f"{transaction.transaction_id}. "
                f"Refund ID: {refund.get('id')}"
            ),
            ip_address=request.META.get("REMOTE_ADDR")
        )

        return Response(
            {
                "message": "Refund initiated successfully",
                "transaction_id": transaction.transaction_id,
                "refund_id": refund.get("id"),
                "refund_amount": str(
                    Decimal(refund.get("amount", 0)) / Decimal("100")
                ),
                "refund_status": refund.get("status")
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:

        AuditLog.objects.create(
            admin=request.user,
            action=(
                f"Refund failed for transaction "
                f"{transaction.transaction_id}: {str(e)}"
            ),
            ip_address=request.META.get("REMOTE_ADDR")
        )

        return Response(
            {
                "message": "Refund failed",
                "error": str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )    


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_financial_audit_logs(request):

    # Refunds and other financial actions recorded in AuditLog
    audit_logs = AuditLog.objects.select_related(
        "admin"
    ).order_by("-created_at")

    audit_data = []

    for log in audit_logs:
        audit_data.append({
            "admin": log.admin.username,
            "action": log.action,
            "ip_address": log.ip_address,
            "created_at": log.created_at
        })

    # Payment failures
    failed_transactions = PaymentTransaction.objects.filter(
        payment_status="FAILED"
    ).select_related("user").order_by("-payment_date")

    failed_data = []

    for transaction in failed_transactions:
        failed_data.append({
            "transaction_id": transaction.transaction_id,
            "user": transaction.user.username,
            "amount": str(transaction.amount),
            "payment_status": transaction.payment_status,
            "payment_date": transaction.payment_date
        })

    # Suspicious transactions
    # Here we flag high-value transactions for admin review.
    suspicious_transactions = PaymentTransaction.objects.filter(
        amount__gte=50000
    ).select_related("user").order_by("-payment_date")

    suspicious_data = []

    for transaction in suspicious_transactions:
        suspicious_data.append({
            "transaction_id": transaction.transaction_id,
            "user": transaction.user.username,
            "amount": str(transaction.amount),
            "payment_status": transaction.payment_status,
            "payment_date": transaction.payment_date,
            "reason": "High-value transaction requires review"
        })

    return Response({
        "total_audit_logs": len(audit_data),
        "audit_logs": audit_data,

        "total_payment_failures": len(failed_data),
        "payment_failures": failed_data,

        "total_suspicious_transactions": len(suspicious_data),
        "suspicious_transactions": suspicious_data
    })
