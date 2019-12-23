import re
from datetime import datetime, time, date, timedelta

from telebot import types

from django.core.paginator import Paginator

from .utils import localize_time, unlocalize_time, set_menu_state, get_current_state, set_state
from .states.states import States

import bot.phrases as ph
from .bot import bot
from .handlers import MAIN_KEYBOARD, CANCEL_INLINE_BUTTON, paginate_events, show_events
from .models import TgUser, Subscription, UserEvent

from bot.buffer import Buffer



EVENT_INDEX_PATTERN = r"eventindex_(\d+)_page_(\d+)"

@bot.callback_query_handler(func=lambda call: re.match(EVENT_INDEX_PATTERN, call.data))
def choose_event(call):
    message = call.message
    event_index, curr_page = [int(i) for i in call.data.split("_") if i.isdigit()]
    event = UserEvent.objects.filter(id=event_index)
    if not event.exists():
        events = UserEvent.objects.filter(user__tg_id=message.chat.id).order_by("remind_time")
        message_text, keyboard = paginate_events(events, page=curr_page)
        return bot.edit_message_text(message_text, message.chat.id, message.message_id, reply_markup=keyboard, parse_mode="HTML")
    event = event[0]
    localized_time = localize_time(datetime.combine(date.today(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info).time()
    message_text = ph.READ_EVENT_TEMPLATE % (event.title, localized_time.strftime("%H:%M"), event.times)
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    buffer.add_or_change(buffer_key, event)
    buffer_key = f"{message.chat.id}_events_current_page"
    buffer.add_or_change(buffer_key, curr_page)

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
            types.InlineKeyboardButton(text="✏️", callback_data="edit_event"),
            CANCEL_INLINE_BUTTON,
            types.InlineKeyboardButton(text="️↩️", callback_data="go_back_read_event")
    )

    return bot.edit_message_text(message_text, message.chat.id, message.message_id, reply_markup=keyboard, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "go_back_read_event")
def event_read_go_back(call):
    message = call.message
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_events_current_page"
    curr_page = buffer.get(buffer_key)
    events = UserEvent.objects.filter(user__tg_id=message.chat.id).order_by("remind_time")
    message_text, keyboard = paginate_events(events, page=curr_page)
    return bot.edit_message_text(message_text, message.chat.id, message.message_id, reply_markup=keyboard, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "edit_event")
def event_edit(call):
    message = call.message
    # buffer = Buffer()
    # buffer_key = f"{message.chat.id}_event_read"
    # event = buffer.get(buffer_key)
    # buffer_key = f"{message.chat.id}_events_current_page"
    # buffer.get(buffer_key)

    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    event = buffer.get(buffer_key)

    localized_time = localize_time(datetime.combine(date.today(), time(hour=event.remind_time.hour, minute=event.remind_time.minute)), timezone=event.user.tz_info).time()
    message_text = '<i>{}</i> ({}) кол-во повторений: {}\n\n'.format(event.title, localized_time.strftime("%H:%M"), event.times) + ph.EDIT_EVENT_TEXT

    keyboard = types.InlineKeyboardMarkup()
    keyboard.row(
            types.InlineKeyboardButton(text="📝", callback_data="edit_event_title"),
            types.InlineKeyboardButton(text="🕐", callback_data="edit_event_remind_time"),
            types.InlineKeyboardButton(text="🔂", callback_data="edit_event_times"),
            CANCEL_INLINE_BUTTON,
            types.InlineKeyboardButton(text="️↩️", callback_data="go_back_edit_event"),
    )

    return bot.edit_message_text(message_text, message.chat.id, message.message_id, reply_markup=keyboard, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "go_back_edit_event")
def go_back_edit_event(call):
    message = call.message
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    event = buffer.get(buffer_key)
    buffer_key = f"{message.chat.id}_events_current_page"
    curr_page = buffer.get(buffer_key)

    call.data = f"{event.id}_{curr_page}"

    return choose_event(call)


@bot.callback_query_handler(func=lambda call: call.data == "edit_event_remind_time")
def edit_event_remind_time(call):
    message = call.message
    bot.delete_message(message.chat.id, message.message_id)
    answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_TIME, parse_mode="HTML")
    bot.register_next_step_handler(answer_message, handle_edit_event_remind_time)
    return answer_message

def handle_edit_event_remind_time(message):
    time_pattern = r"([0-1][0-9]|2[0-3]):[0-5][0-9]$"
    if re.match(time_pattern, message.text):
        buffer = Buffer()
        buffer_key = f"{message.chat.id}_event_read"
        event = buffer.get(buffer_key)
        buffer_key = f"{message.chat.id}_events_current_page"
        curr_page = buffer.get(buffer_key)
        hours = int(message.text.split(':')[0])
        minutes = int(message.text.split(':')[1])
        event_time = unlocalize_time(datetime.combine(date.today(), time(hour=hours, minute=minutes)), timezone=event.user.tz_info).time()
        event.remind_time = event_time
        event.save()

        return show_events(message, curr_page)
    else:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIME)
        bot.register_next_step_handler(answer_message, handle_edit_event_remind_time)
        return answer_message


@bot.callback_query_handler(func=lambda call: call.data == "edit_event_title")
def edit_event_title(call):
    message = call.message
    
    bot.delete_message(message.chat.id, message.message_id)
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    event = buffer.get(buffer_key)
    answer_message = bot.send_message(message.chat.id, ph.ENTER_EDIT_EVENT_TITLE % event.title, parse_mode="HTML")
    bot.register_next_step_handler(answer_message, handle_edit_event_title)
    return answer_message

def handle_edit_event_title(message):
    if len(message.text) > 256:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TITLE, parse_mode="HTML")
        bot.register_next_step_handler(answer_message, handle_edit_event_title)
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    event = buffer.get(buffer_key)
    buffer_key = f"{message.chat.id}_events_current_page"
    curr_page = buffer.get(buffer_key)
    event.title = message.text
    event.save()

    return show_events(message, curr_page)


@bot.callback_query_handler(func=lambda call: call.data == "edit_event_times")
def edit_event_remind_times(call):
    message = call.message
    bot.delete_message(message.chat.id, message.message_id)
    answer_message = bot.send_message(message.chat.id, ph.ENTER_EVENT_REMIND_TIMES, parse_mode="HTML")
    bot.register_next_step_handler(answer_message, handle_edit_event_remind_times)
    return answer_message

def handle_edit_event_remind_times(message):
    try:
        times = int(message.text)
        if not 0 < times < 999999999:
            raise ValueError("Invalid number")
    except:
        answer_message = bot.send_message(message.chat.id, ph.INVALID_TIMES)
        bot.register_next_step_handler(answer_message, handle_edit_event_remind_times)
        return answer_message
    
    buffer = Buffer()
    buffer_key = f"{message.chat.id}_event_read"
    event = buffer.get(buffer_key)
    buffer_key = f"{message.chat.id}_events_current_page"
    curr_page = buffer.get(buffer_key)
    event.times = times
    event.save()

    return show_events(message, curr_page)

