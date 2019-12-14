import telebot
import logging

from telebot import types

from reminder_bot.settings import TOKEN

from .models import TgUser
import bot.phrases as ph
from .utils import user_exists


bot = telebot.TeleBot(TOKEN)

from .handlers import tz_handler, MAIN_KEYBOARD
from .mailing import *
logger = telebot.logger
logging.basicConfig(filename='bot.log', filemode='a', format='%(asctime)s:%(name)s - %(message)s')
# telebot.logger.setLevel(logging.DEBUG)


@bot.message_handler(commands=['start'])
def cmd_start(message: telebot.types.Message):
    if message.chat.type != "private":
        bot.send_message(message.chat.id, ph.BOT_WORKS_IN_PRIVATE_CHAT_ONLY)
        return 
    if not user_exists(message):
        new_user = TgUser.objects.create(tg_id=message.chat.id, 
                        first_name=message.chat.first_name, 
                        username=message.chat.username, 
                        admin=False
                        )
        answer_message = bot.send_message(message.chat.id, ph.ENTER_YOUR_TIMEZONE, reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(answer_message, tz_handler)
        return answer_message
        

    return bot.reply_to(message, 'Hello, I\'m bot!')


bot.enable_save_next_step_handlers(delay=1)
bot.load_next_step_handlers()