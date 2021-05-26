import json
from typing import Union, Optional

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import User, Auction, Rent, Video, Bids


def register_user(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
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
    return render(request, "Error Pages/405.html", status=405)


def get_users(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    List all users in database.

    """
    if request.method == "GET":
        qs = User.objects.all()
        data = {
            "summary": "Get all users",
            "users": [u.serialize() for u in qs]
        }
        return JsonResponse(data, status=200, safe=False)
    return render(request, "Error Pages/405.html", status=405)


def get_user(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    Gets specified user.

    :param request: wsgi request
    """
    if request.method == "GET":
        data = json.loads(request.body)
        user_id = data["UserId"]
        qs = User.objects.all().filter(id=user_id).first()
        data = {
            "summary": "Get user",
            "user": qs.serialize()
        }
        return JsonResponse(data, status=200)
    return render(request, "Error Pages/403.html", status=403)


def get_user_details(request) -> Optional[Union[JsonResponse, HttpResponse]]:
    if request.method == "GET":
        data = json.loads(request.body)
        user_id = data["UserId"]
        # auctions in which user participate at the moment
        u = User.objects.all().filter(id=user_id).first()
        auctions = Auction.objects.all().filter(last_bidder=u, state="active")
        # all user transactions
        rents = Rent.objects.filter(user=u)
        data = {
            "summary": "Get user actual auctions and all his rents.",
            "attendingAuctions": [a.serialize for a in auctions],  # totally wrong name need to be changed
            "cash": u.cash,
            "rents": [r.serialize() for r in rents],
            # "actualRents": [r.serialize() for r in rents.select_related("auction").filter()],
            # "expiredRents": [r.serialize() for r in rents.filter()]
        }
        return JsonResponse(data, status=200)

    return None


def get_auctions(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    List all auctions existed in database.

    """
    # gen_auc()
    # insert_youtube_videos('marvel', 'funny dog', 'python', 'nike', 'kotlin')
    if request.method == "GET":
        qs = Auction.objects.all()
        data = {
            "summary": "Get all auctions",
            "activeAuctions": [a.serialize() for a in qs.filter(state="active")],
            "inactiveAuctions": [a.serialize() for a in qs.filter(state="inactive")],
        }
        return JsonResponse(data, status=200, safe=False)
    return render(request, "Error Pages/405.html", status=405)


@csrf_exempt
def get_auction(request, auction_id) -> Union[JsonResponse, HttpResponse]:
    """
    On GET request returns specific auction

    On POST request changes last bidder, and bet value.

    :param request: wsgi request
    :param auction_id: auction id

    """
    qs = Auction.objects.all().filter(id=auction_id)
    if request.method == "GET":
        auction_bidders = Bids.objects.all().filter(auction=qs.first()).values('user').distinct('user').count()
        data = {
            "summary": "Get auction",
            "auctionBidders": int(auction_bidders),
            "auction": qs.first().serialize(),
        }
        return JsonResponse(data, status=200)

    elif request.method == "POST":
        data = json.loads(request.body)
        user_id = data["UserId"]
        bid_value = int(data["bidValue"])
        u = User.objects.all().filter(id=user_id)
        if u.first().cash >= bid_value:
            b = Bids(qs.first(), u, bid_value)
            b.save()
            qs.update(last_bidder=u, last_bid_value=bid_value)
            data = {
                "summary": "Bet on auction",
                "auction": qs.first().serialize()
            }
            return JsonResponse(data, status=200)
        # else no money for bet

    return render(request, "Error Pages/403.html", status=403)


def close_auction(request, auction_id) -> Union[JsonResponse, HttpResponse]:
    if request.method == "GET":
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
    return render(request, "Error Pages/403.html", status=403)


def get_videos(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    List all videos existing in database.

    """
    insert_youtube_videos('hulk', 'gorilla', 'tiger')
    if request.method == "GET":
        qs = Video.objects.all()
        data = {
            "summary": "Get all videos",
            "videos": [a.serialize() for a in qs],
        }
        return JsonResponse(data, status=200, safe=False)
    return render(request, "Error Pages/405.html", status=405)


def get_rents(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    List all rents existing in database.

    """
    if request.method == "GET":
        qs = Rent.objects.all()
        data = {
            "summary": "Get all rents",
            "rents": [a.serialize() for a in qs],
        }
        return JsonResponse(data, status=200, safe=False)
    return render(request, "Error Pages/405.html", status=405)


def insert_youtube_videos(*args):
    print("Inserting videos...")
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
