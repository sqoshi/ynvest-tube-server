# Generated by Django 3.2.3 on 2021-05-22 20:33

import dirtyfields.dirtyfields
from django.db import migrations, models
import django.db.models.deletion
import uuid
import ynvest_tube_server.ynvest_tube_app.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Auction',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('state', models.TextField(choices=[('ACTIVE', 'active'), ('INACTIVE', 'inactive')], default='active')),
                ('starting_price', models.IntegerField()),
                ('last_bid_value', models.IntegerField(default=None, null=True)),
                ('rental_duration', models.DurationField()),
                ('rental_expiration_date', models.DateTimeField()),
            ],
            bases=(models.Model, dirtyfields.dirtyfields.DirtyFieldsMixin, ynvest_tube_server.ynvest_tube_app.models.Serializable),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('cash', models.IntegerField(default=1000)),
                ('creation_date', models.DateTimeField(auto_now=True)),
            ],
            bases=(models.Model, ynvest_tube_server.ynvest_tube_app.models.Serializable),
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.TextField(null=True)),
                ('link', models.TextField()),
                ('views', models.IntegerField()),
                ('rented', models.BooleanField(default=False)),
            ],
            bases=(models.Model, ynvest_tube_server.ynvest_tube_app.models.Serializable),
        ),
        migrations.CreateModel(
            name='Rent',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('auction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ynvest_tube_app.auction')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ynvest_tube_app.user')),
            ],
            bases=(models.Model, dirtyfields.dirtyfields.DirtyFieldsMixin, ynvest_tube_server.ynvest_tube_app.models.Serializable),
        ),
        migrations.AddField(
            model_name='auction',
            name='last_bidder',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='ynvest_tube_app.user'),
        ),
        migrations.AddField(
            model_name='auction',
            name='video',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='ynvest_tube_app.video'),
        ),
    ]
