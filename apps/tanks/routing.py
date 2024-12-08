# core/routing.py
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from apps.tanks.consumers import TankStatusConsumer

websocket_urlpatterns = [
    re_path(r'ws/tank_status/$', TankStatusConsumer.as_asgi()),
]
