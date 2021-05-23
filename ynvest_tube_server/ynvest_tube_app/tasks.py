import datetime
import random

from ynvest_tube_server import celery_app
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import Auction, Video, Rent


@celery_app.task(name='close_expired_auctions')
def close_expired_auctions():
    def store_rent(auction):
        print('Saving rent...')
        # set video as rented
        v = a.video
        v.rented = True
        v.save()

        r = Rent(auction=auction, user=auction.last_bidder)
        r.save()
        print('Saved rent.')

    # very often 1 per 1 s
    print("Searching for closeable auctions...")
    auctions = Auction.objects.filter(state='active', auction_expiration_date__lte=datetime.datetime.now())
    # auctions.update(state='inactive')
    for a in auctions:
        a.state = 'inactive'
        # a.video_views_on_sold = a.video.views
        u = a.last_bidder
        if u is not None:
            # handle rent in system
            store_rent(a)
            # reduce user cash
            u.cash -= a.last_bid_value
            u.save()

    for a in auctions:
        a.save()

    print(f"Closed {len(auctions)} auctions. List: \n {auctions}.")


@celery_app.task(name='generate_auction')
def generate_auction():
    # 1 call per 1800 s
    print(f"Generating auction nr {len(Auction.objects.all())}...")
    active_auctions = Auction.objects.filter(state='active', rental_expiration_date__gt=datetime.datetime.now())
    if len(active_auctions) < 10:
        video_all = Video.objects.all().filter(rented=False)
        v = random.choice(video_all)

        random_time_delta = datetime.timedelta(days=random.randint(0, 7), hours=random.randint(0, 24))
        auction = Auction(starting_price=random.randint(200, 5000),
                          video=v,
                          rental_duration=random_time_delta,
                          auction_expiration_date=datetime.datetime.now() + datetime.timedelta(minutes=15),
                          rental_expiration_date=datetime.datetime.now() + random_time_delta,
                          video_views_on_sold=v.views)
        auction.save()
    print(f"Generated auction nr {len(Auction.objects.all())}.")


@celery_app.task(name='update_video_views')
def update_video_views():
    # NOTE: max  1 call / 9s
    print("Updating videos statistics...")
    objects = list(Video.objects.all())
    videos_id_str = ','.join([x.link for x in objects])
    video_statistics = youtube.videos().list(id=videos_id_str, part='statistics').execute()
    for obj, stats in zip(objects, video_statistics['items']):
        stats = stats['statistics']
        obj.likes = stats['likeCount']
        obj.dislikes = stats['dislikeCount']
        obj.views = stats['viewCount']

    for o in objects:
        o.save()

    print("Finished videos statistics update.")


@celery_app.task(name='settle_rents')
def settle_users_rents():
    print(f'Settling rents...')
    rents = list(Rent.objects.all())

    # todo maybe a little optimized by changing all to filter above
    for r in rents:
        u = r.user
        a = r.auction
        v = r.auction.video
        if a.rental_expiration_date <= datetime.datetime.now():
            r.state = 'inactive'
            views_diff = v.views - a.video_views_on_sold
            print(f'Video earned {views_diff} views.')
            u.cash += views_diff
            u.save()

            v.rented = False
            r.save()
    print(f'Settled rents.')
