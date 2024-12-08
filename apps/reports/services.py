from io import BytesIO
from django.http import HttpResponse
from reportlab.pdfgen import canvas
import openpyxl
from django.http import HttpResponse

def generate_pdf_report(data):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)

    # Título
    pdf.drawString(100, 750, "Reporte de Tanques")

    # Datos del reporte
    for i, item in enumerate(data):
        pdf.drawString(100, 700 - (i * 20), f"Tanque: {item['tanque']}, Consumo: {item['consumo']} L/día")

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def generate_excel_report(data):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Reporte de Tanques"

    # Agregar encabezados
    sheet.append(["Tanque", "Consumo Diario", "Consumo Semanal"])

    # Agregar datos
    for item in data:
        sheet.append([item['tanque'], item['consumo_diario'], item['consumo_semanal']])

    # Preparar la respuesta
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = 'attachment; filename="reporte_tanques.xlsx"'
    workbook.save(response)
    return response
