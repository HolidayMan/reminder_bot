import re
from datetime import datetime, time, date

from telebot import types

from .utils import localize_time, unlocalize_time, set_menu_state, get_current_state, set_state
from .states.states import States

import bot.phrases as ph
from .bot import bot
from .models import TgUser, Subscriptions, UserEvent

from bot.buffer import Buffer

MAIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAIN_KEYBOARD.add("Подробнее о рассылке", "Создать своё событие", "Калькулятор сна", "Изменить часовой пояс")

MAILING_KEYBOARD_UNSUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_UNSUBSCRIBED.add("Подписаться на рассылку", "Назад в меню")

MAILING_KEYBOARD_SUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_SUBSCRIBED.add("Отписаться от рассылки", "Назад в меню")

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
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMEZONE)
        bot.register_next_step_handler(answer_message, tz_handler)
        return answer_message


@bot.message_handler(func=lambda message: message.text == "Назад в меню")
def back_to_menu_handler(message):
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.MENU, reply_markup=MAIN_KEYBOARD)


def back_to_menu(bot_message, user_message):
    set_menu_state(user_message.chat.id)
    return bot.edit_message_reply_markup(user_message.chat.id, message_id=bot_message.message_id, reply_markup=MAIN_KEYBOARD)


# mailing

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Подробнее о рассылке")
def opt_more_about_mailing(message):
    set_state(message.chat.id, States.S_CHOOSE_MAILING_MENU_OPT.value)
    user = TgUser.objects.get(tg_id=message.chat.id)
    if user.subscriptions.filter(title__iexact="Mailing").exists():
        return bot.send_message(message.chat.id, ph.MAILING_INFO, reply_markup=MAILING_KEYBOARD_SUBSCRIBED)
    else:
        return bot.send_message(message.chat.id, ph.MAILING_INFO, reply_markup=MAILING_KEYBOARD_UNSUBSCRIBED)


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MAILING_MENU_OPT.value and message.text == "Подписаться на рассылку")
def opt_subscribe_mailing(message):
    user = TgUser.objects.get(tg_id=message.chat.id)
    if not Subscriptions.objects.filter(title="Mailing").exists():
        mailing = Subscriptions.objects.create(title="Mailing")
    else:
        mailing = Subscriptions.objects.get(title="Mailing")
    user.subscriptions.add(mailing)
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.AFTER_SUBSCRIBING_MAILING, reply_markup=MAIN_KEYBOARD)


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MAILING_MENU_OPT.value and message.text == "Отписаться от рассылки")
def opt_unsubscribe_mailing(message):
    user = TgUser.objects.get(tg_id=message.chat.id)
    mailing = Subscriptions.objects.get(title="Mailing")
    user.subscriptions.remove(mailing)
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.AFTER_UNSUBSCRIBING_MAILING, reply_markup=MAIN_KEYBOARD)


# create events

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Создать своё событие")
def opt_create_event(message):
    user = TgUser.objects.get(tg_id=message.chat.id)
    new_event = UserEvent(user=user)
    buffer = Buffer()
    buffer.add_or_change(f"new_user_event{str(message.chat.id)}", new_event)
    answer_message = bot.send_message(message.chat.id, ph.ENETER_EVENT_TIME, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, handle_event_time)
    return answer_message


def handle_event_time(message):
    time_pattern = r"([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    if re.match(time_pattern, message.text):
        user = TgUser.objects.get(tg_id=message.chat.id)
        buffer = Buffer()
        event = buffer.get(f"new_user_event{str(message.chat.id)}")
        hours = int(message.text.split(':')[0])
        minutes = int(message.text.split(':')[1])
        event_time = unlocalize_time(datetime.combine(date.today(), time(hour=hours, minute=minutes)), timezone=user.tz_info).time()
        event.remind_time = event_time
        buffer.add_or_change(f"new_user_event{str(message.chat.id)}", event)
        
        answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_TITLE)
        bot.register_next_step_handler(answer_message, handle_event_title)
        return answer_message
    else:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIME)
        bot.register_next_step_handler(answer_message, handle_event_time)
        return answer_message
    

def handle_event_title(message):
    buffer = Buffer()
    event = buffer.get(f"new_user_event{str(message.chat.id)}")
    event.title = message.text
    buffer.add_or_change(f"new_user_event{str(message.chat.id)}", event)
    
    answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_REMIND_TIMES)
    bot.register_next_step_handler(answer_message, handle_event_remind_times)


def handle_event_remind_times(message):
    try:
        times = int(message.text)
    except:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMES)
        bot.register_next_step_handler(answer_message, handle_event_remind_times)
        return answer_message
    
    buffer = Buffer()
    event = buffer.get(f"new_user_event{str(message.chat.id)}")
    event.times = times
    event.save()
    return bot.send_message(message.chat.id, ph.EVENT_SUCCESSFULY_ADDED % (event.remind_time.strftime("%H:%M"), event.title), reply_markup=MAIN_KEYBOARD)


# sleep calculator

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Калькулятор сна")
def opt_sleep_calculator(message):
    bot.send_message(message.chat.id, ph.THIS_OPTION_IS_UNRELEASED_YET)


# change timezones

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Изменить часовой пояс")
def opt_change_timezone(message):
    answer_message = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, tz_handler)
    return answer_message
    