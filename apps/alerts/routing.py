from django.urls import re_path
from apps.alerts.consumers import AlertaConsumer

websocket_urlpatterns = [
    re_path(r'ws/alerts/$', AlertaConsumer.as_asgi()),
]