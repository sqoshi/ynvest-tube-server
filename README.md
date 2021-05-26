# ynvest-tube-server

# Table of contests

<hr>

- [Installation](#installation)
- [Launch](#launch)
- [Periodic Tasks](#periodic-tasks)
- [Endpoints](#endpoints)

## Installation

<hr>
Redis:

- `sudo apt-get install redis`

YoutubeApi
- Add file `api_config.py` in `../ynvest_tube_server/ynvest_tube_server/` with variable `api_key='xxxxxxxxxxxxxxxxxxx'`

![](docs/.README_images/apikey.png)

Requirements

- `pip install -r requirements.txt`


Migrations (Call migrations, just for sure)

- `./manage.py makemigrations`

- `./manage.py migrate`


## Launch

Run three terminals in directory containing `manage.py`.
In each one activate python virutalenv with `source venv/bin/activate`.

1. In first: `celery -A ynvest_tube_server worker -l info -B`

2. In second: `celery -A ynvest_tube_server beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`

3. In third: `./manage.py runserver`


Server is bind to local `http://127.0.0.1:8000/`

![](docs/.README_images/launch.png)

## Periodic Tasks

<hr>

Redis used as a machine handling calls for periodic tasks. Task scheduler may be configured with django-admin
`localhost:8080/admin` interface.

### Auctions closer ( 1call / 1s)

When auction expires, set auction to `inactive`

1. If no one participated in auction, then just change auction state.
2. Else add new rent to `rents` table with user as `last_bidder`, reduce user cash by `last_bid_value`, set video
   to `rented`.

### Auctions generator ( 1call / 1800s)

Generate random auction if there is less than 10 active auctions.

- random not rented video
- random starting price
- rental expiration date= now() + random(8 days

### Video updater (1call / 30s) ( max )

Update views, likes and dislikes of each video in database.

## Rents settler ( 1call / 1s )

Payoff users salaries at the end of renting.

- gets rentals with expired date and calculate video diffs.
- computes salary and increases user cash.
- sets rent to `inactive`
- sets video to `not rented`

## Endpoints

![](docs/.README_images/endpoints.png)