# Generated by Django 3.0 on 2019-12-14 17:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subscriptions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=256)),
                ('users', models.ManyToManyField(blank=True, related_name='subscriptions', to='bot.TgUser', verbose_name='Subscriptions')),
            ],
        ),
    ]