import datetime
import os
import random

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ynvest_tube_server.settings")

django.setup()


from ynvest_tube_server.ynvest_tube_app.models import Video, Auction


def generate_auction():
    print(f"Generating auction")
    v = Video(name=f"video_{datetime.date.today()}",
              link=f"video_link_{datetime.date.today()}",
              views=random.randint(10000, 10000000))

    v.save()
    random_time_delta = datetime.timedelta(days=random.randint(0, 7), hours=random.randint(0, 24))
    auction = Auction(starting_price=random.randint(200, 5000),
                      video=v,
                      rental_duration=random_time_delta,
                      rental_expiration_date=datetime.datetime.now() + random_time_delta)
    auction.save()


generate_auction()
