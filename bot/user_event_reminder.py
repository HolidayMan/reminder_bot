import threading
from time import sleep
from datetime import datetime, time, date

from .utils import localize_time

from bot.bot import bot

from .models import UserEvent, TgUser


user_event_sent = {}


def delete_sent_event(user, event):
    sleep(60)
    events = user_event_sent.get(user.tg_id)
    events.remove(event.id)


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
                threading.Thread(target=delete_sent_event, args=(user, event), daemon=True)
        if send:
            bot.send_message(user.tg_id, mess_text)


def main():
    while True:
        user_events = get_user_events()
        send_events(user_events)
        sleep(1)


remind_event_thread = threading.Thread(target=main, daemon=True)
remind_event_thread.start()
