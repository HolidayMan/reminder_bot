# Generated by Django 3.0 on 2019-12-14 19:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0005_auto_20191214_1847'),
    ]

    operations = [
        migrations.CreateModel(
            name='MailingArcticle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.CharField(max_length=4096)),
                ('remind_time', models.TimeField(blank=True, verbose_name='Remind Time')),
                ('remind', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterField(
            model_name='userevent',
            name='remind_time',
            field=models.TimeField(blank=True, verbose_name='Remind Time'),
        ),
    ]
