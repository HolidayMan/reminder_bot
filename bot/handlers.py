import re
from datetime import datetime, time, date, timedelta

from telebot import types

from django.core.paginator import Paginator

from .utils import localize_time, unlocalize_time, set_menu_state, get_current_state, set_state
from .states.states import States

import bot.phrases as ph
from .bot import bot
from .models import TgUser, Subscription, UserEvent

from bot.buffer import Buffer

SEARCH_TZ_KEYBOARD = types.InlineKeyboardMarkup()
SEARCH_TZ_KEYBOARD.add(types.InlineKeyboardButton(text="Мой часовой пояс", url="https://www.google.com/search?q=%D0%BC%D0%BE%D0%B9+%D1%87%D0%B0%D1%81%D0%BE%D0%B2%D0%BE%D0%B9+%D0%BF%D0%BE%D1%8F%D1%81"))

MAIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
MAIN_KEYBOARD.add("Подробнее о рассылке")
MAIN_KEYBOARD.row("Создать своё событие", "Мои события")
MAIN_KEYBOARD.add("Калькулятор сна", "Часовой пояс")

MAILING_KEYBOARD_UNSUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_UNSUBSCRIBED.add("Подписаться на рассылку", "Назад в меню")

MAILING_KEYBOARD_SUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_SUBSCRIBED.add("Отписаться от рассылки", "Назад в меню")


TZ_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
TZ_KEYBOARD.add("Изменить часовой пояс", "Назад в меню")

def tz_handler(message):
    tz_pattern = r'[A-Z]{3}(\+|-)[1-9]{1,2}$'
    if re.match(tz_pattern, message.text):
        user = TgUser.objects.get(tg_id__iexact=message.chat.id)
        user.tz_info = message.text
        user.save()
        utctime = datetime.utcnow()
        localized_time = localize_time(utctime, timezone=user.tz_info)
        if get_current_state(message.chat.id) == States.S_PAGINATE_TZ.value:
            answer_message = bot.send_message(message.chat.id, ph.AFTER_UPDATING_TIMEZONE % (user.tz_info, localized_time.strftime("%H:%M")), reply_markup=MAIN_KEYBOARD)
        else:
            answer_message = bot.send_message(message.chat.id, ph.AFTER_ADDING_TIMEZONE % (user.tz_info, localized_time.strftime("%H:%M")), reply_markup=MAIN_KEYBOARD)
        set_menu_state(message.chat.id)
        return answer_message
    else:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMEZONE)
        bot.register_next_step_handler(answer_message, tz_handler)
        return answer_message


@bot.message_handler(func=lambda message: message.text == "Назад в меню")
def back_to_menu_handler(message):
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.MENU, reply_markup=MAIN_KEYBOARD)


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
    if not Subscription.objects.filter(title="Mailing").exists():
        mailing = Subscription.objects.create(title="Mailing")
    else:
        mailing = Subscription.objects.get(title="Mailing")
    user.subscriptions.add(mailing)
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.AFTER_SUBSCRIBING_MAILING, reply_markup=MAIN_KEYBOARD)


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MAILING_MENU_OPT.value and message.text == "Отписаться от рассылки")
def opt_unsubscribe_mailing(message):
    user = TgUser.objects.get(tg_id=message.chat.id)
    mailing = Subscription.objects.get(title="Mailing")
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
        if not 0 < times < 999999999:
            raise ValueError("Invalid number")
    except:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMES)
        bot.register_next_step_handler(answer_message, handle_event_remind_times)
        return answer_message
    
    buffer = Buffer()
    event = buffer.get(f"new_user_event{str(message.chat.id)}")
    event.times = times
    event.save()
    localized_time = localize_time(datetime.combine(date.today(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info)
    return bot.send_message(message.chat.id, ph.EVENT_SUCCESSFULY_ADDED % (localized_time.strftime("%H:%M"), event.title), reply_markup=MAIN_KEYBOARD)


# get user events

def paginate_events(events, page=1):
    events_on_page = 10
    paginator = Paginator(events, events_on_page)
    page = paginator.page(page)
    
    if page.object_list:
        message_text = ph.PAGINATE_EVENTS % (page.number, paginator.num_pages)
        for num, event in enumerate(page, page.start_index()): # generating of a message
            localized_time = localize_time(datetime.combine(date.today(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info)
            message_text += '{}. <i>{}</i> ({}) кол-во повторений: {}\n'.format(num, event.title, localized_time.strftime("%H:%M"), event.times)
    else:
        return (ph.YOU_DONT_HAVE_EVENTS, MAIN_KEYBOARD)

    keyboard = types.InlineKeyboardMarkup()
    
    # first_row = []
    # second_row = []
    # for num, i in enumerate(page.get_range()):
    #     if num < plans_on_page // 2:
    #         first_row.append(types.InlineKeyboardButton(text=str(i+1), callback_data="planindex_"+str(i)))
    #     else:
    #         second_row.append(types.InlineKeyboardButton(text=str(i+1), callback_data="planindex_"+str(i)))
    # keyboard.row(*first_row)
    # keyboard.row(*second_row)
    prev_page_button = types.InlineKeyboardButton(text="⬅️", callback_data="eventpage_"+str(page.previous_page_number()) if page.has_previous() else 'eventpage_1')
    cancel_button = types.InlineKeyboardButton(text="❌", callback_data="cancel")
    next_page_button = types.InlineKeyboardButton(text="➡️", callback_data="eventpage_"+str(page.next_page_number()) if page.has_next() else "eventpage_"+str(paginator.num_pages))
    keyboard.row(
        prev_page_button,
        cancel_button,
        next_page_button
    )
    return message_text, keyboard


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Мои события")
def show_events(message):
    user = TgUser.objects.get(tg_id=message.chat.id)
    events = UserEvent.objects.filter(user=user).order_by("remind_time")
    message_text, keyboard = paginate_events(events)
    # if message_text != ph.YOU_DONT_HAVE_EVENTS:
    #     set_state(user.tg_id, States.S_PAGINATE_EVENTS.value)
    answer_message = bot.send_message(message.chat.id, message_text, reply_markup=keyboard, parse_mode="HTML")
    return answer_message


# @bot.callback_query_handler(func=lambda call: get_current_state(call.message.chat.id) == States.S_PAGINATE_EVENTS.value and call.data.split('_')[0] == "eventpage")
@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == "eventpage")
def change_events_page(call):
    page = int(call.data.split('_')[1])
    user = TgUser.objects.get(tg_id=call.message.chat.id)
    events = UserEvent.objects.filter(user=user).order_by("remind_time")
    message_text, keyboard = paginate_events(events, page=page)
    try:
        answer_message = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=keyboard, parse_mode="HTML")
        return answer_message
    except:
        return call.message
    

# sleep calculator

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Калькулятор сна")
def opt_sleep_calculator(message):
    user = TgUser.objects.get(tg_id__iexact=message.chat.id)
    utctime = datetime.utcnow()
    localized_time = localize_time(utctime, timezone=user.tz_info)
    bot.send_message(message.chat.id, ph.YOUR_TIME_NOW % localized_time.strftime("%H:%M"), reply_markup=MAIN_KEYBOARD)
    TIME_19_00 = datetime.combine(localized_time.date(), time(hour=19))
    TIME_20_00 = datetime.combine(localized_time.date(), time(hour=20))
    TIME_07_00 = datetime.combine(localized_time.date(), time(hour=7))
    TIME_00_00_TODAY = datetime.combine(localized_time.date(), time(hour=0))
    TIME_00_00_TOMORROW = datetime.combine((localized_time  + timedelta(days=1)).date(), time(hour=0))

    if TIME_07_00 < localized_time < TIME_19_00:
        answer_message = if_time_less_19_00(message)
    elif TIME_19_00 < localized_time < TIME_20_00:
        answer_message = bot.send_message(message.chat.id, ph.IF_TIME_BETWEEN_19_20, reply_markup=MAIN_KEYBOARD)
    elif TIME_20_00 < localized_time < TIME_00_00_TOMORROW or TIME_00_00_TODAY < localized_time < TIME_07_00:
        answer_message = bot.send_message(message.chat.id, make_after_20_00_message(localized_time), reply_markup=MAIN_KEYBOARD)
    
    return answer_message


def if_time_less_19_00(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    keyboard.add("Да, очень! Глаза сами закрываются!", "Ну не совсем...", "Назад в меню")
    set_state(message.chat.id, States.S_LESS_19_00.value)
    return bot.send_message(message.chat.id, ph.IF_TIME_LESS_19_00, reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Да, очень! Глаза сами закрываются!" and get_current_state(message.chat.id) == States.S_LESS_19_00.value)
def sleep_calc_less_19_00_want_to_sleep(message):
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.IF_WANT_TO_SLEEP, reply_markup=MAIN_KEYBOARD)


@bot.message_handler(func=lambda message: message.text == "Ну не совсем..." and get_current_state(message.chat.id) == States.S_LESS_19_00.value)
def sleep_calc_less_19_00_dont_want_to_sleep(message):
    set_menu_state(message.chat.id)
    return bot.send_message(message.chat.id, ph.IF_DONT_WANT_TO_SLEEP, reply_markup=MAIN_KEYBOARD)


def make_after_20_00_message(localized_time):
    time_after_8_hours = localized_time + timedelta(hours=8)
    localized_time_string = localized_time.strftime("%H:%M")
    time_after_8_hours_string = time_after_8_hours.strftime("%H:%M")
    message = ph.IF_TIME_AFTER_20 % (localized_time_string, localized_time_string, time_after_8_hours_string)
    return message


# change timezones

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Часовой пояс")
def timezone_menu(message):
    set_state(message.chat.id, States.S_PAGINATE_TZ.value)
    user = TgUser.objects.get(tg_id=message.chat.id)
    answer_message = bot.send_message(message.chat.id, ph.YOU_ARE_IN_TZ % (user.tz_info, localize_time(datetime.utcnow(), timezone=user.tz_info).strftime("%H:%M")), reply_markup=TZ_KEYBOARD)
    return answer_message


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_PAGINATE_TZ.value and message.text == "Изменить часовой пояс")
def opt_change_timezone(message):
    answer_message = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=SEARCH_TZ_KEYBOARD)
    bot.register_next_step_handler(answer_message, tz_handler)
    return answer_message
    
