from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path
from apps.tanks.consumers import TankStatusConsumer
from apps.alerts.consumers import AlertaConsumer

websocket_urlpatterns = [
    re_path(r'^ws/tank_status/$', TankStatusConsumer.as_asgi()),
    re_path(r'^ws/alerts/$', AlertaConsumer.as_asgi()),
]

# Agregar print para depuración
print("\nRutas WebSocket registradas en routing.py:")
for pattern in websocket_urlpatterns:
    print(f"  - {pattern.pattern}")

""" application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    )
}) """