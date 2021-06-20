from ynvest_tube_server.settings import youtube
from typing import List
import sys

from ynvest_tube_server.ynvest_tube_app.models import Auction, Video, Rent, User


def set_video(video: Video, state: str) -> None:
    """
    Set video state.

    """
    video.state = state
    video.save()


def assign_rent(auction: Auction) -> None:
    """
    Handle rent in system

    """
    r = Rent(auction=auction, user=auction.last_bidder)
    r.save()


def settle_user(user: User, value: int) -> None:
    """
    Reduce user cash

    """
    # print(f' {user} settled by {value}')
    user.cash += value
    user.save()


def collect_videos_statistics(objects: List, result_limit: int = 50) -> List:
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
        videos_id_str = ",".join([x.link for x in objects[i - result_limit : upper_limit]])
        response = youtube.videos().list(id=videos_id_str, part="statistics").execute()
        videos_statistics.extend(response["items"])

    return videos_statistics


def choose_loyalty_degree(days: int, max_level=6, cash_base: int = 500, interval_base: int = 30) -> int:
    """
    Designates payout by specifying the degree of loyalty

    :param interval_base: multiplicity of these intervals determines nex stages
    :param cash_base: multiplicity of these intervals determines nex cash payouts
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


def deactivate_rent(rent: Rent, views_diff: int) -> None:
    """
    Deactivate rent in system

    """
    rent.state = "inactive"
    rent.profit = views_diff - rent.auction.last_bid_value
    rent.save()
