import telebot
import logging

from telebot import types

from reminder_bot.settings import TOKEN

from .models import TgUser
import bot.phrases as ph
from .utils import user_exists, set_menu_state
from .buffer import Buffer

bot = telebot.TeleBot(TOKEN)

from .handlers import tz_handler, MAIN_KEYBOARD

from reminder_bot.tasks import *


logger = telebot.logger
logging.basicConfig(filename='bot.log', filemode='a', format='%(asctime)s:%(name)s - %(message)s')
# telebot.logger.setLevel(logging.DEBUG)


@bot.message_handler(commands=['start'])
def cmd_start(message: telebot.types.Message):
    if message.chat.type != "private":
        bot.send_message(message.chat.id, ph.BOT_WORKS_IN_PRIVATE_CHAT_ONLY)
        return 
    if not user_exists(message):
        new_user = TgUser(tg_id=message.chat.id)
        if message.chat.username:
            new_user.username = message.chat.username
        if message.chat.first_name:
            new_user.first_name = message.chat.first_name
        if message.chat.last_name:
            new_user.last_name = message.chat.last_name
        new_user.tz_info = "UTC+0"
        new_user.admin = False
        new_user.save()
        answer_message = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(answer_message, tz_handler)
        return answer_message
        

    return bot.reply_to(message, 'Hello, I\'m bot!')


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel(call):
    set_menu_state(call.message.chat.id)
    # clean_buffer(call.message.chat.id)
    buffer = Buffer()
    buffer.clean_for_user(call.message.chat.id)
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id, ph.MENU, reply_markup=MAIN_KEYBOARD)


@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    set_menu_state(message.chat.id)
    buffer = Buffer()
    buffer.clean_for_user(message.chat.id)
    bot.send_message(message.chat.id, ph.MENU, reply_markup=MAIN_KEYBOARD)


bot.enable_save_next_step_handlers(delay=1)
bot.load_next_step_handlers()