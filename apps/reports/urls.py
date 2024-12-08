from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PDFReportViewSet, ExcelReportViewSet, CSVReportViewSet

# Configuración del router
router = DefaultRouter()
router.register(r'pdf', PDFReportViewSet, basename='pdf-report')
router.register(r'excel', ExcelReportViewSet, basename='excel-report')
router.register(r'csv', CSVReportViewSet, basename='csv-report')

app_name = 'reports'

urlpatterns = [
    path('', include(router.urls)),  # Incluir las rutas generadas por el router
]
