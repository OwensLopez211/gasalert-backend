from django.core.management.base import BaseCommand
from apps.tanks.models import Tanque
from apps.alerts.models import ConfiguracionUmbrales
from django.db import transaction

class Command(BaseCommand):
    help = 'Configura umbrales de prueba para un tanque'

    def add_arguments(self, parser):
        parser.add_argument('tanque_id', type=int)

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                tanque = Tanque.objects.get(id=options['tanque_id'])
                
                # Configuración de umbrales predeterminados
                umbrales = [
                    ('CRITICO', 20.0),
                    ('BAJO', 30.0),
                    ('MEDIO', 50.0),
                    ('ALTO', 70.0),
                    ('LIMITE', 90.0)
                ]
                
                for tipo, valor in umbrales:
                    ConfiguracionUmbrales.objects.create(
                        tanque=tanque,
                        tipo=tipo,
                        valor=valor,
                        activo=True,
                        modificado_por=tanque.estacion.creado_por
                    )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Umbrales configurados exitosamente para el tanque {tanque.nombre}'
                    )
                )
                
        except Tanque.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'No se encontró el tanque con ID {options["tanque_id"]}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            )