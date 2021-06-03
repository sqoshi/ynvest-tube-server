import random
import sys
from typing import List

from django.utils import timezone

from ynvest_tube_server import celery_app
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import Auction, Video, Rent, User


def _set_video(video: Video, state: str) -> None:
    """
    Set video state.

    """
    video.state = state
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
    auctions = Auction.objects.filter(state='active', auction_expiration_date__lte=timezone.now())

    if auctions:
        print("Searching for closeable auctions...")
    for a in auctions:
        a.state = 'inactive'
        # a.video_views_on_sold = a.video.views
        u = a.last_bidder
        if u is not None:
            _set_video(a.video, "rented")
            _assign_rent(a)
            # _settle_user(u, -a.last_bid_value)
        else:
            _set_video(a.video, "available")
        a.save()
    if auctions:
        print(f"Closed {len(auctions)} auctions. \nList of closed videos: \n {[x.video.title for x in auctions]}.")


@celery_app.task(name='generate_auction')
def generate_auction(max_auctions=10) -> None:
    """
    Generates random auction with random video.

    auction cost = random between 200 and 500 coins  [[OLD]1-5 % of current video views]

    rent duration = random between 1 hour and 7 days

    each auction lasts between 15 and 20 minutes

    max auctions = 10

    :interval 1 call per 1800 s
    """
    minutes = random.randint(10, 20)
    auction_timedelta = timezone.timedelta(minutes=minutes)
    active_auctions = Auction.objects.filter(state='active', rental_expiration_date__gt=timezone.now())
    if len(active_auctions) < max_auctions:
        new_auction_id = len(Auction.objects.all())
        print(f"Generating auction #{new_auction_id} ...")

        available_videos = Video.objects.all().filter(state='available')
        if available_videos:
            v = random.choice(available_videos)
            _set_video(v, "auctioned")

            random_time_delta = timezone.timedelta(days=random.randint(0, 6), hours=random.randint(1, 24))
            auction = Auction(starting_price=random.randint(200, 500),
                              # random.randint(int(1 / 100 * v.views), int(5 / 100 * v.views)),
                              video=v,
                              rental_duration=random_time_delta,
                              auction_expiration_date=timezone.now() + auction_timedelta,
                              rental_expiration_date=timezone.now() + random_time_delta,
                              video_views_on_sold=v.views)
            auction.save()

            print(f"Generated auction #{new_auction_id}. Auctioned video: {v.title}")
        else:
            print(f"Auction #{new_auction_id} generation failed. \nReason: `No available videos in database`")


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


def _deactivate_rent(rent: Rent, views_diff: int) -> None:
    """
    Deactivate rent in system

    """
    rent.state = 'inactive'
    rent.profit = views_diff - rent.auction.last_bid_value
    rent.save()


@celery_app.task(name='settle_rents')
def settle_users_rents() -> None:
    """
    When user rent expires it comes to a payday and he gets settled.

    :interval 1 call per 1 s
    """
    rents = list(Rent.objects.filter(auction__rental_expiration_date__lte=timezone.now(), state='active'))
    if rents:
        print(f'Settling rents...')

    for r in rents:
        u, a, v = r.user, r.auction, r.auction.video
        views_diff = v.views - a.video_views_on_sold
        print(f'Video `{v.title}` views increased by {views_diff}.')

        _settle_user(u, views_diff)
        _set_video(v, "available")
        _deactivate_rent(r, views_diff)

    if rents:
        print(f'Settled {len(rents)} rents.')


def _choose_loyalty_degree(days: int, max_level=6, cash_base: int = 500, interval_base: int = 30) -> int:
    """
    Designates payout by specifying the degree of loyalty

    :param days: since user registration
    :param max_level: loyalty max level
    :return: payout value
    """
    loyalty_payout = [cash_base * i for i in range(1, max_level)]
    loyalty_period = [interval_base * i for i in range(max_level)] + [sys.maxsize]
    for p, v in zip(loyalty_period, loyalty_payout):
        if days < p:
            return v
    return 0


@celery_app.task(name='payout_loyalty_cash')
def payout_loyalty_cash() -> None:
    """
    Periodically payouts loyal free cash.

    Counts since registration.

    :interval 1 call per 7 days
    """
    users = User.objects.all()
    for u in users:
        d = (timezone.now() - u.creation_date).days
        _settle_user(u, _choose_loyalty_degree(d))
