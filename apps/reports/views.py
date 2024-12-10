from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from .services.report_generators import generate_pdf_report, generate_excel_report, generate_csv_report
from .services.report_data_service import ReportDataService
from .models import ReportLog
import logging

logger = logging.getLogger(__name__)

class PDFReportViewSet(ViewSet):
    def list(self, request):
        """
        Endpoint para generar un reporte en formato PDF.
        """
        try:
            logger.info("Iniciando generación de reporte PDF...")
            user = request.user
            date_range = request.query_params.get('range', 'month')

            # Obtener datos para el reporte
            service = ReportDataService()
            estacion_id = user.roles_estaciones.first().estacion_id  # Asegúrate de que esto sea válido
            data = service.get_report_data(estacion_id, date_range)

            # Generar reporte
            buffer = generate_pdf_report(data)
            response = HttpResponse(buffer, content_type="application/pdf")
            response["Content-Disposition"] = 'attachment; filename="reporte_tanques.pdf"'

            # Log del reporte
            ReportLog.objects.create(user=user, report_type="PDF", date_range=date_range, success=True)
            return response

        except Exception as e:
            logger.error(f"Error generando reporte PDF: {str(e)}", exc_info=True)
            ReportLog.objects.create(user=request.user, report_type="PDF", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
            return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExcelReportViewSet(ViewSet):
    def list(self, request):
        """
        Endpoint para generar un reporte en formato Excel.
        """
        try:
            logger.info("Iniciando generación de reporte Excel...")
            user = request.user
            date_range = request.query_params.get('range', 'month')

            # Obtener datos para el reporte
            service = ReportDataService()
            estacion_id = user.roles_estaciones.first().estacion_id
            data = service.get_report_data(estacion_id, date_range)

            # Generar reporte
            response = generate_excel_report(data)
            response["Content-Disposition"] = 'attachment; filename="reporte_tanques.xlsx"'

            # Log del reporte
            ReportLog.objects.create(user=user, report_type="Excel", date_range=date_range, success=True)
            return response

        except Exception as e:
            logger.error(f"Error generando reporte Excel: {str(e)}", exc_info=True)
            ReportLog.objects.create(user=request.user, report_type="Excel", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
            return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CSVReportViewSet(ViewSet):
    def list(self, request):
        """
        Endpoint para generar un reporte en formato CSV.
        """
        try:
            logger.info("Iniciando generación de reporte CSV...")
            user = request.user
            date_range = request.query_params.get('range', 'month')

            # Obtener datos para el reporte
            service = ReportDataService()
            estacion_id = user.roles_estaciones.first().estacion_id
            data = service.get_report_data(estacion_id, date_range)

            # Generar reporte
            response = generate_csv_report(data)
            response["Content-Disposition"] = 'attachment; filename="reporte_tanques.csv"'

            # Log del reporte
            ReportLog.objects.create(user=user, report_type="CSV", date_range=date_range, success=True)
            return response

        except Exception as e:
            logger.error(f"Error generando reporte CSV: {str(e)}", exc_info=True)
            ReportLog.objects.create(user=request.user, report_type="CSV", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
            return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
