import datetime
import random
import uuid
from typing import Dict

from dirtyfields import DirtyFieldsMixin
from django.db.models import CASCADE, ForeignKey, Max
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
    name = models.TextField(null=True)
    link = models.TextField(null=False)
    views = models.IntegerField(null=False)
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
    Model represents auctions and stores information about it.

    """
    id = models.AutoField(primary_key=True)
    state = models.TextField(default="active", choices=(("ACTIVE", "active"), ("INACTIVE", "inactive")))
    starting_price = models.IntegerField(null=False)
    last_bid_value = models.IntegerField(null=True, default=None)
    last_bidder = models.ForeignKey(User, null=True, default=None, on_delete=CASCADE)
    video = models.ForeignKey(Video, on_delete=CASCADE)
    rental_duration = models.DurationField()
    # rental_begin_date = models.DateTimeField(auto_now=True)
    rental_expiration_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        if self.is_dirty() and 'state' in self.get_dirty_fields():
            print(type(self.get_dirty_fields()))
            print(self.get_dirty_fields())
            auctions_quantity = Auction.objects.filter(state="active").count()
            while auctions_quantity < 10:
                generate_auction()
        super().save(*args, **kwargs)
        print(Auction.objects.filter(state="active").count())


class Rent(models.Model, DirtyFieldsMixin, Serializable):
    """
    Model represents transaction between user and server.

    """
    id = models.AutoField(primary_key=True)
    auction = models.ForeignKey(Auction, on_delete=CASCADE)
    user = models.ForeignKey(User, on_delete=CASCADE)

    def save(self, *args, **kwargs):
        print(self.get_dirty_fields())
        print(self.get_dirty_fields().get('auction'))
        # change
        super().save(*args, **kwargs)


#########################################################33

def generate_auction():
    print(f"Generating auction")
    # v = Video(name=f"video_{datetime.date.today()}",
    #           link=f"video_link_{datetime.date.today()}",
    #           views=100000)
    video_all = Video.objects.all().filter(rented=False)
    v = random.choice(video_all)

    # v.save()
    random_time_delta = datetime.timedelta(days=random.randint(0, 7), hours=random.randint(0, 24))
    auction = Auction(starting_price=random.randint(200, 5000),
                      video=v,
                      rental_duration=random_time_delta,
                      rental_expiration_date=datetime.datetime.now() + random_time_delta)
    auction.save()
