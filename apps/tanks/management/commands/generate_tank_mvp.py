from django.core.management.base import BaseCommand
from apps.tanks.models import Lectura, Tanque
from datetime import datetime, timedelta
import random

class Command(BaseCommand):
    help = "Genera lecturas simuladas para el tanque MVP (ID 5) con patrones realistas"

    def handle(self, *args, **kwargs):
        try:
            # Configuración del tanque MVP
            tanque_id = 5
            tanque_capacidad = 12.0  # Litros
            tanque_llenado = tanque_capacidad * 0.9  # 90% de la capacidad
            personas = 3

            # Rango de tiempo: últimos 3 meses
            fecha_final = datetime.now()
            fecha_inicial = fecha_final - timedelta(days=90)

            # Obtener el tanque
            tanque = Tanque.objects.get(id=tanque_id)
            volumen_actual = tanque_llenado  # Inicialmente lleno al 90%

            lecturas = []
            fecha_actual = fecha_inicial

            while fecha_actual <= fecha_final:
                # Determinar consumo por horario
                hora = fecha_actual.hour
                consumo = 0

                if 8 <= hora < 18:  # Día: consumo bajo (personas fuera)
                    consumo = random.uniform(0, 0.05 * personas)
                elif 18 <= hora < 24:  # Noche: consumo moderado
                    consumo = random.uniform(0.1, 0.3 * personas)
                else:  # Madrugada: consumo muy bajo
                    consumo = random.uniform(0, 0.02 * personas)

                # Fines de semana: consumo más alto durante el día
                if fecha_actual.weekday() in [5, 6]:  # Sábado y domingo
                    if 8 <= hora < 18:
                        consumo *= random.uniform(1.2, 1.5)

                # Aplicar anomalías ocasionales
                if random.random() < 0.02:  # 2% de probabilidad de anomalía
                    consumo *= random.uniform(2, 5)

                # Reducir el volumen del tanque
                volumen_actual -= consumo

                # Llenar el tanque si llega a 0
                if volumen_actual <= 0:
                    volumen_actual = tanque_llenado

                # Registrar la lectura
                lecturas.append(
                    Lectura(
                        tanque=tanque,
                        fecha=fecha_actual,
                        nivel=round((volumen_actual / tanque_capacidad) * 100, 2),
                        volumen=round(volumen_actual, 2),
                        temperatura=round(random.uniform(15, 35), 2),
                    )
                )

                # Avanzar una hora
                fecha_actual += timedelta(hours=1)

                # Crear lecturas en lotes para mejorar el rendimiento
                if len(lecturas) >= 1000:
                    Lectura.objects.bulk_create(lecturas, batch_size=1000)
                    lecturas = []

            # Insertar las lecturas restantes
            if lecturas:
                Lectura.objects.bulk_create(lecturas, batch_size=1000)

            self.stdout.write(self.style.SUCCESS("¡Lecturas simuladas para el tanque MVP generadas con éxito!"))

        except Exception as e:
            self.stderr.write(f"Error al generar datos simulados para el tanque MVP: {e}")
