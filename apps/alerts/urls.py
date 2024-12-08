from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import NotificacionesViewSet, AlertaViewSet

router = DefaultRouter()
router.register(r'umbrales', views.UmbralesViewSet, basename='umbrales')
router.register(r'notificaciones', NotificacionesViewSet, basename='notificaciones')
router.register(r'alertas', AlertaViewSet, basename='alerta')


app_name = 'alerts'

urlpatterns = [
    path('', include(router.urls)),
    path('alerts/', views.generar_alerta, name='generar_alerta'),
]
