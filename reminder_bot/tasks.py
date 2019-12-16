from reminder_bot.celery import app as celery_app

from bot.user_event_reminder import get_user_events, send_events
from bot.mailing import get_users_whose_time_equals, send_users_articles

@celery_app.task
def remind_about_events():
    user_events = get_user_events()
    send_events(user_events)

@celery_app.task
def mailing_task():
    user_articles = get_users_whose_time_equals()
    send_users_articles(user_articles)