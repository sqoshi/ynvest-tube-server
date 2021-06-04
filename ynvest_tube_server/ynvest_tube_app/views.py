import json
import random
from typing import Optional, List, Dict, Tuple, Union

import requests
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from ynvest_tube_server.settings import youtube
from ynvest_tube_server.ynvest_tube_app.models import User, Auction, Rent, Video, Bids
from ynvest_tube_server.ynvest_tube_app.tasks import _settle_user

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


def _load_data_from(request: WSGIRequest, *args: str) -> Union[List, str, int]:
    """
    Load data from request by transforming request to json. [python dict]

    :param args: keys that should be in request body, if not found then None
    :return: list of selected request body elements
    """
    data = json.loads(request.body)
    rs = [data[arg] if arg in data.keys() else None for arg in args]
    return rs if len(rs) > 1 else rs[0]


@csrf_exempt
def get_user(request: WSGIRequest) -> JsonResponse:
    """
    Gets specified user.

    :param request: wsgi request
    """
    if request.method == "POST":
        user_id = _load_data_from(request, "UserId")
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
        user_id = _load_data_from(request, "UserId")

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
    return wrong_method_response


def _extend_auctions_data(query_set: QuerySet, user_id: str) -> List:
    """
    Extends auction details by user contribution state.

    :param query_set: list of auctions
    :param user_id: UUID
    :return:  list of auctions extended by their relation with user
    """
    result = []
    for a in query_set:
        auction_serialized = a.serialize()
        auction_serialized['user_contribution'] = _specify_relation((a, user_id))
        result.append(auction_serialized)
    return result


@csrf_exempt
def get_auctions(request: WSGIRequest) -> JsonResponse:
    """
    List all auctions existed in database.

    """
    if request.method == "POST":
        auctions = Auction.objects.all()
        user_id = _load_data_from(request, "UserId")

        data = {
            "summary": "Get all auctions",
            "activeAuctions": _extend_auctions_data(auctions.filter(state="active"), user_id),
            "inactiveAuctions": _serialize_query_set(auctions.filter(state="inactive")),
        }
        return JsonResponse(data, status=200, safe=False)

    if request.method == "GET":
        auctions = Auction.objects.all()

        data = {
            "summary": "Get all auctions",
            "activeAuctions": _serialize_query_set(auctions.filter(state="active")),
            "inactiveAuctions": _serialize_query_set(auctions.filter(state="inactive")),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


def _check_auction_post_request_cash_requirements(auction: Auction, user_query: QuerySet, bid_value: int) -> Tuple:
    """
    Check if auction post request requirements are fulfilled, but focus only on cash requirements.

    Requirements:

        - user must have enough cash for bid
        - bid must be greater than last bid value and auction starting price

    :param auction: aimed auction
    :param user_query: query of users with special uuid
    :param bid_value: value of new bid (try)
    :return: response status and information about occurred error
    """
    data, status = {}, 0
    user = user_query.first()
    # check user cash in wallet
    if user.cash < bid_value:
        data['summary'] = 'User has not enough cash for this bet.'
        data['userCash'] = user.cash
        data['bidValue'] = bid_value
        data['errorMessage'] = 'User has less cash than minimal bid value.'
        return data, 400

    last_bid = auction.last_bid_value
    # check bid value correctness
    if (last_bid is not None and bid_value <= last_bid) or bid_value <= auction.starting_price:
        data['summary'] = 'Wrong bid value.'
        data['auctionStartingPrice'] = auction.starting_price
        data['auctionLastBidValue'] = auction.last_bid_value
        data['bidValue'] = bid_value
        data['errorMessage'] = 'Bid must be greater than starting price and last bid value.'
        return data, 400

    return data, status


def _check_auction_post_request_requirements(auction: Auction, user_query: QuerySet, bid_value: int) -> Tuple:
    """
    Check if auction post request requirements are fulfilled.

    Requirements:

        - user must be registered in database
        - auction must be active

    :param auction: aimed auction
    :param user_query: query of users with special uuid
    :param bid_value: value of new bid (try)
    :return: response status and information about occurred error
    """
    data, status = {}, 0
    # check if auction expired
    if auction.auction_expiration_date < timezone.now():
        data['summary'] = 'Auction expired.'
        data['expirationDate'] = auction.auction_expiration_date
        return data, 404

    # check if user exist
    if not len(user_query):
        data['summary'] = 'Wrong user UUID in body.'
        data['errorMessage'] = 'User with that uuid does not exist in database.'
        return data, 403

    # check cash requirements
    data, status = _check_auction_post_request_cash_requirements(auction, user_query, bid_value)

    return data, status


def _specify_relation(*args) -> int:
    """
    Specify relation between auction and user.

    Possible results
        0 - had not participated in auction,
        1 - user had bid in auction, but is not winning
        2 - user is winning auction (biggest bid)

    It may be one liner but its not simply readable.
    """
    result = []
    for tup in args:
        auction, user_id = tup
        user = User.objects.all().filter(id=user_id).first()
        had_participated = Bids.objects.all().filter(auction=auction, user=user)
        if had_participated:
            is_winning = user == auction.last_bidder
            if is_winning:
                result.append(2)
            else:
                result.append(1)
        else:
            result.append(0)
    return result if len(result) > 1 else result.pop()


def _settle_auctioneers(user: User, auction: Auction, bid_value: int) -> None:
    """
    Every bid triggers
        - current bidder cash reduction,
        - reimbursement to the previous user (last bidder)

    :param user: currently bidding user
    :param auction: aimed auction
    :param bid_value: new bid value of current user (piercing bid)
    """
    _settle_user(user, -bid_value)
    if auction.last_bidder:
        _settle_user(auction.last_bidder, auction.last_bid_value)


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
        user_id = _load_data_from(request, "UserId")
        auction_bidders = Bids.objects.all().filter(auction=auction).values_list('user').distinct()
        serialized_auction = auction.serialize()
        serialized_auction["user_contribution"] = _specify_relation((auction, user_id))

        data = {
            "summary": "Get auction",
            "auctionBiddersCount": int(auction_bidders.count()),
            "auction": serialized_auction,
        }

        return JsonResponse(data, status=200)

    elif request.method == "PUT":
        user_id, bid_value = _load_data_from(request, "UserId", "bidValue")
        user_query = User.objects.all().filter(id=user_id)
        error_response, error_status = _check_auction_post_request_requirements(auction, user_query, bid_value)
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


def _serialize_query_set(query_set: QuerySet) -> List[Dict]:
    """
    Serializes whole query set to list of dicts

    :param query_set: django query set ( 'list' of rows from table )
    :return: list of dictionaries representing database models
    """
    return [obj.serialize() for obj in query_set]


##################################################### DEVELOPMENT ######################################################

def get_users(request: WSGIRequest) -> JsonResponse:
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
        user_id = _load_data_from(request, "UserId")
        u = User.objects.all().filter(id=user_id).first()
        v = random.choice(list(Video.objects.all()))
        sp = random.randint(10, 600)
        rtd = timezone.timedelta(days=random.randint(1, 10))
        a = Auction(state='inactive',
                    starting_price=sp,
                    last_bid_value=sp + 1,
                    last_bidder=u,
                    video=v,
                    rental_duration=rtd,
                    auction_expiration_date=timezone.now() - timezone.timedelta(days=random.randint(7, 10)),
                    rental_expiration_date=timezone.now() - timezone.timedelta(days=random.randint(2, 4)),
                    video_views_on_sold=v.views
                    )
        a.save()
        r = Rent(user=u, auction=a, state='inactive', profit=0)
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
            "auctionedVideos": _serialize_query_set(videos.filter(state='auctioned')),
            "rentedVideos": _serialize_query_set(videos.filter(state='rented')),
            "availableVideos": _serialize_query_set(videos.filter(state='available')),
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
            "allBids": _serialize_query_set(bids),
        }
        return JsonResponse(data, status=200, safe=False)
    return wrong_method_response


def get_rents(request: WSGIRequest) -> JsonResponse:
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
    return wrong_method_response


def get_random_words(n: int, word_site: str = "https://www.mit.edu/~ecprice/wordlist.10000") -> List[str]:
    """
    Returns random words from word_site

    :param n: quantity of random words
    :param word_site: english dictionary
    :return: list of random words from word_site
    """
    response = requests.get(word_site)
    result = [x.decode('utf-8') for x in random.sample(list(response.content.splitlines()), n)]
    return get_random_words(n) if not result else result


def _fix_punctuation_marks(text: str) -> str:
    """
    Changing not parsed quotes and ampersands to correct form.

    :param text: string containing not parsed symbols
    :return: string with parsed & and '
    """
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', '"')
    return text.replace('&amp;', '&')


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
            v = Video(title=_fix_punctuation_marks(v_snip['snippet']['title']),
                      description=_fix_punctuation_marks(v_snip['snippet']['description']),
                      link=v_snip['id']['videoId'],
                      likes=v_stats['statistics']['likeCount'],
                      views=v_stats['statistics']['viewCount'],
                      dislikes=v_stats['statistics']['dislikeCount'],
                      )
            v.save()

        print(f'Inserted videos{[_fix_punctuation_marks(v["snippet"]["title"]) for v in snippets["items"]]}')

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
