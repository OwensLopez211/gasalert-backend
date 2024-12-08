from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # Aquí van las urls de las respectivas APIS
    path('api/', include('apps.users.urls')),         # URLs de users
    path('api/', include('apps.stations.urls')),      # URLs de stations
    path('api/tanks/', include('apps.tanks.urls')),   # URLs de tanks
    path('api/alerts/', include('apps.alerts.urls')), # URLs de alerts
    path('api/reports/', include('apps.reports.urls')),  # URLs de reports
]

if settings.DEBUG:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
