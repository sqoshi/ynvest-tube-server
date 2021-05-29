import datetime
import json
import random
from typing import Optional, List, Dict

import requests
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import User, Auction, Rent, Video, Bids


def register_user(request: WSGIRequest) -> Optional[HttpResponse]:
    """
    Register new user in database. ( uuid generator)

    """
    if request.method == "GET":
        new_user = User()
        new_user.save()
        data = {
            "summary": "Register new user",
            "userId": new_user.id,
        }
        return JsonResponse(data, status=200)
    return HttpResponse(request, status=405)


def get_user(request: WSGIRequest) -> HttpResponse:
    """
    Gets specified user.

    :param request: wsgi request
    """
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data["UserId"]
        u = User.objects.all().filter(id=user_id).first()
        data = {
            "summary": "Get user",
            "user": u.serialize()
        }
        return JsonResponse(data, status=200)
    return HttpResponse(request, status=403)


def get_user_details(request: WSGIRequest) -> Optional[HttpResponse]:
    """
    Display detailed data about user
            - cash
            - attendingAuctions - all auctions that user actually participate in
            - rents - history

    """
    if request.method == "POST":
        data = json.loads(request.body)
        user_id = data["UserId"]

        # auctions in which user participate at the moment
        u = User.objects.all().filter(id=user_id).first()
        auctions = Auction.objects.all().filter(last_bidder=u, state="active")

        # user rents
        active_rents = Rent.objects.filter(user=u, state='active')
        inactive_rents = Rent.objects.filter(user=u, state='inactive')

        data = {
            "summary": "Get user actual auctions and all his rents.",
            "cash": u.cash,
            "attendingAuctions": _serialize_query_set(auctions),  # wrong name need to be changed
            "actualRents": _serialize_query_set(active_rents),
            "expiredRents": _serialize_query_set(inactive_rents)
        }
        return JsonResponse(data, status=200)
    return HttpResponse(request, status=403)


def get_auctions(request: WSGIRequest) -> HttpResponse:
    """
    List all auctions existed in database.

    """
    if request.method == "GET":
        qs = Auction.objects.all()
        data = {
            "summary": "Get all auctions",
            "activeAuctions": _serialize_query_set(qs.filter(state="active")),
            "inactiveAuctions": _serialize_query_set(qs.filter(state="inactive")),
        }
        return JsonResponse(data, status=200, safe=False)
    return HttpResponse(request, status=405)


@csrf_exempt
def get_auction(request: WSGIRequest, auction_id: int) -> HttpResponse:
    """
    On GET request returns specific auction

    On POST request changes last bidder, and bet value.

    :param request: wsgi request
    :param auction_id: auction id

    """
    qs = Auction.objects.all().filter(id=auction_id)
    if request.method == "GET":
        auction_bidders = Bids.objects.all().filter(auction=qs.first()).values('user').distinct().count()
        data = {
            "summary": "Get auction",
            "auctionBidders": int(auction_bidders),
            "auction": qs.first().serialize(),
        }
        return JsonResponse(data, status=200)

    elif request.method == "POST":
        if qs.first().auction_expiration_date < datetime.datetime.now():
            # auction already ended
            return HttpResponse(request, status=404)

        data = json.loads(request.body)
        user_id = data["UserId"]
        bid_value = int(data["bidValue"])
        u = User.objects.all().filter(id=user_id)
        if len(u) > 0:
            if u.first().cash >= bid_value:
                b = Bids(qs.first(), u, bid_value)
                b.save()
                qs.update(last_bidder=u, last_bid_value=bid_value)
                data = {
                    "summary": "Bet on auction",
                    "auction": qs.first().serialize()
                }
                # success
                return JsonResponse(data, status=200)
            else:
                # not enough money
                return HttpResponse(request, status=400)
    # bad auction / user id
    return HttpResponse(request, status=403)


def _serialize_query_set(query_set: QuerySet) -> List[Dict]:
    """
    Serializes whole query set to list of dicts

    :param query_set: django query set ( 'list' of rows from table )
    :return: list of dictionaries representing database models
    """
    return [obj.serialize() for obj in query_set]


##################################################### DEVELOPMENT ######################################################

def get_users(request: WSGIRequest) -> HttpResponse:
    """
    List all users in database.

    """
    if request.method == "GET":
        qs = User.objects.all()
        data = {
            "summary": "Get all users",
            "users": _serialize_query_set(qs)
        }
        return JsonResponse(data, status=200, safe=False)
    return HttpResponse(request, status=405)


def get_videos(request: WSGIRequest) -> HttpResponse:
    """
    List all videos existing in database.

    """
    if request.method == "GET":
        qs = Video.objects.all()
        data = {
            "summary": "Get all videos",
            "videos": _serialize_query_set(qs),
        }
        return JsonResponse(data, status=200, safe=False)
    return HttpResponse(request, status=405)


def get_rents(request: WSGIRequest) -> HttpResponse:
    """
    List all rents existing in database.

    """
    if request.method == "GET":
        qs = Rent.objects.all()
        data = {
            "summary": "Get all rents",
            "rents": _serialize_query_set(qs),
        }
        return JsonResponse(data, status=200, safe=False)
    return HttpResponse(request, status=405)


def get_random_words(n: int, word_site: str = "https://www.mit.edu/~ecprice/wordlist.10000") -> List[str]:
    """
    Returns random words from word_site

    :param n: quantity of random words
    :param word_site: english dictionary
    :return: list of random words from word_site
    """
    response = requests.get(word_site)
    return [x.decode('utf-8') for x in random.sample(list(response.content.splitlines()), n)]


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
            v = Video(title=v_snip['snippet']['title'],
                      description=v_snip['snippet']['description'],
                      link=v_snip['id']['videoId'],
                      likes=v_stats['statistics']['likeCount'],
                      views=v_stats['statistics']['viewCount'],
                      dislikes=v_stats['statistics']['dislikeCount'],
                      )
            v.save()

        print(f'Inserted videos{[v["snippet"]["title"] for v in snippets["items"]]}')

    return redirect('videos')


def close_auction(request: WSGIRequest, auction_id: int) -> HttpResponse:
    """
    Closes auction.

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
    return HttpResponse(request, status=403)
