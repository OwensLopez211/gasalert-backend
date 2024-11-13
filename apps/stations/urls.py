from django.urls import path
from .views import (
    RegionListView,
    ComunasByRegionView,
    EstacionListCreateView,
    EstacionDetailView,
)

app_name = 'stations'

urlpatterns = [
    # Endpoints para regiones y comunas
    path('regiones/', RegionListView.as_view(), name='region-list'),
    path('regiones/<int:region_id>/comunas/', ComunasByRegionView.as_view(), name='comuna-by-region'),
    
    # Endpoints para estaciones
    path('estaciones/', EstacionListCreateView.as_view(), name='estacion-list-create'),
    path('estaciones/<int:pk>/', EstacionDetailView.as_view(), name='estacion-detail'),
]