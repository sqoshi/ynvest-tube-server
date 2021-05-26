import datetime
import uuid
from typing import Dict

from dirtyfields import DirtyFieldsMixin
from django.db.models import CASCADE, ForeignKey
from django.db import models


class Serializable:
    """
    Interface provides object serialization.

    """

    def serialize(self: models.Model) -> Dict:
        """
        Converts model to python dictionary.

        :return: dict with keys as object fields and its values.
        """
        dictionary = {}
        for field in self._meta.fields:
            value = self.__getattribute__(field.name)
            dictionary[field.name] = value.serialize() if isinstance(field, ForeignKey) and value is not None else value
        return dictionary


class Video(models.Model, Serializable):
    """
    Model represents youtube video.

    """
    id = models.AutoField(primary_key=True)
    title = models.TextField(null=True)
    description = models.TextField(null=True)
    link = models.TextField(null=False)
    views = models.IntegerField(null=True, default=None)
    likes = models.IntegerField(null=True, default=None)
    dislikes = models.IntegerField(null=True, default=None)
    rented = models.BooleanField(default=False)


class User(models.Model, Serializable):
    """
    Model represents User identified by UUID.

    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cash = models.IntegerField(default=1000, null=False)
    creation_date = models.DateTimeField(auto_now=True)


class Auction(models.Model, DirtyFieldsMixin, Serializable):
    """
    Model represents auctions and stores details about it.

    """
    id = models.AutoField(primary_key=True)
    state = models.TextField(default="active", choices=(("ACTIVE", "active"), ("INACTIVE", "inactive")))
    starting_price = models.IntegerField(null=False)
    last_bid_value = models.IntegerField(null=True, default=None)
    last_bidder = models.ForeignKey(User, null=True, default=None, on_delete=CASCADE)
    video = models.ForeignKey(Video, on_delete=CASCADE)
    rental_duration = models.DurationField()
    # rental_begin_date = models.DateTimeField(auto_now=True)
    auction_expiration_date = models.DateTimeField(default=datetime.datetime.now() - datetime.timedelta(days=10))
    rental_expiration_date = models.DateTimeField()
    video_views_on_sold = models.IntegerField(null=True, default=None)


class Rent(models.Model, DirtyFieldsMixin, Serializable):
    """
    Model represents transaction between user and server.

    """
    id = models.AutoField(primary_key=True)
    auction = models.ForeignKey(Auction, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=CASCADE)
    state = models.TextField(default="active", choices=(("ACTIVE", "active"), ("INACTIVE", "inactive")))


class Bids(models.Model):
    """
    Stores all bids.

    Using this model we can see the list of users that participated in auction.
    """
    id = models.AutoField(primary_key=True)
    auction = models.ForeignKey(Auction, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=CASCADE)
    value = models.IntegerField(null=False)
