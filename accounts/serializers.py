from rest_framework import serializers
from .models import (
    CustomUser,
    CandidateProfile,
    EmployerProfile,
    Job,
    Application,
    AuditLog,
    QuestionTemplate,
    QuestionFlow,
    InterviewState,
    AIInterviewSession,
    AIQuestion,
    AIAnswer,
    AvailabilitySlot,
    InterviewSchedule,
)
from .encryption import encrypt_value, decrypt_value

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'phone', 'role']

    def validate_phone(self, value):
        if len(value) != 10 or not value.isdigit():
            raise serializers.ValidationError("Phone number must be 10 digits.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')

        if validated_data.get("phone"):
            validated_data["phone"] = encrypt_value(validated_data["phone"])

        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.phone:
            try:
                data["phone"] = decrypt_value(instance.phone)
            except Exception:
                data["phone"] = instance.phone

        return data

class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = "__all__"
        read_only_fields = ['user']

    def validate_experience(self, value):
        if value < 0:
            raise serializers.ValidationError("Experience cannot be negative.")
        return value

    def validate_expected_salary(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Expected salary must be greater than 0."
            )
        return value

    def validate_skills(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Skills cannot be empty.")
        return value

    def validate_education(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Education is required.")
        return value

    def validate_resume(self, value):
        allowed_extensions = ['pdf', 'doc', 'docx']

        extension = value.name.split('.')[-1].lower()

        if extension not in allowed_extensions:
            raise serializers.ValidationError(
                "Only PDF, DOC, and DOCX files are allowed."
            )

        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError(
                "File size must be less than 5 MB."
            )

        return value


class CandidateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateProfile
        fields = [
            "id",
            "user",
            "skills",
            "education",
            "experience",
            "expected_salary",
            "resume",
            "is_deleted",
        ]        


class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployerProfile
        fields = "__all__"
        read_only_fields = ['user']

    def validate_company_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Company name is required.")
        return value

    def validate_domain(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Domain is required.")
        return value

    def validate_company_size(self, value):
        if len(value.strip()) == 0:
            raise serializers.ValidationError("Company size is required.")
        return value


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = "__all__"
        read_only_fields = [
            "id",
            "employer",
            "created_at",
            "updated_at"
        ]

    def validate_title(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Job title must be at least 3 characters."
            )
        return value

    def validate_salary_min(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Minimum salary cannot be negative."
            )
        return value

    def validate_salary_max(self, value):
        if value < 0:
            raise serializers.ValidationError(
                "Maximum salary cannot be negative."
            )
        return value

    def validate(self, data):
        salary_min = data.get("salary_min")
        salary_max = data.get("salary_max")

        if salary_min is not None and salary_max is not None:
           if salary_max < salary_min:
               raise serializers.ValidationError(
                "Maximum salary must be greater than minimum salary."
               )

        return data
class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(
        source="job.title",
        read_only=True
    )

    class Meta:
        model = Application
        fields = [
            "id",
            "candidate",
            "job",
            "job_title",
            "resume_snapshot",
            "status",
            "applied_date",
        ]
        read_only_fields = [
            "id",
            "candidate",
            "resume_snapshot",
            "status",
            "applied_date",
        ]
class AuditLogSerializer(serializers.ModelSerializer):

    class Meta:
        model = AuditLog
        fields = "__all__"      

class QuestionTemplateSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuestionTemplate
        fields = "__all__"

    def validate_question(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError(
                "Question must be at least 5 characters."
            )
        return value

class QuestionFlowSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuestionFlow
        fields = "__all__"

class InterviewStateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterviewState
        fields = "__all__"
        

class AIAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = AIAnswer
        fields = "__all__"
        read_only_fields = [
            "answer_score",
            "relevance_score",
            "completeness_score",
            "keyword_score",
            "confidence",
            "annotations",
            "created_at",
        ]        


class AvailabilitySlotSerializer(serializers.ModelSerializer):

    class Meta:
        model = AvailabilitySlot
        fields = "__all__"
        read_only_fields = [
            "employer",
            "created_at",
        ]

    def validate(self, data):
        if data["start_time"] >= data["end_time"]:
            raise serializers.ValidationError(
                "End time must be greater than start time."
            )
        return data


class InterviewScheduleSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterviewSchedule
        fields = "__all__"
        read_only_fields = [
            "scheduled_at",
        ]                