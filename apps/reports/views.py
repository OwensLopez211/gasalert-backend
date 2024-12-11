from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from .services.report_generators import generate_pdf_report, generate_excel_report, generate_csv_report
from .services.report_data_service import ReportDataService
from .models import ReportLog
import logging



from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import connection
import csv
from io import StringIO, BytesIO
from reportlab.pdfgen import canvas
import xlsxwriter

class BaseReportViewSet(ViewSet):
    """
    Clase base para los reportes. Contiene métodos reutilizables.
    """

    def call_stored_procedure(self, proc_name, params):
        """
        Llama a un procedimiento almacenado y devuelve los resultados.
        """
        with connection.cursor() as cursor:
            cursor.callproc(proc_name, params)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def generate_csv(self, data, filename="reporte.csv"):
        """
        Genera un archivo CSV a partir de los datos.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.DictWriter(response, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return response

    def generate_pdf(self, data, filename="reporte.pdf"):
        """
        Genera un archivo PDF a partir de los datos.
        """
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.drawString(100, 800, "Reporte Generado")
        y = 750
        for row in data:
            pdf.drawString(100, y, str(row))
            y -= 20
        pdf.save()

        response.write(buffer.getvalue())
        buffer.close()
        return response

    def generate_excel(self, data, filename="reporte.xlsx"):
        """
        Genera un archivo Excel a partir de los datos.
        """
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # Escribir encabezados
        for col, header in enumerate(data[0].keys()):
            worksheet.write(0, col, header)

        # Escribir datos
        for row_idx, row in enumerate(data, start=1):
            for col_idx, (key, value) in enumerate(row.items()):
                worksheet.write(row_idx, col_idx, value)

        workbook.close()
        output.seek(0)

        response = HttpResponse(output, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

class PDFReportViewSet(BaseReportViewSet):
    """
    ViewSet para generar reportes en formato PDF.
    """

    def list(self, request):
        """
        Genera un reporte basado en parámetros de consulta.
        """
        tanque_id = request.query_params.get("tanque_id")
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        # Llamar al procedimiento almacenado
        data = self.call_stored_procedure("resumen_consumo_tanque", [tanque_id, fecha_inicio, fecha_fin])
        return self.generate_pdf(data, filename="reporte_consumo.pdf")

class ExcelReportViewSet(BaseReportViewSet):
    """
    ViewSet para generar reportes en formato Excel.
    """

    def list(self, request):
        """
        Genera un reporte basado en parámetros de consulta.
        """
        tanque_id = request.query_params.get("tanque_id")
        intervalo = request.query_params.get("intervalo", "day")
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        # Llamar al procedimiento almacenado
        data = self.call_stored_procedure("historico_lecturas", [tanque_id, intervalo, fecha_inicio, fecha_fin])
        return self.generate_excel(data, filename="reporte_historico.xlsx")

class CSVReportViewSet(BaseReportViewSet):
    """
    ViewSet para generar reportes en formato CSV.
    """

    def list(self, request):
        """
        Genera un reporte basado en parámetros de consulta.
        """
        estacion_id = request.query_params.get("estacion_id")

        # Llamar al procedimiento almacenado
        data = self.call_stored_procedure("reporte_umbrales", [estacion_id])
        return self.generate_csv(data, filename="reporte_umbrales.csv")


# logger = logging.getLogger(__name__)

# class PDFReportViewSet(ViewSet):
#     def list(self, request):
#         """
#         Endpoint para generar un reporte en formato PDF.
#         """
#         try:
#             logger.info("Iniciando generación de reporte PDF...")
#             user = request.user
#             date_range = request.query_params.get('range', 'month')

#             # Obtener datos para el reporte
#             service = ReportDataService()
#             estacion_id = user.roles_estaciones.first().estacion_id  # Asegúrate de que esto sea válido
#             data = service.get_report_data(estacion_id, date_range)

#             # Generar reporte
#             buffer = generate_pdf_report(data)
#             response = HttpResponse(buffer, content_type="application/pdf")
#             response["Content-Disposition"] = 'attachment; filename="reporte_tanques.pdf"'

#             # Log del reporte
#             ReportLog.objects.create(user=user, report_type="PDF", date_range=date_range, success=True)
#             return response

#         except Exception as e:
#             logger.error(f"Error generando reporte PDF: {str(e)}", exc_info=True)
#             ReportLog.objects.create(user=request.user, report_type="PDF", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
#             return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class ExcelReportViewSet(ViewSet):
#     def list(self, request):
#         """
#         Endpoint para generar un reporte en formato Excel.
#         """
#         try:
#             logger.info("Iniciando generación de reporte Excel...")
#             user = request.user
#             date_range = request.query_params.get('range', 'month')

#             # Obtener datos para el reporte
#             service = ReportDataService()
#             estacion_id = user.roles_estaciones.first().estacion_id
#             data = service.get_report_data(estacion_id, date_range)

#             # Generar reporte
#             response = generate_excel_report(data)
#             response["Content-Disposition"] = 'attachment; filename="reporte_tanques.xlsx"'

#             # Log del reporte
#             ReportLog.objects.create(user=user, report_type="Excel", date_range=date_range, success=True)
#             return response

#         except Exception as e:
#             logger.error(f"Error generando reporte Excel: {str(e)}", exc_info=True)
#             ReportLog.objects.create(user=request.user, report_type="Excel", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
#             return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class CSVReportViewSet(ViewSet):
#     def list(self, request):
#         """
#         Endpoint para generar un reporte en formato CSV.
#         """
#         try:
#             logger.info("Iniciando generación de reporte CSV...")
#             user = request.user
#             date_range = request.query_params.get('range', 'month')

#             # Obtener datos para el reporte
#             service = ReportDataService()
#             estacion_id = user.roles_estaciones.first().estacion_id
#             data = service.get_report_data(estacion_id, date_range)

#             # Generar reporte
#             response = generate_csv_report(data)
#             response["Content-Disposition"] = 'attachment; filename="reporte_tanques.csv"'

#             # Log del reporte
#             ReportLog.objects.create(user=user, report_type="CSV", date_range=date_range, success=True)
#             return response

#         except Exception as e:
#             logger.error(f"Error generando reporte CSV: {str(e)}", exc_info=True)
#             ReportLog.objects.create(user=request.user, report_type="CSV", date_range=request.query_params.get('range', 'month'), success=False, error_message=str(e))
#             return Response({"error": "No se pudo generar el reporte."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
