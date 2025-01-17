import re
from datetime import datetime, time, date, timedelta

from telebot import types

from django.core.paginator import Paginator

from .utils import localize_time, unlocalize_time, set_menu_state, get_current_state, set_state, count_time_left2sleep, calculate_phases
from .states.states import States

import bot.phrases as ph
from .bot import bot
from .models import TgUser, Subscription, UserEvent

from bot.buffer import Buffer

CANCEL_INLINE_BUTTON = types.InlineKeyboardButton(text="❌", callback_data="cancel")

SEARCH_TZ_KEYBOARD = types.InlineKeyboardMarkup()
SEARCH_TZ_KEYBOARD.add(types.InlineKeyboardButton(text="Мой часовой пояс", url="https://www.google.com/search?q=%D0%BC%D0%BE%D0%B9+%D1%87%D0%B0%D1%81%D0%BE%D0%B2%D0%BE%D0%B9+%D0%BF%D0%BE%D1%8F%D1%81"))

MAIN_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAIN_KEYBOARD.add("Подробнее о рассылке")
MAIN_KEYBOARD.row("Создать своё событие", "Мои события")
MAIN_KEYBOARD.add("Калькулятор сна", "Часовой пояс")

MAILING_KEYBOARD_UNSUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_UNSUBSCRIBED.add("Подписаться на рассылку", "Назад в меню")

MAILING_KEYBOARD_SUBSCRIBED = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
MAILING_KEYBOARD_SUBSCRIBED.add("Отписаться от рассылки", "Назад в меню")


TZ_KEYBOARD = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
TZ_KEYBOARD.add("Изменить часовой пояс", "Назад в меню")

def tz_handler(message):
    if not (isinstance(message.text, str) or isinstance(message.text, bytes)):
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMEZONE)
        bot.register_next_step_handler(answer_message, tz_handler)
        return answer_message
    tz_pattern = r'[A-Z]{3}(\+|-)([0-9]|1[0-2])$'
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
    buffer.add_or_change(f"{str(message.chat.id)}new_user_event", new_event)
    answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_TIME, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, handle_event_time)
    return answer_message


def handle_event_time(message):
    if not (isinstance(message.text, str) or isinstance(message.text, bytes)):
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIME)
        bot.register_next_step_handler(answer_message, handle_event_time)
        return answer_message
    time_pattern = r"([0-1]*[0-9]|2[0-3]):[0-5][0-9]$"
    if re.match(time_pattern, message.text):
        user = TgUser.objects.get(tg_id=message.chat.id)
        buffer = Buffer()
        event = buffer.get(f"{str(message.chat.id)}new_user_event")
        hours = int(message.text.split(':')[0])
        minutes = int(message.text.split(':')[1])
        event_time = unlocalize_time(datetime.combine(datetime.utcnow().date(), time(hour=hours, minute=minutes)), timezone=user.tz_info).time()
        event.remind_time = event_time
        buffer.add_or_change(f"{str(message.chat.id)}new_user_event", event)
        
        answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_TITLE)
        bot.register_next_step_handler(answer_message, handle_event_title)
        return answer_message
    else:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIME)
        bot.register_next_step_handler(answer_message, handle_event_time)
        return answer_message
    

def handle_event_title(message):
    if not (isinstance(message.text, str) or isinstance(message.text, bytes)):
        answer_message =  bot.send_message(message.chat.id, ph.INVALID_TITLE, parse_mode="HTML")
        bot.register_next_step_handler(answer_message, handle_event_title)
        return answer_message
    if len(message.text) > 256:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TITLE, parse_mode="HTML")
        bot.register_next_step_handler(answer_message, handle_event_title)
    buffer = Buffer()
    event = buffer.get(f"{str(message.chat.id)}new_user_event")
    event.title = message.text
    buffer.add_or_change(f"{str(message.chat.id)}new_user_event", event)
    
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
    event = buffer.get(f"{str(message.chat.id)}new_user_event")
    event.times = times
    event.save()
    localized_time = localize_time(datetime.combine(datetime.utcnow().date(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info)
    return bot.send_message(message.chat.id, ph.EVENT_SUCCESSFULY_ADDED % (localized_time.strftime("%H:%M"), event.title), reply_markup=MAIN_KEYBOARD)


# get user events

def paginate_events(events, page=1):
    events_on_page = 10
    paginator = Paginator(events, events_on_page)
    if page < paginator.num_pages:
        page = paginator.page(page)
    else:
        page = paginator.page(paginator.num_pages)

    if page.object_list:
        message_text = ph.PAGINATE_EVENTS % (page.number, paginator.num_pages)
        for num, event in enumerate(page, page.start_index()): # generating of a message
            localized_time = localize_time(datetime.combine(datetime.utcnow().date(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info)
            message_text += '{}. <i>{}</i> ({}) <b>кол-во повторений:</b> {}\n'.format(num, event.title, localized_time.strftime("%H:%M"), event.times)
    else:
        return (ph.YOU_DONT_HAVE_EVENTS,  None)

    keyboard = types.InlineKeyboardMarkup()
    
    first_row = []
    second_row = []
    for num, i in enumerate(page.object_list, page.start_index()):
        if num-1 < events_on_page // 2:
            first_row.append(types.InlineKeyboardButton(text=str(num), callback_data=f"eventindex_{i.id}_page_{page.number}"))
        else:
            second_row.append(types.InlineKeyboardButton(text=str(num), callback_data=f"eventindex_{i.id}_page_{page.number}"))
    keyboard.row(*first_row)
    keyboard.row(*second_row)
    prev_page_button = types.InlineKeyboardButton(text="⬅️", callback_data=f"eventpage_{page.previous_page_number()}_page_{page.number}" if page.has_previous() else f'eventpage_1_page_{page.number}')
    next_page_button = types.InlineKeyboardButton(text="➡️", callback_data=f"eventpage_{page.next_page_number()}_page_{page.number}" if page.has_next() else f"eventpage_{paginator.num_pages}_page_{page.number}")
    keyboard.row(
        prev_page_button,
        CANCEL_INLINE_BUTTON,
        next_page_button
    )
    return message_text, keyboard


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Мои события")
def show_events(message, page=1):
    user = TgUser.objects.get(tg_id=message.chat.id)
    events = UserEvent.objects.filter(user=user).order_by("remind_time")
    message_text, keyboard = paginate_events(events, page)
    # if message_text != ph.YOU_DONT_HAVE_EVENTS:
    #     set_state(user.tg_id, States.S_PAGINATE_EVENTS.value)
    answer_message = bot.send_message(message.chat.id, message_text, reply_markup=keyboard, parse_mode="HTML")
    return answer_message


# @bot.callback_query_handler(func=lambda call: get_current_state(call.message.chat.id) == States.S_PAGINATE_EVENTS.value and call.data.split('_')[0] == "eventpage")
@bot.callback_query_handler(func=lambda call: call.data.split('_')[0] == "eventpage")
def change_events_page(call):
    page, curr_page = [int(i) for i in call.data.split("_") if i.isdigit()]
    if page == curr_page:
        return
    user = TgUser.objects.get(tg_id=call.message.chat.id)
    events = UserEvent.objects.filter(user=user).order_by("remind_time")
    message_text, keyboard = paginate_events(events, page=page)
    answer_message = bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=keyboard, parse_mode="HTML")
    return answer_message
    

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
        # answer_message = bot.send_message(message.chat.id, make_after_20_00_message(localized_time), reply_markup=MAIN_KEYBOARD)
        answer_message = if_time_after_20_00(message)
    
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


def if_time_after_20_00(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1, one_time_keyboard=True)
    keyboard.add("Сколько я просплю если засну прямо сейчас", "Во сколько лечь чтобы встать бодрым", "Назад в меню")
    set_state(message.chat.id, States.S_AFTER_20_00.value)
    return bot.send_message(message.chat.id, ph.ARE_YOU_GOING_TO_SLEEP, reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "Сколько я просплю если засну прямо сейчас" and get_current_state(message.chat.id) == States.S_AFTER_20_00.value)
def sleep_calc_less_20_00_how_long_i_will_sleep(message):
    answer_message = bot.send_message(message.chat.id, ph.WHAT_TIME_SET_ALARM_CLOCK, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, handle_alarm_clock_time)
    set_state(message.chat.id, States.S_HOW_LONG_I_WILL_SLEEP.value)
    return answer_message


@bot.message_handler(func=lambda message: message.text == "Во сколько лечь чтобы встать бодрым" and get_current_state(message.chat.id) == States.S_AFTER_20_00.value)
def sleep_calc_less_20_00_sleep_phases(message):
    answer_message = bot.send_message(message.chat.id, ph.WHAT_TIME_SET_ALARM_CLOCK, reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(answer_message, handle_alarm_clock_time)
    set_state(message.chat.id, States.S_SLEEP_PHASES.value)
    return answer_message


def handle_alarm_clock_time(message):
    time_pattern = r"([0-1]*[0-9]|2[0-3]):[0-5][0-9]$"
    if re.match(time_pattern, message.text):
        user = TgUser.objects.get(tg_id=message.chat.id)
        hours = int(message.text.split(':')[0])
        minutes = int(message.text.split(':')[1])
        localized_alarm_time = time(hour=hours, minute=minutes)

        if get_current_state(message.chat.id) == States.S_HOW_LONG_I_WILL_SLEEP.value:
            set_menu_state(message.chat.id)
            time_left2sleep = count_time_left2sleep(localized_alarm_time, timezone=user.tz_info)
            return bot.send_message(message.chat.id, ph.TO_ALARM_LEFT_TIME % (localized_alarm_time.strftime("%H:%M"), str(time_left2sleep.hour), str(time_left2sleep.minute)), reply_markup=MAIN_KEYBOARD, parse_mode="HTML")
        elif get_current_state(message.chat.id) == States.S_SLEEP_PHASES.value:
            set_menu_state(message.chat.id)
            sleep_phases = calculate_phases(localized_alarm_time)
            str_sleep_phases = tuple(phase.strftime("%H:%M") for phase in sleep_phases)
            return bot.send_message(message.chat.id, ph.THE_BEST_TIME_TO_GO_TO_BED % str_sleep_phases, reply_markup=MAIN_KEYBOARD, parse_mode="HTML")
    else:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIME)
        bot.register_next_step_handler(answer_message, handle_alarm_clock_time)
        return answer_message


# def make_after_20_00_message(localized_time):
#     time_after_8_hours = localized_time + timedelta(hours=8)
#     localized_time_string = localized_time.strftime("%H:%M")
#     time_after_8_hours_string = time_after_8_hours.strftime("%H:%M")
#     message = ph.IF_TIME_AFTER_20 % (localized_time_string, localized_time_string, time_after_8_hours_string)
#     return message


# change timezones

@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_CHOOSE_MENU_OPT.value and message.text == "Часовой пояс")
def timezone_menu(message):
    set_state(message.chat.id, States.S_PAGINATE_TZ.value)
    user = TgUser.objects.get(tg_id=message.chat.id)
    answer_message = bot.send_message(message.chat.id, ph.YOU_ARE_IN_TZ % (user.tz_info, localize_time(datetime.utcnow(), timezone=user.tz_info).strftime("%H:%M")), reply_markup=TZ_KEYBOARD)
    return answer_message


@bot.message_handler(func=lambda message: get_current_state(message.chat.id) == States.S_PAGINATE_TZ.value and message.text == "Изменить часовой пояс")
def opt_change_timezone(message):
    answer_message1 = bot.send_message(message.chat.id, ph.CHANGING_TZ, reply_markup=types.ReplyKeyboardRemove())
    answer_message2 = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=SEARCH_TZ_KEYBOARD)
    bot.register_next_step_handler(answer_message2, tz_handler)
    return answer_message1, answer_message2
