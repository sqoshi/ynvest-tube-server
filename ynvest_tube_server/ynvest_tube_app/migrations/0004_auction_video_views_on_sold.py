# Generated by Django 3.2.3 on 2021-05-23 19:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ynvest_tube_app', '0003_auto_20210523_1924'),
    ]

    operations = [
        migrations.AddField(
            model_name='auction',
            name='video_views_on_sold',
            field=models.IntegerField(default=None, null=True),
        ),
    ]
