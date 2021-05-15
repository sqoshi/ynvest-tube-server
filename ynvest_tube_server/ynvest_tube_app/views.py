from django.http import JsonResponse

from ynvest_tube_server.ynvest_tube_app.models import User


def register_user(request):
    if request.method == "GET":
        new_user = User()
        new_user.save()
        return JsonResponse({"uuid": new_user.id})
