from typing import List, Tuple

from django.db.models import QuerySet
from django.utils import timezone

from ynvest_tube_server.ynvest_tube_app.models import Auction, Bids, User
from ynvest_tube_server.ynvest_tube_app.tasks_service import settle_user


def settle_auctioneers(user: User, auction: Auction, bid_value: int) -> None:
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


def specify_relation(*args) -> int:
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


def extend_auctions_data(query_set: QuerySet, user_id: str) -> List:
    """
    Extends auction details by user contribution state.

    :param query_set: list of auctions
    :param user_id: UUID
    :return:  list of auctions extended by their relation with user
    """
    result = []
    for a in query_set:
        auction_serialized = a.serialize()
        auction_serialized['user_contribution'] = specify_relation((a, user_id))
        result.append(auction_serialized)
    return result


############################# validators #######################################
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


def check_auction_post_request_requirements(auction: Auction, user_query: QuerySet, bid_value: int) -> Tuple:
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
