import random

from django.utils import timezone

from ynvest_tube_server import celery_app
from ynvest_tube_server.ynvest_tube_app.models import Auction, Video, Rent, User
from ynvest_tube_server.ynvest_tube_app.tasks_service import set_video, assign_rent, collect_videos_statistics, \
    settle_user, choose_loyalty_degree, deactivate_rent


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
        if a.last_bidder is not None:
            set_video(a.video, "rented")
            assign_rent(a)
        else:
            set_video(a.video, "available")
        a.save()
    if auctions:
        print(f"Closed {len(auctions)} auctions. \nList of closed videos: \n {[x.video.title for x in auctions]}.")


@celery_app.task(name='generate_auction')
def generate_auction(max_auctions: int = 10, auction_interval: int = random.randint(5, 30)) -> None:
    """
    Generates random auction with random available video.

    auction cost = random between 200 and 500 coins  [[OLD]1-5 % of current video views]

    rent duration = random between 1 hour and 7 days

    each auction lasts between auction_interval

    max auctions = 10

    :interval 1 call per 1800 s
    """
    auction_timedelta = timezone.timedelta(minutes=auction_interval)
    active_auctions = Auction.objects.filter(state='active', rental_expiration_date__gt=timezone.now())
    if len(active_auctions) < max_auctions:
        new_auction_id = len(Auction.objects.all())
        print(f"Generating auction #{new_auction_id} ...")

        available_videos = Video.objects.all().filter(state='available')
        if available_videos:
            v = random.choice(available_videos)
            set_video(v, "auctioned")

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


@celery_app.task(name='update_video_views')
def update_videos_views() -> None:
    """
    Updates statistics views, likes and dislikes of each video in database via youtube data api v3.

    For now user's cash is being increased by views difference. (rent start, rent end)

    :interval 1 call per day
    """
    print("Updating videos statistics...")

    objects = list(Video.objects.all())
    videos_statistics = collect_videos_statistics(objects)

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
    rents = list(Rent.objects.filter(auction__rental_expiration_date__lte=timezone.now(), state='active'))
    if rents:
        print(f'Settling rents...')

    for r in rents:
        u, a, v = r.user, r.auction, r.auction.video
        views_diff = v.views - a.video_views_on_sold
        print(f'Video `{v.title}` views increased by {views_diff}.')

        settle_user(u, views_diff)
        set_video(v, "available")
        deactivate_rent(r, views_diff)

    if rents:
        print(f'Settled {len(rents)} rents.')


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
        settle_user(u, choose_loyalty_degree(d))
