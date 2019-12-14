from vedis import Vedis

from reminder_bot.settings import STATES_FILE

from datetime import datetime, timedelta, time
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
