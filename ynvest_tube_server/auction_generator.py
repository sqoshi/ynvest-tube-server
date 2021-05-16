import datetime
import random

from ynvest_tube_server.ynvest_tube_app.models import Auction, Video


def generate_auction():
    v = Video(name=f"video_{datetime.date.today()}",
              link=f"video_link_{datetime.date.today()}",
              views=100000)
    v.save()
    random_time_delta = datetime.timedelta(days=random.randint(0, 7), hours=random.randint(0, 24))
    auction = Auction(starting_price=random.randint(200, 5000),
                      video=v,
                      rental_duration=random_time_delta,
                      rental_expiration_date=datetime.datetime.now() + random_time_delta)
    auction.save()
