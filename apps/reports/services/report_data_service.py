from datetime import datetime, timedelta
from django.db.models import Avg, Count, Sum, F
from django.utils import timezone
from apps.tanks.models import Tanque, Lectura
from apps.alerts.models import Alerta
from apps.alerts.serializers import AlertaSerializer
import matplotlib.pyplot as plt
from io import BytesIO


class ReportDataService:
    @staticmethod
    def get_tanks_status(estacion_id):
        """
        Obtiene el estado actual de los tanques de la estación.
        """
        tanks = Tanque.objects.filter(estacion_id=estacion_id).prefetch_related(
            'lecturas'
        ).select_related('tipo_combustible')

        tank_status = []
        for tank in tanks:
            last_reading = tank.lecturas.order_by('-fecha').first()
            tank_status.append({
                'id': tank.id,
                'nombre': tank.nombre,
                'nivel_actual': last_reading.nivel if last_reading else 0,
                'volumen_actual': last_reading.volumen if last_reading else 0,
                'estado': ReportDataService._determine_tank_status(last_reading.nivel if last_reading else 0),
            })

        return tank_status

    @staticmethod
    def _determine_tank_status(nivel):
        """
        Determina el estado del tanque basado en el nivel.
        """
        if nivel >= 75:
            return 'ÓPTIMO'
        elif nivel >= 40:
            return 'NORMAL'
        elif nivel >= 20:
            return 'BAJO'
        return 'CRÍTICO'

    @staticmethod
    def get_alerts_data(estacion_id, date_range):
        """
        Obtiene las alertas generadas en un rango de fechas.
        """
        start_date, end_date = ReportDataService._get_date_range(date_range)

        alerts = Alerta.objects.filter(
            tanque__estacion_id=estacion_id,
            fecha_generacion__range=(start_date, end_date)
        )

        return {
            'total': alerts.count(),
            'by_type': dict(alerts.values('tipo_tendencia').annotate(total=Count('id'))),
            'recent': AlertaSerializer(alerts.order_by('-fecha_generacion')[:5], many=True).data
        }

    @staticmethod
    def get_consumption_metrics(estacion_id, date_range):
        """
        Calcula métricas de consumo para la estación.
        """
        start_date, end_date = ReportDataService._get_date_range(date_range)

        lecturas = Lectura.objects.filter(
            tanque__estacion_id=estacion_id,
            fecha__range=(start_date, end_date)
        ).order_by('fecha')

        daily_consumption = (
            lecturas.annotate(day=F('fecha__date'))
            .values('day')
            .annotate(total_consumo=Sum('volumen'))
        )

        total_consumption = sum(item['total_consumo'] for item in daily_consumption)
        daily_avg = total_consumption / len(daily_consumption) if daily_consumption else 0

        return {
            'total_consumption': round(total_consumption, 2),
            'daily_avg': round(daily_avg, 2),
            'daily_trend': daily_consumption
        }

    @staticmethod
    def generate_consumption_graph(daily_trend):
        """
        Genera un gráfico de consumo diario.
        """
        days = [item['day'] for item in daily_trend]
        consumption = [item['total_consumo'] for item in daily_trend]

        plt.figure(figsize=(8, 6))
        plt.plot(days, consumption, marker='o', linestyle='-', color='b')
        plt.title("Consumo Diario")
        plt.xlabel("Día")
        plt.ylabel("Consumo (litros)")
        plt.grid(True)

        buffer = BytesIO()
        plt.savefig(buffer, format='PNG')
        buffer.seek(0)
        plt.close()
        return buffer

    @staticmethod
    def get_report_data(estacion_id, date_range):
        """
        Prepara los datos del reporte combinando métricas, alertas y gráficos.
        """
        try:
            tanks_status = ReportDataService.get_tanks_status(estacion_id)
            alerts_data = ReportDataService.get_alerts_data(estacion_id, date_range)
            consumption_metrics = ReportDataService.get_consumption_metrics(estacion_id, date_range)

            # Generar gráfico de tendencias de consumo
            consumption_graph = ReportDataService.generate_consumption_graph(
                consumption_metrics['daily_trend']
            )

            return {
                'generated_at': timezone.now(),
                'date_range': date_range,
                'tanks_status': tanks_status,
                'alerts': alerts_data,
                'consumption_metrics': consumption_metrics,
                'graphs': {
                    'consumption_graph': consumption_graph
                }
            }
        except Exception as e:
            raise Exception(f"Error en get_report_data: {e}")

    @staticmethod
    def _get_date_range(date_range):
        """
        Calcula las fechas de inicio y fin basado en el rango.
        """
        end_date = timezone.now()
        if date_range == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_range == 'week':
            start_date = end_date - timedelta(days=7)
        elif date_range == 'month':
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=365)
        return start_date, end_date
