from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
# from celery.schedules import crontab
from datetime import timedelta
# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reminder_bot.settings')

app = Celery('reminder_bot')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    # Executes every Monday morning at 7:30 a.m.
    'remind_about_events': {
        'task': 'reminder_bot.tasks.remind_about_events',
        'schedule': timedelta(seconds=40),
    },
    'mailing': {
        'task': 'reminder_bot.tasks.mailing_task',
        'schedule': timedelta(seconds=40),
    },
}

# celery -A reminder_bot worker -l info --beat