"""ynvest_tube_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path
from . import views

urlpatterns = [
    # functional endpoints
    path('users/register', views.register_user, name='register_user'),
    path('user', views.get_user, name='get_user'),
    path('user/details', views.get_user_details, name='get_user_details'),
    path('auctions', views.get_auctions, name='get_auctions'),
    path('auctions/<int:auction_id>', views.get_auction, name='get_auction'),
    # debug endpoints
    path('bids', views.get_bids, name='get_bids'),
    path('users', views.get_users, name='get_users'),
    path('auctions/<int:auction_id>/close', views.close_auction, name='close_auction'),
    path('videos', views.get_videos, name='get_videos'),
    path('videos/random-insert', views.insert_youtube_videos, name='insert_youtube_videos'),
    path('rents', views.get_rents, name='get_rents'),
    path('rents/insert-expired', views.insert_expired_rent, name='insert_expired_rent'),

]
