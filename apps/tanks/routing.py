from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/tank_status/$', consumers.TankStatusConsumer.as_asgi()),
]