import uuid
from typing import Dict

from django.db.models import CASCADE
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
            dictionary[field.name] = self.__getattribute__(field.name)
        return dictionary


class Video(models.Model, Serializable):
    """
    Model represents youtube video.

    """
    id = models.AutoField(primary_key=True)
    name = models.TextField(null=True)
    link = models.TextField(null=False)


class User(models.Model, Serializable):
    """
    Model represents User identified by UUID.

    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


class Auction(models.Model, Serializable):
    """
    Model represents auctions and stores information about it.

    """
    id = models.AutoField(primary_key=True)
    state = models.TextField(choices=(("ACTIVE", "active"), ("EXPIRED", "expired")))
    bet_value = models.IntegerField()
    last_bidder = models.TextField(null=True, default=None)
    video_id = models.ForeignKey(Video, on_delete=CASCADE)


class Transaction(models.Model, Serializable):
    """
    Model represents transaction between user and server.

    """
    id = models.AutoField(primary_key=True)
    video_id = models.ForeignKey(User, on_delete=CASCADE)
    auction_id = models.ForeignKey(Auction, on_delete=CASCADE)
