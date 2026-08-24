from django.contrib.auth.models import AbstractUser
from django.db import models

# Custom user model

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('Admin', 'Admin'),
        ('Employer', 'Employer'),
        ('Candidate', 'Candidate'),
    )

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=255, blank=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

  # Candidate profile model
    
class CandidateProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE,
        related_name="candidate_profile"
    )
    skills = models.TextField()
    education = models.CharField(max_length=255)
    experience = models.PositiveIntegerField(default=0)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2)

    resume = models.FileField(
        upload_to='resumes/',
        null=True,
        blank=True
    )

    is_deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return self.user.username


class EmployerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="employer_profile"
    )
    company_name = models.CharField(max_length=255)
    domain = models.CharField(max_length=255)
    company_size = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return self.company_name

class Job(models.Model):

    JOB_TYPE_CHOICES = (
        ('Full Time', 'Full Time'),
        ('Part Time', 'Part Time'),
        ('Internship', 'Internship'),
        ('Remote', 'Remote'),
    )

    employer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='jobs'
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    skills = models.TextField()
    experience = models.PositiveIntegerField()
    salary_min = models.DecimalField(max_digits=10, decimal_places=2)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)

    job_type = models.CharField(
        max_length=20,
        choices=JOB_TYPE_CHOICES
    )

    status = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Application(models.Model):

    STATUS_CHOICES = (
    ('Applied', 'Applied'),
    ('Shortlisted', 'Shortlisted'),
    ('Interview Scheduled', 'Interview Scheduled'),
    ('Rejected', 'Rejected'),
    ('Selected', 'Selected'),
)
    candidate = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
        related_name='applications'
    )

    resume_snapshot = models.FileField(
        upload_to='application_resumes/',
        null=True,
        blank=True
    )

    status = models.CharField(
    max_length=20,
    choices=STATUS_CHOICES,
    default='Applied',
    db_index=True

    )

    ats_score = models.FloatField(default=0)

    auto_processed = models.BooleanField(default=False)

    is_eligible = models.BooleanField(default=False)

    applied_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('candidate', 'job')

    def __str__(self):
        return f"{self.candidate.username} - {self.job.title}"

class AuditLog(models.Model):
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="audit_logs"
    )

    action = models.CharField(max_length=255)

    ip_address = models.GenericIPAddressField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.username} - {self.action}"

class AICall(models.Model):

    STATUS_CHOICES = (
        ('QUEUED', 'Queued'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='ai_call'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='QUEUED'
    )

    retries = models.PositiveIntegerField(default=0)

    scheduled_time = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.application.candidate.username} - {self.status}"        


class AIInterviewSession(models.Model):

    STATUS_CHOICES = (
        ('Scheduled', 'Scheduled'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='interview_session'
    )

    interview_start = models.DateTimeField()

    interview_end = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Scheduled'
    )

    transcript = models.JSONField(
        default=list,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.candidate.username} - {self.status}"
        
class AIQuestion(models.Model):

    interview_session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    question_text = models.TextField()

    question_order = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question {self.question_order}"


class AIAnswer(models.Model):

    interview_session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name='answers'
    )

    question = models.OneToOneField(
        AIQuestion,
        on_delete=models.CASCADE,
        related_name='answer'
    )

    answer_text = models.TextField()

    answer_score = models.FloatField(default=0)

    answer_text = models.TextField()

    answer_score = models.FloatField(default=0)

    relevance_score = models.FloatField(default=0)

    completeness_score = models.FloatField(default=0)

    keyword_score = models.FloatField(default=0)

    confidence = models.FloatField(default=0)

    annotations = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Answer for Question {self.question.question_order}"


class CallLog(models.Model):

    STATUS_CHOICES = (
        ('Started', 'Started'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    )

    interview_session = models.OneToOneField(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name='call_log'
    )

    triggered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    reason = models.CharField(max_length=255)

    call_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Started'
    )

    started_at = models.DateTimeField()

    ended_at = models.DateTimeField(
        null=True,
        blank=True
    )

    duration = models.DurationField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interview_session.application.candidate.username} - {self.call_status}"   


class QuestionTemplate(models.Model):

    CATEGORY_CHOICES = (
        ('Introduction', 'Introduction'),
        ('Experience', 'Experience'),
        ('Skills', 'Skills'),
        ('Availability', 'Availability'),
        ('Salary', 'Salary'),
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES
    )

    question = models.TextField()

    role = models.CharField(
        max_length=100,
        default="General"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question

class QuestionFlow(models.Model):

    current_question = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.CASCADE,
        related_name="current_question"
    )

    answer_value = models.CharField(
        max_length=100
    )

    next_question = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.CASCADE,
        related_name="next_question"
    )

    def __str__(self):
        return f"{self.current_question} -> {self.next_question}"

class InterviewState(models.Model):

    candidate = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )

    current_question = models.ForeignKey(
        QuestionTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    last_answer = models.TextField(
        blank=True
    )

    completed = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.candidate.username


class AvailabilitySlot(models.Model):
    employer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="availability_slots"
    )

    date = models.DateField()

    start_time = models.TimeField()

    end_time = models.TimeField()

    is_booked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employer.username} - {self.date}"



class InterviewSchedule(models.Model):

    STATUS_CHOICES = (
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    )

    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name="interview_schedule"
    )

    slot = models.ForeignKey(
        AvailabilitySlot,
        on_delete=models.CASCADE,
        related_name="interviews"
    )

    meeting_link = models.URLField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Scheduled"
    )

    scheduled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.candidate.username}"    



class InterviewReminder(models.Model):

    REMINDER_TYPE_CHOICES = (
        ("24_HOURS", "24 Hours Before"),
        ("1_HOUR", "1 Hour Before"),
    )

    STATUS_CHOICES = (
        ("Pending", "Pending"),
        ("Sent", "Sent"),
        ("Failed", "Failed"),
    )

    interview = models.ForeignKey(
        InterviewSchedule,
        on_delete=models.CASCADE,
        related_name="reminders"
    )

    reminder_type = models.CharField(
        max_length=20,
        choices=REMINDER_TYPE_CHOICES
    )

    scheduled_time = models.DateTimeField()

    sent_at = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )

    failure_reason = models.TextField(
        blank=True,
        null=True
    )

    retry_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.interview.application.candidate.username} - {self.reminder_type}"    



class SubscriptionPlan(models.Model):

    PLAN_CHOICES = (
        ("FREE", "Free"),
        ("PRO", "Pro"),
        ("ENTERPRISE", "Enterprise"),
    )

    name = models.CharField(
        max_length=20,
        choices=PLAN_CHOICES,
        unique=True
    )

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    job_post_limit = models.PositiveIntegerField(
        default=0
    )

    ai_analytics = models.BooleanField(default=False)

    unlimited_job_posts = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserSubscription(models.Model):

    STATUS_CHOICES = (
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    start_date = models.DateTimeField()

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class PaymentTransaction(models.Model):

    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="payment_transactions"
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Internal transaction reference
    transaction_id = models.CharField(
        max_length=255,
        unique=True
    )

    # Razorpay order ID
    razorpay_order_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    # Razorpay payment ID
    razorpay_payment_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True
    )

    # Razorpay payment signature
    razorpay_signature = models.CharField(
        max_length=500,
        null=True,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    payment_date = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.transaction_id}"


class BillingHistory(models.Model):

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="billing_history"
    )

    subscription = models.ForeignKey(
        UserSubscription,
        on_delete=models.CASCADE,
        related_name="billing_records"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    billing_date = models.DateTimeField(
        auto_now_add=True
    )

    invoice_number = models.CharField(
        max_length=100,
        unique=True
    )

    description = models.CharField(
        max_length=255,
        blank=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.invoice_number}"        