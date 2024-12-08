import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

# Configurar el módulo de settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')

# Obtener la aplicación ASGI de Django
django_asgi_app = get_asgi_application()

# Importar los patrones de websocket desde el routing principal
from core.routing import websocket_urlpatterns

print("\nComprobando rutas en ASGI:")
for pattern in websocket_urlpatterns:
    print(f"  - Ruta registrada: {pattern.pattern}")

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})