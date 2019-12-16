import threading
from time import sleep
from datetime import datetime, time, date

from .utils import localize_time

from bot.bot import bot

from .models import UserEvent, TgUser

from reminder_bot.celery import app

user_event_sent = {}

@app.task
def delete_sent_event(user_id, event_id):
    # sleep(60)
    events = user_event_sent.get(user_id)
    events.remove(event_id)


def get_user_events():
    utctime: datetime = datetime.utcnow()
    user_events = {}
    events = UserEvent.objects.all()
    for event in events:
        event_user = event.user
        if time(event.remind_time.hour, event.remind_time.minute) == time(utctime.time().hour, utctime.time().minute):
            user_events.setdefault(event_user, set()).add(event)
    return user_events


def send_events(user_events: dict):
    for user, events in user_events.items():
        utcdate = datetime.combine(date.today(), time(hour=list(events)[0].remind_time.hour, minute=list(events)[0].remind_time.minute))
        mess_text = "Напоминание (%s): \n" % localize_time(utcdate, timezone=user.tz_info).strftime("%H:%M")
        send = False
        for event in events:
            if event.id in user_event_sent.get(user.tg_id, {}): # was already sent
                continue
            send = True
            mess_text += f"- {event.title}\n"
            event.times -= 1
            if event.times <= 0:
                event.delete()
            else:
                event.save(update_fields=["times"])
                user_event_sent.setdefault(user.tg_id, set()).add(event.id)
                # threading.Thread(target=delete_sent_event, args=(user, event), daemon=True).start()
                delete_sent_event.apply_async(args=(user.tg_id, event.id), countdown=60)
        if send:
            try:
                bot.send_message(user.tg_id, mess_text)
            except Exception as e:
                print(e.with_traceback())


