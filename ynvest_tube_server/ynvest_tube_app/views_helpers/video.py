import random
from typing import List

import requests


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


def fix_punctuation_marks(text: str) -> str:
    """
    Changing not parsed quotes and ampersands to correct form.

    :param text: string containing not parsed symbols
    :return: string with parsed & and '
    """
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', '"')
    return text.replace('&amp;', '&')
