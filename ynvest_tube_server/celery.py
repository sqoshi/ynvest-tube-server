import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ynvest_tube_server.settings')
app = Celery("ynvest_tube_server")

app.config_from_object('django.conf:settings', namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    'close-auctions': {
        'task': 'close_expired_auctions',
        'schedule': 1.0,
    },
    'settle-rents': {
        'task': 'settle_rents',
        'schedule': 1.0,
    },
    'generate-auction': {
        'task': 'generate_auction',
        'schedule': 60.0,
        # 'args': (16, 16)
    },
    'payout-loyalty': {
        'task': 'payout_loyalty_cash',
        'schedule': 3600 * 24 * 7,
        # 'args': (16, 16)
    },
    'update-video-views': {
        'task': 'update_video_views',
        'schedule': 3600,
        # 'args': (16, 16)
    }

}

app.conf.timezone = 'Europe/Warsaw'
