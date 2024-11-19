from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TipoCombustibleViewSet, 
    TanqueViewSet, 
    LecturaViewSet, 
    DashboardViewSet,
    sensor_reading
)

router = DefaultRouter()
router.register(r'tipos-combustible', TipoCombustibleViewSet)
router.register(r'', TanqueViewSet, basename='tanque')
router.register(r'lecturas', LecturaViewSet, basename='lectura')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

app_name = 'tanks'

urlpatterns = [
    path('sensor-reading/', sensor_reading, name='sensor-reading'),
    path('', include(router.urls)),
]