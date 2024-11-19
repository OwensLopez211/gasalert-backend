from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConfiguracionUmbralesViewSet, update_thresholds, test_alert

app_name = 'alerts'

router = DefaultRouter()
router.register(r'umbrales', ConfiguracionUmbralesViewSet, basename='umbrales')

urlpatterns = [
    # Ruta para pruebas
    path('test-alert/', test_alert, name='test-alert'),

    # Rutas del router
    path('', include(router.urls)),

    # Ruta para manejar umbrales de tanques específicos
    path('<int:tank_id>/thresholds', update_thresholds, name='update_thresholds'),
]
