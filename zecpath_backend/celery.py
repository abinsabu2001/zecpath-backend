import os

from celery import Celery
from celery.schedules import crontab


os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'zecpath_backend.settings'
)

app = Celery('zecpath_backend')

app.config_from_object(
    'django.conf:settings',
    namespace='CELERY'
)

app.autodiscover_tasks()


# Automatic reminder schedule
app.conf.beat_schedule = {
    'send-interview-reminders-every-hour': {
        'task': 'accounts.tasks.send_interview_reminders_task',
        'schedule': crontab(minute=0),
    },
}