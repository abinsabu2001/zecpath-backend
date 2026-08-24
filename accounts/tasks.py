from celery import shared_task

from .reminder_service import send_interview_reminders


@shared_task
def send_interview_reminders_task():
    send_interview_reminders()
    return "Interview reminders processed successfully."


@shared_task
def test_task():
    print("Hello from Celery!")
    return "Task Completed Successfully"