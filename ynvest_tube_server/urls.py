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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from swagger_render.views import SwaggerUIView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ynvest_tube_server.ynvest_tube_app.urls")),
    path("", SwaggerUIView.as_view()),
]

urlpatterns += static("/docs/", document_root="docs")
