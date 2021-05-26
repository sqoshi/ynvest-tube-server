import datetime
import random
from typing import List

from ynvest_tube_server import celery_app
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import Auction, Video, Rent, User


def _set_video_rented(video: Video, value=True) -> None:
    """
    Set video state as rented

    """
    video.rented = value
    video.save()


def _assign_rent(auction: Auction) -> None:
    """
    Handle rent in system

    """
    r = Rent(auction=auction, user=auction.last_bidder)
    r.save()


def _settle_user(user: User, value: int) -> None:
    """
    Reduce user cash

    """
    user.cash += value
    user.save()


@celery_app.task(name='close_expired_auctions')
def close_expired_auctions() -> None:
    """
    Periodic task close auctions that the expiry date has passed.
    by:
            - changing auction state to inactive
            - assign auction to winning user by adding rent to Rent table or passing on none participants
            - charges user wallet


    :interval very often 1 per 1 s

    """
    print("Searching for closeable auctions...")
    auctions = Auction.objects.filter(state='active', auction_expiration_date__lte=datetime.datetime.now())

    for a in auctions:
        a.state = 'inactive'
        # a.video_views_on_sold = a.video.views
        u = a.last_bidder
        if u is not None:
            _set_video_rented(a.video)
            _assign_rent(a)
            _settle_user(u, -a.last_bid_value)
        a.save()

    print(f"Closed {len(auctions)} auctions. List: \n {[x for x in auctions]}.")


@celery_app.task(name='generate_auction')
def generate_auction() -> None:
    """
    Generates random auction with random video.

    auction cost = 1-5 % of current video views

    rent duration = random between 1 hour and 7 days

    each auction lasts 15 minutes

    max auctions = 10

    :interval 1 call per 1800 s
    """
    active_auctions = Auction.objects.filter(state='active', rental_expiration_date__gt=datetime.datetime.now())
    if len(active_auctions) < 10:
        print(f"Generating auction #{len(Auction.objects.all())} ...")

        videos_not_rented = Video.objects.all().filter(rented=False)
        v = random.choice(videos_not_rented)

        random_time_delta = datetime.timedelta(days=random.randint(0, 6), hours=random.randint(1, 24))
        auction = Auction(starting_price=random.randint(int(1 / 100 * v.views), int(5 / 100 * v.views)),
                          video=v,
                          rental_duration=random_time_delta,
                          auction_expiration_date=datetime.datetime.now() + datetime.timedelta(minutes=15),
                          rental_expiration_date=datetime.datetime.now() + random_time_delta,
                          video_views_on_sold=v.views)
        auction.save()

        print(f"Generated auction #{len(Auction.objects.all()) - 1}.")


def _collect_videos_statistics(objects: List, result_limit: int = 50) -> List:
    """
    Calls youtube API to collect data about videos statistics in objects list.

    response limit result is 50, so we need to call api len(video_rows)/50 times

    :param objects: list of videos
    :param result_limit: youtube api limits result rows to 50

    :return: List of dictionaries containing statistics about each video in objects list
    """
    videos_statistics = []
    iterations_ = len(objects)

    for i in range(result_limit, iterations_ + result_limit, result_limit):
        upper_limit = iterations_ if i > iterations_ else i
        videos_id_str = ','.join([x.link for x in objects[i - result_limit:upper_limit]])
        response = youtube.videos().list(id=videos_id_str, part='statistics').execute()
        videos_statistics.extend(response['items'])

    return videos_statistics


@celery_app.task(name='update_video_views')
def update_videos_views() -> None:
    """
    Updates statistics views, likes and dislikes of each video in database via youtube data api v3.

    For now user's cash is being increased by views difference. (rent start, rent end)

    :interval 1 call per day
    """
    print("Updating videos statistics...")

    objects = list(Video.objects.all())
    videos_statistics = _collect_videos_statistics(objects)

    for obj, stats in zip(objects, videos_statistics):
        stats = stats['statistics']
        obj.likes = stats['likeCount']
        obj.dislikes = stats['dislikeCount']
        obj.views = stats['viewCount']
        obj.save()

    print(f"Updated {len(objects)} videos statistics.")


@celery_app.task(name='settle_rents')
def settle_users_rents() -> None:
    """
    When user rent expires it comes to a payday and he gets settled.

    :interval 1 call per 1 s
    """
    print(f'Settling rents...')
    rents = list(Rent.objects.filter(auction__rental_expiration_date__lte=datetime.datetime.now()))
    for r in rents:
        u, a, v = r.user, r.auction, r.auction.video
        views_diff = v.views - a.video_views_on_sold
        print(f'Video `{v.title}` views increased by {views_diff}.')

        _settle_user(u, views_diff)
        _set_video_rented(v, False)

        r.state = 'inactive'
        r.save()

    print(f'Settled {len(rents)} rents.')
