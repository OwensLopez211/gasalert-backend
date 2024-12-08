from django.core.management.base import BaseCommand
from apps.tanks.models import Lectura, Tanque
from datetime import datetime, timedelta
import random


class Command(BaseCommand):
    help = 'Genera lecturas simuladas minuto a minuto para los últimos 9 meses de cada tanque con mayor variabilidad'

    def handle(self, *args, **kwargs):
        try:
            # Configuración de los tanques
            tanques = [
                {"id": 3, "capacidad": 10000, "consumo_horario": (15, 25)},  # Bencina 93
                {"id": 4, "capacidad": 25000, "consumo_horario": (30, 50)},  # Bencina 95
                {"id": 2, "capacidad": 15000, "consumo_horario": (40, 70)},  # Diesel
            ]

            # Configuración de tiempo
            fecha_final = datetime.now()
            fecha_inicial = fecha_final - timedelta(days=270)  # Últimos 9 meses

            # Variabilidad por semana
            def get_weekly_variation(week_number):
                """
                Genera una variación semanal basada en un número de semana.
                """
                random.seed(week_number)
                return random.uniform(0.8, 1.2)  # Variación entre 80% y 120%

            # Iterar sobre cada tanque
            for tanque_data in tanques:
                tanque = Tanque.objects.get(id=tanque_data["id"])
                capacidad = tanque_data["capacidad"]
                volumen_actual = capacidad * random.uniform(0.75, 0.85)  # Comenzar entre 75%-85%

                self.stdout.write(f"Generando datos para el tanque {tanque.nombre} (ID: {tanque.id})...")

                # Iterar por cada minuto en el rango de tiempo
                fecha_actual = fecha_inicial
                lecturas = []

                while fecha_actual <= fecha_final:
                    week_number = fecha_actual.isocalendar()[1]
                    daily_variation = random.uniform(0.9, 1.1)  # Variación diaria adicional
                    weekly_factor = get_weekly_variation(week_number)

                    # Consumo base ajustado por hora y semana
                    hora = fecha_actual.hour
                    if 6 <= hora < 10 or 16 <= hora < 20:  # Horas pico
                        consumo_por_minuto = (
                            random.uniform(*tanque_data["consumo_horario"]) / 60 * 1.2 * weekly_factor * daily_variation
                        )
                    else:
                        consumo_por_minuto = (
                            random.uniform(*tanque_data["consumo_horario"]) / 60 * 0.8 * weekly_factor * daily_variation
                        )

                    # Ajustes estacionales
                    if fecha_actual.month in [6, 7, 8]:  # Invierno
                        if tanque.nombre == "Diesel":
                            consumo_por_minuto *= 1.25
                    elif fecha_actual.month in [12, 1, 2]:  # Verano
                        if tanque.nombre in ["Bencina 93", "Bencina 95"]:
                            consumo_por_minuto *= 1.15

                    # Ajustes por días de la semana
                    if fecha_actual.weekday() in [5, 6]:  # Fin de semana
                        consumo_por_minuto *= 0.9

                    # Reducir el volumen según el consumo
                    volumen_actual -= consumo_por_minuto

                    # Simulación de reabastecimiento
                    if volumen_actual <= capacidad * random.uniform(0.15, 0.25):  # Umbral crítico ajustado aleatoriamente
                        volumen_actual = capacidad

                    # Evitar valores negativos
                    volumen_actual = max(0, volumen_actual)

                    # Nivel en porcentaje
                    nivel = (volumen_actual / capacidad) * 100

                    # Crear la lectura
                    lecturas.append(
                        Lectura(
                            tanque=tanque,
                            fecha=fecha_actual,
                            nivel=round(nivel, 2),
                            volumen=round(volumen_actual, 2),
                        )
                    )

                    # Avanzar un minuto
                    fecha_actual += timedelta(minutes=1)

                    # Guardar en lotes para optimizar rendimiento
                    if len(lecturas) >= 1000:
                        Lectura.objects.bulk_create(lecturas, batch_size=1000)
                        lecturas = []

                # Insertar las lecturas restantes
                if lecturas:
                    Lectura.objects.bulk_create(lecturas, batch_size=1000)

                self.stdout.write(self.style.SUCCESS(f"Datos generados para el tanque {tanque.nombre}"))

            self.stdout.write(self.style.SUCCESS("¡Datos simulados generados exitosamente!"))

        except Exception as e:
            self.stderr.write(f"Error al generar datos simulados: {e}")
