import re
from datetime import datetime

from telebot import types

from .utils import localize_time, set_menu_state, get_current_state, set_state
from .states.states import States

import bot.phrases as ph
from .bot import bot
from .models import TgUser

MAIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAIN_KEYBOARD.add("Подробнее о рассылке", "Создать своё событие", "Калькулятор сна", "Изменить часовой пояс")


def tz_handler(message):
    tz_pattern = r'[A-Z]{3}(\+|-)[1-9]{1,2}$'
    if re.match(tz_pattern, message.text):
        user = TgUser.objects.get(tg_id__iexact=message.chat.id)
        user.tz_info = message.text
        user.save()
        utctime = datetime.utcnow()
        localized_time = localize_time(utctime, timezone=user.tz_info)
        set_menu_state(message.chat.id)
        return bot.send_message(message.chat.id, ph.AFTER_UPDATING_TIMEZONE % (user.tz_info, localized_time.strftime("%H:%M")), reply_markup=MAIN_KEYBOARD)
    else:
        bot.send_message(message.chat.id, ph.INVALID_TIMEZONE)


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Подробнее о рассылке")
def opt_more_about_mailing(message):
    pass

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Создать своё событие")
def opt_create_event(message):
    pass

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Калькулятор сна")
def opt_sleep_calculator(message):
    pass

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Изменить часовой пояс")
def opt_change_timezone(message):
    answer_message = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, tz_handler)
    return answer_message