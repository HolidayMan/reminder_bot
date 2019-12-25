from vedis import Vedis

from reminder_bot.settings import STATES_FILE

from datetime import datetime, timedelta, time, date
from .models import TgUser
from .states.states import States



def localize_time(utctime: datetime, offset: int = 0, timezone: str = None) -> datetime:
    if offset:
        if offset >= 0:
            return utctime + timedelta(hours=offset)
        elif offset < 0:
            return utctime - timedelta(hours=abs(offset))
    elif timezone:
        offset = int(timezone[3:])
        if offset >= 0:
            return utctime + timedelta(hours=offset)
        elif offset < 0:
            return utctime - timedelta(hours=abs(offset))
    return utctime


def unlocalize_time(local_time: datetime, offset: int = 0, timezone: str = None) -> datetime:
    if offset:
        if offset >= 0:
            return local_time - timedelta(hours=offset)
        elif offset < 0:
            return local_time + timedelta(hours=abs(offset))
    elif timezone:
        offset = int(timezone[3:])
        if offset >= 0:
            return local_time - timedelta(hours=offset)
        elif offset < 0:
            return local_time + timedelta(hours=abs(offset))
    return local_time


def user_exists(message):
    return TgUser.objects.filter(tg_id__iexact=message.chat.id).exists()

def set_state(user_id, value):
    with Vedis(STATES_FILE) as db:
        try:
            db[user_id] = value
            return True
        except:
            return False


def get_current_state(user_id):
    with Vedis(STATES_FILE) as db:
        try:
            return db[user_id].decode()
        except KeyError:
            return States.S_CHOOSE_MENU_OPT.value


def set_menu_state(user_id):
    with Vedis(STATES_FILE) as db:
        try:
            db[user_id] = States.S_CHOOSE_MENU_OPT.value
            return True
        except:
            return False


def count_time_left2sleep(alarm_time, timezone="UTC+0") -> time:
    utctime = datetime.utcnow()
    localized_time = localize_time(utctime, timezone=timezone)

    alarm_time = datetime.combine(localized_time.date(), time(hour=alarm_time.hour, minute=alarm_time.minute))
    if alarm_time < localized_time:
        alarm_time = datetime.combine((localized_time + timedelta(days=1)).date(), time(hour=alarm_time.hour, minute=alarm_time.minute))
        
    time_sleep_minutes = (alarm_time - localized_time).seconds % 3600 // 60
    time_sleep_hours = (alarm_time - localized_time).seconds // 3600
    datetime_sleep = datetime.combine(localized_time.date(), time(hour=time_sleep_hours, minute=time_sleep_minutes))
    return datetime_sleep.time()


def calculate_phases(alarm_time) -> tuple:
    utctime = datetime.utcnow()
    alarm_time = datetime.combine(utctime.date(), time(hour=alarm_time.hour, minute=alarm_time.minute))
    first_phase = alarm_time - timedelta(hours=9)
    second_phase = alarm_time - timedelta(hours=7, minutes=30)
    third_phase = alarm_time - timedelta(hours=6)
    fourth_phase = alarm_time - timedelta(hours=4, minutes=30)
    return (first_phase.time(), second_phase.time(), third_phase.time(), fourth_phase.time())