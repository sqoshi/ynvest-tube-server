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
    path('users/register', views.register_user, name='register_user'),
    path('users/<str:user_id>', views.get_user, name='get_user'),
    path('users', views.get_users, name='get_users'),
    path('auctions/<int:auction_id>', views.get_auction, name='get_auction'),
    path('auctions', views.get_auctions, name='get_auctions'),
]
