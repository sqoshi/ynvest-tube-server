import uuid

from django.db.models import CASCADE
from django.db import models


class Video(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.TextField(null=True)
    link = models.TextField(null=False)


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


class Auction(models.Model):
    id = models.AutoField(primary_key=True)
    state = models.TextField(choices=(("ACTIVE", "active"), ("EXPIRED", "expired")))
    bet = models.IntegerField()
    video_id = models.ForeignKey(Video, on_delete=CASCADE)


class Transaction(models.Model):
    id = models.AutoField(primary_key=True)
    video_id = models.ForeignKey(User, on_delete=CASCADE)
    auction_id = models.ForeignKey(Auction, on_delete=CASCADE)
