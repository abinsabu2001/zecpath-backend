from django.contrib import admin
from .models import (
    CustomUser,
    CandidateProfile,
    EmployerProfile,
    Job,
    Application,
    AuditLog,
    AICall,
    AIInterviewSession,
    AIQuestion,
    AIAnswer,
    CallLog,
    QuestionTemplate,
    QuestionFlow,
    InterviewState,
    AvailabilitySlot,
    InterviewSchedule,
    SubscriptionPlan,
    UserSubscription,
    PaymentTransaction,
    BillingHistory,


)



@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        'username',
        'email',
        'role',
        'is_verified',
        'created_at',
        'updated_at',
    )
    list_filter = ('role', 'is_verified')
    search_fields = ('username', 'email')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'employer',
        'location',
        'job_type',
        'status',
        'featured',
        'created_at',
    )
    list_filter = ('status', 'featured', 'job_type')
    search_fields = ('title', 'location', 'skills')


admin.site.register(CandidateProfile)
admin.site.register(EmployerProfile)
admin.site.register(Application)
admin.site.register(AuditLog)
admin.site.register(AICall)
admin.site.register(AIInterviewSession)
admin.site.register(AIQuestion)
admin.site.register(AIAnswer)
admin.site.register(CallLog)

admin.site.register(QuestionTemplate)
admin.site.register(QuestionFlow)
admin.site.register(InterviewState)

admin.site.register(AvailabilitySlot)
admin.site.register(InterviewSchedule)
admin.site.register(SubscriptionPlan)
admin.site.register(UserSubscription)
admin.site.register(PaymentTransaction)
admin.site.register(BillingHistory)
