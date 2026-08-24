from django.utils import timezone
from datetime import timedelta

from .models import InterviewReminder
from .email_utils import send_notification_email


def send_interview_reminders():
    now = timezone.now()

    reminders = InterviewReminder.objects.filter(
        status="Pending",
        scheduled_time__lte=now
    )

    for reminder in reminders:

        try:
            candidate = reminder.interview.application.candidate

            email = candidate.email

            subject = "Interview Reminder"

            interview_time = reminder.interview.slot.start_time
            interview_date = reminder.interview.slot.date

            message = (
                f"Hello {candidate.username},\n\n"
                f"This is a reminder that your interview is scheduled "
                f"for {interview_date} at {interview_time}.\n\n"
                f"Please be available on time.\n\n"
                f"Good luck!"
            )

            send_notification_email(
                subject,
                message,
                email
            )

            reminder.status = "Sent"
            reminder.sent_at = now
            reminder.save()

        except Exception as e:

            reminder.status = "Failed"
            reminder.failure_reason = str(e)
            reminder.retry_count += 1
            reminder.save()