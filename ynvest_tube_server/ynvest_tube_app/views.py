from typing import Union

from django.core.handlers.wsgi import WSGIRequest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render

from ynvest_tube_server.ynvest_tube_app.models import User, Auction


def register_user(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    Register new user in database. ( uuid generator)

    """
    if request.method == "GET":
        new_user = User()
        new_user.save()
        data = {
            "summary": "Register new user",
            "operationId": "registerUser",
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
            "operationId": "getUsers",
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
            "operationId": "getUser",
            "user": qs.serialize()
        }
        return JsonResponse(data, status=200)
    return render(request, "Error Pages/403.html", status=403)


def get_auctions(request: WSGIRequest) -> Union[JsonResponse, HttpResponse]:
    """
    List all auctions existed in database.

    """
    if request.method == "GET":
        users = User.objects.all()
        data = {
            "summary": "Get all auctions",
            "operationId": "getAuctions",
            "auctions": [u.serialize() for u in users]
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
            "operationId": "getAuction",
            "auction": qs.first().serialize()
        }
        return JsonResponse(data, status=200)

    elif request.method == "POST":
        qs.update(last_bidder=request.POST.get("Bidder"),
                  bet_value=request.POST.get("Value"))
        data = {
            "summary": "Bet on auction",
            "operationId": "betAuction",
            "user": qs.serialize()
        }
        return JsonResponse(data, status=200)

    return render(request, "Error Pages/403.html", status=403)
