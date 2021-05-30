# ynvest-tube-server

<div align="right" style="display: flex;flex-direction: row">
  <img src="https://github.com/sqoshi/ynvest-tube/tree/master/ynvest_tube/app/src/main/ynvest_tube_logo-playstore.png" width="100"/>
</div>

Server for mobile game [YnvestTube](https://github.com/sqoshi/ynvest-tube). Instructions included in this article
concern Linux systems.



# Table of contests

- [Endpoints](#endpoints)
- [Installation](#installation)
   - [Automatic](#automatic)
   - [Manual](#manual)
- [Launch](#launch)
   - [Automatic](#automatic-1)
   - [Manual](#manual-1)
- [Periodic Tasks](#periodic-tasks)
   - [Auctions closer](#auctions-closer)
   - [Auctions generator](#auctions-generator)
   - [Video updater](#video-updater)
   - [Rents settler](#rents-settler)
- [Technologies](#technologies)


## Endpoints

![](docs/.README_images/endpoints.png)

## Installation

### Automatic

Installation process may be automated via script `install.sh`.

1. `chmod +rwx install.sh`
2. `./install.sh`

### Manual

If script fails in some way, installation may be carried out manually.

YoutubeApi (Optional)

1. You may change api_key in `api_config.py` in `../ynvest_tube_server/ynvest_tube_server/` to key generated
   in [YoutubeDataApi Projects](https://developers.google.com/youtube/v3).

![](docs/.README_images/apikey.png)

Redis

1. `sudo apt-get install redis`

Requirements

1. `pip install -r requirements.txt`

Migrations (Call migrations, just for sure)

1. `./manage.py makemigrations`
2. `./manage.py migrate`

## Launch

### Automatic

1. `chmod +rwx run_server.sh`
2. `./run_server.sh`

### Manual

If script fails in some way, installation may be carried out manually.

Run three terminals in directory containing `manage.py`. In each one activate python virutalenv
with `source venv/bin/activate` and run subsequent commands, one in one terminal.

1. `celery -A ynvest_tube_server worker -l info -B`
2. `celery -A ynvest_tube_server beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`
3. `./manage.py runserver`

Server is bind to local `http://127.0.0.1:8000/`

![](docs/.README_images/launch.png)

## Periodic Tasks

Redis used as a machine is handling calls for periodic tasks. Task scheduler may be configured with django-admin
`localhost:8080/admin` interface.

### Auctions closer 

`( 1call / 1s)`

When auction expires, set auction to `inactive`

1. If no one participated in auction, then just change auction state.
2. Else add new rent to `rents` table with user as `last_bidder`, reduce user cash by `last_bid_value`, set video
   to `rented`.

### Auctions generator

`(1call / 1800s)`

Generate random auction if there is less than 10 active auctions.

- random not rented video
- random starting price
- rental expiration date= now() + random(8 days

### Video updater 

`(1call / 30s) ( max )`

Update views, likes and dislikes of each video in database.

### Rents settler 

`( 1call / 1s )`

Payoff users salaries at the end of renting.

- gets rentals with expired date and calculate video diffs.
- computes salary and increases user cash.
- sets rent to `inactive`
- computes rent profit.
- sets video to `not rented`

## Technologies

- python3
- django
- redis
- bash
- celery
- swagger
