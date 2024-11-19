import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set the correct settings module path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')  # Note the .base

# Import websocket_urlpatterns after setting up Django
django_asgi_app = get_asgi_application()

# Import routing after Django is set up
from apps.tanks.routing import websocket_urlpatterns  # Import after Django setup

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})