import random
from typing import Optional

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import User, Auction, Rent, Video, Bids
from ynvest_tube_server.ynvest_tube_app.tasks import settle_user
from ynvest_tube_server.ynvest_tube_app.views_helpers.auction import extend_auctions_data, specify_relation, \
    check_auction_post_request_requirements
from ynvest_tube_server.ynvest_tube_app.views_helpers.shared import load_data_from, serialize_query_set
from ynvest_tube_server.ynvest_tube_app.views_helpers.video import get_random_words, fix_punctuation_marks

wrong_method_response = JsonResponse({"summary": "Used request method is not allowed for this endpoint."}, status=405)


def register_user(request: WSGIRequest) -> Optional[JsonResponse]:
    """
    Register new user in database. ( uuid generator)

    """
    if request.method == "GET":
        new_user = User()
        new_user.save()
        data = {
            "summary": "Successfully registered new user",
            "userId": new_user.id,
        }
        return JsonResponse(data, status=200)
    return wrong_method_response


@csrf_exempt
def get_user(request: WSGIRequest) -> JsonResponse:
    """
    Gets specified user.

    :param request: wsgi request
    """
    if request.method == "POST":
        user_id = load_data_from(request, "UserId")
        u = User.objects.all().filter(id=user_id).first()
        data = {
            "summary": "Get user",
            "user": u.serialize()
        }
        return JsonResponse(data, status=200)
    return wrong_method_response


@csrf_exempt
def get_user_details(request: WSGIRequest) -> Optional[JsonResponse]:
    """
    Display detailed data about user
            - cash
            - attendingAuctions - all auctions that user actually participate in
            - rents - history

    """
    if request.method == "POST":
        user_id = load_data_from(request, "UserId")

        # auctions in which user participate at the moment
        u = User.objects.all().filter(id=user_id).first()
        auctions = Auction.objects.all().filter(last_bidder=u, state="active")

        # user rents
        active_rents = Rent.objects.filter(user=u, state='active')
        inactive_rents = Rent.objects.filter(user=u, state='inactive')

        data = {
            "summary": "Get user actual auctions and all his rents.",
            "cash": u.cash,
            "attendingAuctions": serialize_query_set(auctions),  # wrong name need to be changed
            "actualRents": serialize_query_set(active_rents),
            "expiredRents": serialize_query_set(inactive_rents)
        }
        return JsonResponse(data, status=200)
    return wrong_method_response


@csrf_exempt
def get_auctions(request: WSGIRequest) -> JsonResponse:
    """
    List all auctions existed in database.

    """
    if request.method == "POST":
        auctions = Auction.objects.all()
        user_id = load_data_from(request, "UserId")

        data = {
            "summary": "Get all auctions",
            "activeAuctions": extend_auctions_data(auctions.filter(state="active"), user_id),
            "inactiveAuctions": serialize_query_set(auctions.filter(state="inactive")),
        }
        return JsonResponse(data, status=200, safe=False)

    if request.method == "GET":
        auctions = Auction.objects.all()

        data = {
            "summary": "Get all auctions",
            "activeAuctions": serialize_query_set(auctions.filter(state="active")),
            "inactiveAuctions": serialize_query_set(auctions.filter(state="inactive")),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


def _settle_auctioneers(user: User, auction: Auction, bid_value: int) -> None:
    """
    Every bid triggers
        - current bidder cash reduction,
        - reimbursement to the previous user (last bidder)

    :param user: currently bidding user
    :param auction: aimed auction
    :param bid_value: new bid value of current user (piercing bid)
    """
    settle_user(user, -bid_value)
    if auction.last_bidder:
        settle_user(auction.last_bidder, auction.last_bid_value)


@csrf_exempt
def get_auction(request: WSGIRequest, auction_id: int) -> JsonResponse:
    """
    On GET request returns specific auction

    On POST request changes last bidder, and bet value.

    :param request: wsgi request
    :param auction_id: auction id

    """
    auction_query = Auction.objects.all().filter(id=auction_id)
    auction = auction_query.first()
    if request.method == "POST":
        user_id = load_data_from(request, "UserId")
        auction_bidders = Bids.objects.all().filter(auction=auction).values_list('user').distinct()
        serialized_auction = auction.serialize()
        serialized_auction["user_contribution"] = specify_relation((auction, user_id))

        data = {
            "summary": "Get auction",
            "auctionBiddersCount": int(auction_bidders.count()),
            "auction": serialized_auction,
        }

        return JsonResponse(data, status=200)

    elif request.method == "PUT":
        user_id, bid_value = load_data_from(request, "UserId", "bidValue")
        user_query = User.objects.all().filter(id=user_id)
        error_response, error_status = check_auction_post_request_requirements(auction, user_query, bid_value)
        if error_response and error_status:
            return JsonResponse(error_response, status=error_status)
        else:
            u = user_query.first()
            Bids(auction=auction, user=u, value=bid_value).save()
            # auction_query.update(last_bidder=u, last_bid_value=bid_value)
            _settle_auctioneers(u, auction, bid_value)
            auction.last_bidder = u
            auction.last_bid_value = bid_value
            auction.save()
            data = {
                "summary": "Successfully bid on auction",
                "auction": auction.serialize()
            }
            return JsonResponse(data, status=200)
    return wrong_method_response


##################################################### DEVELOPMENT ######################################################

def get_users(request: WSGIRequest) -> JsonResponse:
    """
    List all users in database.

    """
    if request.method == "GET":
        qs = User.objects.all()
        data = {
            "summary": "Get all users",
            "users": serialize_query_set(qs)
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


@csrf_exempt
def insert_expired_rent(request: WSGIRequest) -> JsonResponse:
    """
    Insert expired rent for user.

    Requires UserId in body

    Creating fake expired auction for random video,.
    User won by bid starting_price + 1, bid is being stored in database.

    :param request: wsgi request
    """
    if request.method == "POST":
        user_id = load_data_from(request, "UserId")
        u = User.objects.all().filter(id=user_id).first()
        v = random.choice(list(Video.objects.all()))
        sp = random.randint(10, 600)
        rtd = timezone.timedelta(days=random.randint(1, 10))
        views_on_sold = v.views - random.randint(int(v.views * 0.75), int(v.views * 0.9))
        a = Auction(state='inactive',
                    starting_price=sp,
                    last_bid_value=sp + 1,
                    last_bidder=u,
                    video=v,
                    rental_duration=rtd,
                    auction_expiration_date=timezone.now() - timezone.timedelta(days=random.randint(7, 10)),
                    rental_expiration_date=timezone.now() - timezone.timedelta(days=random.randint(2, 4)),
                    video_views_on_sold=views_on_sold
                    )
        a.save()
        r = Rent(user=u, auction=a, state='inactive', profit=v.views - views_on_sold - sp + 1)
        r.save()
        b = Bids(auction=a, user=u, value=sp + 1)
        b.save()
        data = {
            "summary": "Inserted expired rent for user.",
            "user": u.serialize(),
            "auction": a.serialize(),
            "rent": r.serialize(),
            "bid": b.serialize(),
        }
        return JsonResponse(data, status=200)
    return wrong_method_response


def get_videos(request: WSGIRequest) -> JsonResponse:
    """
    List all videos existing in database.

    """
    if request.method == "GET":
        videos = Video.objects.all()
        data = {
            "summary": "Get all videos",
            "auctionedVideos": serialize_query_set(videos.filter(state='auctioned')),
            "rentedVideos": serialize_query_set(videos.filter(state='rented')),
            "availableVideos": serialize_query_set(videos.filter(state='available')),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


def get_bids(request: WSGIRequest) -> JsonResponse:
    """
    List all bids existing in database.

    """
    if request.method == "GET":
        bids = Bids.objects.all()
        data = {
            "summary": "Get all bids",
            "allBids": serialize_query_set(bids),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


def get_rents(request: WSGIRequest) -> JsonResponse:
    """
    List all rents existing in database.

    """
    if request.method == "GET":
        active_rents = Rent.objects.all().filter(state='active')
        inactive_rents = Rent.objects.all().filter(state='inactive')
        data = {
            "summary": "Get all rents",
            "activeRents": serialize_query_set(active_rents),
            "inactiveRents": serialize_query_set(inactive_rents),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


@csrf_exempt
def insert_youtube_videos(request: WSGIRequest):
    """
    Insert multiple random youtube videos to database

    :return: redirect to videos list
    """
    print("Inserting videos...")
    args = get_random_words(n=5)
    for el in args:
        req = youtube.search().list(q=el, part='snippet', type='video')
        snippets = req.execute()
        videos_id_string = ','.join([x['id']['videoId'] for x in snippets["items"]])

        video_statistics = youtube.videos().list(id=videos_id_string, part='statistics')
        stats = video_statistics.execute()
        for v_snip, v_stats in zip(snippets["items"], stats["items"]):
            v = Video(title=fix_punctuation_marks(v_snip['snippet']['title']),
                      description=fix_punctuation_marks(v_snip['snippet']['description']),
                      link=v_snip['id']['videoId'],
                      likes=v_stats['statistics']['likeCount'],
                      views=v_stats['statistics']['viewCount'],
                      dislikes=v_stats['statistics']['dislikeCount'],
                      )
            v.save()

        print(f'Inserted videos{[fix_punctuation_marks(v["snippet"]["title"]) for v in snippets["items"]]}')

    return redirect('get_videos')


def close_auction(request: WSGIRequest, auction_id: int) -> JsonResponse:
    """
    Closes auction.

    FIXME: its not working properly

    """
    if request.method == "DELETE":
        auction = Auction.objects.all().filter(id=auction_id)
        auction.update(state="inactive")
        auction = auction.first()

        rent = Rent(user=auction.last_bidder, auction=auction)
        rent.save()
        data = {
            "summary": "Auction closed. Transaction saved in database.",
            "auction": auction.serialize(),
            "rent": rent.serialize()
        }
        return JsonResponse(data, status=200)
    return wrong_method_response
