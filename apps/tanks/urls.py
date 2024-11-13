from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TipoCombustibleViewSet, TanqueViewSet, LecturaViewSet, DashboardViewSet

# Crear el router y registrar los viewsets
router = DefaultRouter()
router.register(r'tipos-combustible', TipoCombustibleViewSet)
router.register(r'tanques', TanqueViewSet, basename='tanque')
router.register(r'lecturas', LecturaViewSet, basename='lectura')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')

app_name = 'tanks'

urlpatterns = [
    path('', include(router.urls)),
]