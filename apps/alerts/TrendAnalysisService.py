from django.utils import timezone
from django.db.models import Avg, StdDev
from datetime import timedelta
import numpy as np
from .models import Alerta, Lectura
import logging

logger = logging.getLogger(__name__)

class TrendAnalysisService:
    def __init__(self):
        self.VENTANA_ANALISIS = timedelta(hours=24)
        self.UMBRAL_DESVIACION = 2.0  # Desviaciones estándar para considerar inusual
        self.MIN_LECTURAS = 10  # Mínimo de lecturas para análisis

    def analizar_tendencias(self, tanque_id, nueva_lectura):
        """
        Analiza tendencias y genera alertas si es necesario
        """
        try:
            alertas = []
            
            # Obtener lecturas históricas
            lecturas = self._obtener_lecturas_historicas(tanque_id)
            if len(lecturas) < self.MIN_LECTURAS:
                return alertas

            # Analizar diferentes tipos de tendencias
            alertas.extend(self._analizar_consumo(tanque_id, lecturas, nueva_lectura))
            alertas.extend(self._analizar_frecuencia_critica(tanque_id))
            alertas.extend(self._analizar_reposiciones(tanque_id))

            return alertas

        except Exception as e:
            logger.error(f"Error en análisis de tendencias: {str(e)}")
            return []

    def _obtener_lecturas_historicas(self, tanque_id):
        """Obtiene lecturas históricas para análisis"""
        fecha_inicio = timezone.now() - self.VENTANA_ANALISIS
        return list(Lectura.objects.filter(
            tanque_id=tanque_id,
            fecha__gte=fecha_inicio
        ).order_by('fecha'))

    def _analizar_consumo(self, tanque_id, lecturas_historicas, nueva_lectura):
        """Analiza patrones de consumo inusuales"""
        alertas = []
        try:
            # Calcular tasas de cambio históricas
            tasas_cambio = self._calcular_tasas_cambio(lecturas_historicas)
            if not tasas_cambio:
                return alertas

            # Calcular estadísticas
            media = np.mean(tasas_cambio)
            std = np.std(tasas_cambio)

            # Calcular tasa actual
            ultima_lectura = lecturas_historicas[-1]
            tiempo_delta = (nueva_lectura['fecha'] - ultima_lectura.fecha).total_seconds() / 3600
            
            if tiempo_delta > 0:
                tasa_actual = (nueva_lectura['nivel'] - ultima_lectura.nivel) / tiempo_delta
                desviacion = abs(tasa_actual - media) / std if std > 0 else 0

                # Detectar consumo inusual
                if desviacion > self.UMBRAL_DESVIACION:
                    alerta = Alerta(
                        tanque_id=tanque_id,
                        tipo_tendencia='CONSUMO_INUSUAL',
                        nivel_detectado=nueva_lectura['nivel'],
                        valor_anterior=ultima_lectura.nivel,
                        tasa_cambio=tasa_actual,
                        valor_esperado=media,
                        desviacion=desviacion,
                        notas=f"Consumo inusual detectado: {tasa_actual:.2f}%/hora (Normal: {media:.2f}±{std:.2f}%/hora)"
                    )
                    alertas.append(alerta)

        except Exception as e:
            logger.error(f"Error en análisis de consumo: {str(e)}")

        return alertas

    def _analizar_frecuencia_critica(self, tanque_id):
        """Analiza frecuencia de niveles críticos"""
        alertas = []
        try:
            # Contar alertas críticas en las últimas 24 horas
            fecha_inicio = timezone.now() - timedelta(hours=24)
            count_criticas = Alerta.objects.filter(
                tanque_id=tanque_id,
                configuracion_umbral__tipo='CRITICO',
                fecha_generacion__gte=fecha_inicio
            ).count()

            if count_criticas >= 3:  # Umbral configurable
                alerta = Alerta(
                    tanque_id=tanque_id,
                    tipo_tendencia='FRECUENCIA_CRITICA',
                    nivel_detectado=0,  # Se actualiza al guardar
                    notas=f"Alta frecuencia de niveles críticos: {count_criticas} en las últimas 24 horas"
                )
                alertas.append(alerta)

        except Exception as e:
            logger.error(f"Error en análisis de frecuencia crítica: {str(e)}")

        return alertas

    def _analizar_reposiciones(self, tanque_id):
        """Analiza patrones inusuales en reposiciones"""
        alertas = []
        try:
            fecha_inicio = timezone.now() - timedelta(days=7)
            reposiciones = Lectura.objects.filter(
                tanque_id=tanque_id,
                fecha__gte=fecha_inicio
            ).order_by('fecha')

            if not reposiciones.exists():
                return alertas

            # Detectar reposiciones (incrementos significativos en nivel)
            reposiciones_detectadas = []
            for i in range(1, len(reposiciones)):
                if reposiciones[i].nivel - reposiciones[i-1].nivel > 10:  # Umbral configurable
                    reposiciones_detectadas.append(reposiciones[i])

            if reposiciones_detectadas:
                # Analizar horarios típicos de reposición
                horas_tipicas = [r.fecha.hour for r in reposiciones_detectadas]
                media_hora = np.mean(horas_tipicas)
                std_hora = np.std(horas_tipicas)

                # Verificar última reposición
                ultima_reposicion = reposiciones_detectadas[-1]
                desviacion_hora = abs(ultima_reposicion.fecha.hour - media_hora) / std_hora if std_hora > 0 else 0

                if desviacion_hora > self.UMBRAL_DESVIACION:
                    alerta = Alerta(
                        tanque_id=tanque_id,
                        tipo_tendencia='PATRON_REPOSICION',
                        nivel_detectado=ultima_reposicion.nivel,
                        notas=f"Reposición fuera de horario habitual: {ultima_reposicion.fecha.hour}:00 (Normal: {int(media_hora)}:00±{int(std_hora)}h)"
                    )
                    alertas.append(alerta)

        except Exception as e:
            logger.error(f"Error en análisis de reposiciones: {str(e)}")

        return alertas

    def _calcular_tasas_cambio(self, lecturas):
        """Calcula tasas de cambio entre lecturas consecutivas"""
        tasas = []
        for i in range(1, len(lecturas)):
            tiempo_delta = (lecturas[i].fecha - lecturas[i-1].fecha).total_seconds() / 3600
            if tiempo_delta > 0:
                tasa = (lecturas[i].nivel - lecturas[i-1].nivel) / tiempo_delta
                tasas.append(tasa)
        return tasas