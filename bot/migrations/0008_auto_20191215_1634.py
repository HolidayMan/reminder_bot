# Generated by Django 3.0 on 2019-12-15 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0007_auto_20191215_1429'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tguser',
            name='username',
            field=models.CharField(blank=True, max_length=64),
        ),
    ]