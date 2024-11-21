from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from apps.tanks.models import Tanque, Lectura


class Command(BaseCommand):
    help = 'Genera datos históricos de prueba para los tanques con trazabilidad realista'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Número de días de histórico a generar'
        )
        parser.add_argument(
            '--frequency',
            type=int,
            default=5,
            help='Frecuencia de lecturas en minutos'
        )

    def handle(self, *args, **options):
        days = options['days']
        frequency = options['frequency']

        # Obtener tanques específicos
        tanques = Tanque.objects.filter(id__in=[2, 3, 4, 5], activo=True)

        if not tanques.exists():
            self.stdout.write(
                self.style.ERROR('No se encontraron tanques activos con los IDs especificados')
            )
            return

        # Definir las capacidades de los tanques según los IDs proporcionados
        capacidades = {
            2: 15000,
            3: 10000,
            4: 25000,
            5: 12,
        }

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        for tanque in tanques:
            capacidad_total = capacidades.get(tanque.id, tanque.capacidad_total)
            self.stdout.write(
                self.style.SUCCESS(f'Generando datos para tanque: {tanque.nombre}')
            )

            # Inicializar nivel y volumen
            nivel_actual = random.uniform(70, 90)  # Nivel inicial entre 70% y 90%
            volumen_actual = (nivel_actual / 100) * capacidad_total

            current_date = start_date
            lecturas_creadas = 0
            dias_desde_ultima_recarga = 0  # Para controlar las recargas

            while current_date <= end_date:
                # Disminuir nivel y volumen gradualmente por ventas
                disminucion = random.uniform(0.5, 1.5)  # Disminución realista por venta
                nivel_actual -= disminucion
                volumen_actual = (nivel_actual / 100) * capacidad_total

                # Garantizar que el nivel nunca llegue a cero
                if nivel_actual < 10:  # Si está cerca de 0, recargar inmediatamente
                    self.stdout.write(self.style.WARNING(f'Recargando tanque {tanque.nombre}...'))
                    nivel_actual = random.uniform(70, 90)  # Recarga a un nivel seguro
                    volumen_actual = (nivel_actual / 100) * capacidad_total
                    dias_desde_ultima_recarga = 0  # Reiniciar contador de días

                # Crear lectura
                Lectura.objects.create(
                    tanque=tanque,
                    fecha=current_date,
                    nivel=nivel_actual,
                    volumen=volumen_actual,
                )
                lecturas_creadas += 1

                # Avanzar en el tiempo
                current_date += timedelta(minutes=frequency)
                dias_desde_ultima_recarga += (frequency / 1440)  # Incrementar días

            self.stdout.write(
                self.style.SUCCESS(
                    f'Creadas {lecturas_creadas} lecturas para {tanque.nombre}'
                )
            )

        self.stdout.write(
            self.style.SUCCESS('Generación de datos completada')
        )
