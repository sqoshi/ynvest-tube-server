from typing import Union, Optional

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from ynvest_tube_server.auction_generator import generate_auction
from ynvest_tube_server.ynvest_tube_app.models import User, Auction, Rent


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


def get_user(request: WSGIRequest, user_id: str) -> Union[JsonResponse, HttpResponse]:
    """
    Gets specified user.

    :param request: wsgi request
    :param user_id: UUID assigned in registration
    """
    qs = User.objects.all().filter(id=user_id).first()
    if request.method == "GET":
        data = {
            "summary": "Get user",
            "user": qs.serialize()
        }
        return JsonResponse(data, status=200)
    return render(request, "Error Pages/403.html", status=403)


def get_user_details(request: WSGIRequest, user_id: str) -> Optional[Union[JsonResponse, HttpResponse]]:
    if request.method == "GET":
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
    generate_auction()
    if request.method == "GET":
        qs = Auction.objects.all()
        data = {
            "summary": "Get all auctions",
            "auctions": [a.serialize() for a in qs],
            "activeAuctions": [a.serialize() for a in qs.filter(state="active")],
            "inactiveAuctions": [a.serialize() for a in qs.filter(state="inactive")],
        }
        return JsonResponse(data, status=200, safe=False)
    return render(request, "Error Pages/405.html", status=405)


def get_auction(request, auction_id) -> Union[JsonResponse, HttpResponse]:
    """
    On GET request returns specific auction

    On POST request changes last bidder, and bet value.


    :param request: wsgi request
    :param auction_id: auction id

    """
    qs = Auction.objects.all().filter(id=auction_id)
    if request.method == "GET":
        data = {
            "summary": "Get auction",
            "auction": qs.first().serialize()
        }
        return JsonResponse(data, status=200)

    elif request.method == "POST":
        u = User.objects.all().filter(id=request.POST.get("user_id"))
        qs.update(last_bidder=u,
                  bet_value=int(request.POST.get("value")))
        data = {
            "summary": "Bet on auction",
            "auction": qs.first().serialize()
        }
        return JsonResponse(data, status=200)

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
