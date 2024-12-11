# from rest_framework.viewsets import ViewSet
# from rest_framework.response import Response
# from rest_framework import status
# from django.http import HttpResponse
# from .services.report_generators import generate_pdf_report, generate_excel_report, generate_csv_report
# from .services.report_data_service import ReportDataService
# from .models import ReportLog
# import logging



from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.db import connection
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class PDFReportViewSet(ViewSet):
    """
    ViewSet para generar reportes PDF completos usando procedimientos almacenados.
    """
    
    def call_stored_procedure(self, proc_name, params):
        """
        Llama a un procedimiento almacenado y devuelve los resultados.
        """
        with connection.cursor() as cursor:
            cursor.callproc(proc_name, params)
            if cursor.description:  # Verificar si hay resultados
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            return []

    def generate_pdf_report(self, data):
        """
        Genera un PDF formateado con los datos proporcionados
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Título del reporte
        elements.append(Paragraph("Reporte de Análisis de Tanques", styles['Title']))
        elements.append(Paragraph("<br/><br/>", styles['Normal']))

        # Procesar cada sección de datos
        for section in data:
            if section['data']:
                # Título de la sección
                elements.append(Paragraph(section['title'], styles['Heading1']))
                
                # Convertir datos a tabla
                table_data = [list(section['data'][0].keys())]  # Headers
                table_data.extend([list(item.values()) for item in section['data']])
                
                # Crear y estilizar la tabla
                table = Table(table_data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                
                elements.append(table)
                elements.append(Paragraph("<br/><br/>", styles['Normal']))

        doc.build(elements)
        return buffer

    @action(detail=False, methods=['get'])
    def generate(self, request):
        """
        Genera un reporte PDF completo con datos de múltiples procedimientos almacenados.
        """
        try:
            # Obtener parámetros
            tank_id = request.query_params.get('tank_id')
            station_id = request.query_params.get('station_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            interval = request.query_params.get('interval', 'day')

            if not all([tank_id, station_id, start_date, end_date]):
                return Response(
                    {"error": "Faltan parámetros requeridos"},
                    status=400
                )

            # Recopilar datos de todos los procedimientos almacenados
            report_data = [
                {
                    'title': 'Resumen de Consumo',
                    'data': self.call_stored_procedure(
                        'sp_consumption_summary',
                        [tank_id, start_date, end_date]
                    )
                },
                {
                    'title': 'Historial de Lecturas',
                    'data': self.call_stored_procedure(
                        'sp_readings_history',
                        [tank_id, interval, start_date, end_date]
                    )
                },
                {
                    'title': 'Alertas del Período',
                    'data': self.call_stored_procedure(
                        'sp_period_alerts',
                        [station_id, start_date, end_date]
                    )
                },
                {
                    'title': 'Estadísticas de Reposición',
                    'data': self.call_stored_procedure(
                        'sp_refill_statistics',
                        [tank_id, start_date, end_date]
                    )
                },
                {
                    'title': 'Análisis de Eficiencia',
                    'data': self.call_stored_procedure(
                        'sp_efficiency_analysis',
                        [station_id, start_date, end_date]
                    )
                }
            ]

            # Generar PDF
            buffer = self.generate_pdf_report(report_data)
            buffer.seek(0)
            
            # Preparar respuesta
            response = HttpResponse(
                content=buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="reporte_{start_date}_{end_date}.pdf"'
            response['Accept-Ranges'] = 'bytes'
            
            # Añadir cabeceras CORS explícitas
            response['Access-Control-Allow-Origin'] = '*'  # O tu dominio específico
            response['Access-Control-Allow-Headers'] = 'Accept, Content-Type, Authorization'
            response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            
            buffer.close()
            return response

        except Exception as e:
            logger.error(f"Error generando reporte PDF: {str(e)}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=500,
                content_type='application/json'
            )

    def options(self, request, *args, **kwargs):
        response = HttpResponse()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Accept, Content-Type, Authorization'
        return response

        

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
