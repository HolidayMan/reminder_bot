from django.contrib import admin
from .models import *

@admin.register(TgUser)
class TgUserAdmin(admin.ModelAdmin):
    list_display = ("id", "tg_id", "first_name", "username", "admin", "tz_info", "date_joined")

