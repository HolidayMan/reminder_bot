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

class Subscriptions(models.Model):
    title = models.CharField(max_length=256)
    users = models.ManyToManyField("TgUser", blank=True, related_name="subscriptions", verbose_name="Subscriptions")

    def __str__(self):
        return self.title
        