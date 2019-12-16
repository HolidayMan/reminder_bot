import threading
from time import sleep
from datetime import datetime, time


from bot.bot import bot

from .utils import localize_time

from .models import MailingArcticle, TgUser, Subscription

from reminder_bot.celery import app as celery_app

# datetime.combine(date.today(), time(hour=hours, minute=minutes))

user_article_sent = {}

@celery_app.task
def delete_sent_article(user_id, article_id):
    articles = user_article_sent.get(user_id)
    articles.remove(article_id)


def get_users_whose_time_equals() -> dict:
    utctime = datetime.utcnow()
    user_article = {}
    users = Subscription.objects.get(title="Mailing").users.all()
    articles = MailingArcticle.objects.all()
    for article in articles:
        if not article.remind:
            continue
        for user in users:
            localized_time = localize_time(utctime, timezone=user.tz_info).time()
            if time(localized_time.hour, localized_time.minute) == article.remind_time:
                user_article.setdefault(user, set()).add(article)
    return user_article


def send_users_articles(user_article: dict):
    for user, articles in user_article.items():
        for article in articles:
            if article.id in user_article_sent.get(user.tg_id, set()):
                continue
            user_article_sent.setdefault(user.tg_id, set()).add(article.id)
            try:
                bot.send_message(user.tg_id, "Рассылка (%s):\n" % article.remind_time.strftime("%H:%M") + article.body, parse_mode="HTML")
            except Exception as e:
                print(e.with_traceback())
            # threading.Thread(target=delete_sent_article, args=(user, article), daemon=True).start()
            delete_sent_article.apply_async(args=(user.tg_id, article.id), countdown=60)
