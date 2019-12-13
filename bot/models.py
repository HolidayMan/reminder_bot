from django.db import models

class TgUser(models.Model):
    tg_id = models.IntegerField()
    first_name = models.CharField(max_length=64)
    username = models.CharField(max_length=64)
    admin = models.BooleanField(blank=True)
    tz_info = models.CharField(max_length=5, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

