from django.contrib import admin
from .models import *

@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):
    list_display = ("id", "tg_id", "first_name", "username", "admin", "tz_info", "date_joined")

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "title")


@admin.register(UserEvent)
class UserEventAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "remind_time", "times", "user")


@admin.register(MailingArcticle)
class MailingArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "body", "remind_time", "remind")
    