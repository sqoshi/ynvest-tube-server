import json
from typing import Union, List, Dict

from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet


def load_data_from(request: WSGIRequest, *args: str) -> Union[List, str, int]:
    """
    Load data from request by transforming request to json. [python dict]

    :param args: keys that should be in request body, if not found then None
    :return: list of selected request body elements
    """
    data = json.loads(request.body)
    rs = [data[arg] if arg in data.keys() else None for arg in args]
    return rs if len(rs) > 1 else rs[0]


def serialize_query_set(query_set: QuerySet) -> List[Dict]:
    """
    Serializes whole query set to list of dicts

    :param query_set: django query set ( 'list' of rows from table )
    :return: list of dictionaries representing database models
    """
    return [obj.serialize() for obj in query_set]
