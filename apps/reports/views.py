from rest_framework.viewsets import ViewSet
from django.http import HttpResponse
from .services import generate_pdf_report

class PDFReportViewSet(ViewSet):
    def list(self, request):
        """
        Genera y devuelve un reporte PDF.
        """
        data = [
            {"tanque": "Tanque 1", "consumo": 85},
            {"tanque": "Tanque 2", "consumo": 90},
        ]
        buffer = generate_pdf_report(data)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="reporte.pdf"'
        return response

from rest_framework.viewsets import ViewSet
from django.http import HttpResponse
from .services import generate_excel_report

class ExcelReportViewSet(ViewSet):
    def list(self, request):
        """
        Genera y devuelve un reporte en Excel.
        """
        data = [
            {"tanque": "Tanque 1", "consumo_diario": 85, "consumo_semanal": 560},
            {"tanque": "Tanque 2", "consumo_diario": 90, "consumo_semanal": 630},
        ]
        return generate_excel_report(data)

from rest_framework.viewsets import ViewSet
import csv
from django.http import HttpResponse

class CSVReportViewSet(ViewSet):
    def list(self, request):
        """
        Genera y devuelve un reporte en formato CSV.
        """
        data = [
            {"tanque": "Tanque 1", "consumo_diario": 85, "consumo_semanal": 560},
            {"tanque": "Tanque 2", "consumo_diario": 90, "consumo_semanal": 630},
        ]
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reporte.csv"'

        writer = csv.writer(response)
        writer.writerow(['Tanque', 'Consumo Diario', 'Consumo Semanal'])
        for item in data:
            writer.writerow([item['tanque'], item['consumo_diario'], item['consumo_semanal']])

        return response
