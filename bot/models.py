from django.db import models

class TgUser(models.Model):
    tg_id = models.IntegerField()
    first_name = models.CharField(max_length=64, blank=True, null=True)
    username = models.CharField(max_length=64, blank=True, null=True)
    admin = models.BooleanField(blank=True)
    tz_info = models.CharField(max_length=5, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.username:
            return self.username
        else:
            return str(self.id)

class Subscriptions(models.Model):
    title = models.CharField(max_length=256)
    users = models.ManyToManyField("TgUser", blank=True, related_name="subscriptions", verbose_name="Subscriptions")

    def __str__(self):
        return self.title
        

class UserEvent(models.Model):
    title = models.CharField(max_length=256, blank=True)
    remind_time = models.TimeField(verbose_name="Remind Time", blank=True)
    times = models.IntegerField(blank=True)
    user = models.ForeignKey("TgUser", on_delete=models.CASCADE, related_name="events", blank=False)

    def __str__(self):
        return self.title


class MailingArcticle(models.Model):
    body = models.CharField(max_length=4096)
    remind_time = models.TimeField(verbose_name="Remind Time", blank=True)
    remind = models.BooleanField(default=True)
