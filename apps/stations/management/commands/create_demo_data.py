from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.stations.models import Region, Comuna, Estacion, EstacionUsuarioRol, Ubicacion
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Crea datos de demostración para desarrollo'

    def handle(self, *args, **options):
        self.stdout.write('Creando datos de demostración...')

        try:
            with transaction.atomic():
                # Crear usuarios de prueba si no existen
                admin, created = User.objects.get_or_create(
                    username='admin',
                    defaults={
                        'email': 'admin@example.com',
                        'is_superuser': True,
                        'is_staff': True
                    }
                )
                if created:
                    admin.set_password('admin123')
                    admin.save()
                    self.stdout.write(self.style.SUCCESS('Usuario admin creado'))

                supervisor, created = User.objects.get_or_create(
                    username='supervisor',
                    defaults={'email': 'supervisor@example.com'}
                )
                if created:
                    supervisor.set_password('supervisor123')
                    supervisor.save()
                    self.stdout.write(self.style.SUCCESS('Usuario supervisor creado'))

                operador, created = User.objects.get_or_create(
                    username='operador',
                    defaults={'email': 'operador@example.com'}
                )
                if created:
                    operador.set_password('operador123')
                    operador.save()
                    self.stdout.write(self.style.SUCCESS('Usuario operador creado'))

                # Verificar que existan regiones y comunas
                region = Region.objects.first()
                if not region:
                    region = Region.objects.create(nombre='Región Metropolitana')
                    self.stdout.write(self.style.SUCCESS('Región creada'))

                comuna = Comuna.objects.filter(region=region).first()
                if not comuna:
                    comuna = Comuna.objects.create(
                        nombre='Santiago',
                        region=region
                    )
                    self.stdout.write(self.style.SUCCESS('Comuna creada'))

                # Crear estaciones
                for i in range(1, 11):  # Crear 10 estaciones
                    nombre = f'Estación Demo {i}'
                    
                    # Verificar si la estación ya existe
                    if not Estacion.objects.filter(nombre=nombre).exists():
                        estacion = Estacion.objects.create(
                            nombre=nombre,
                            ubicacion=f'Ubicación {i}',
                            descripcion=f'Estación de demostración número {i}',
                            creado_por=admin
                        )

                        # Crear ubicación
                        Ubicacion.objects.create(
                            estacion=estacion,
                            comuna=comuna,
                            direccion_detalle=f'Dirección {i}',
                            coordenadas=f'-33.{random.randint(400,500)},-70.{random.randint(600,700)}'
                        )

                        # Asignar roles
                        if i <= 3:
                            EstacionUsuarioRol.objects.create(
                                usuario=supervisor,
                                estacion=estacion,
                                rol='supervisor',
                                activo=True
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Rol supervisor asignado a Estación {i}'
                                )
                            )

                        if i <= 5:
                            EstacionUsuarioRol.objects.create(
                                usuario=operador,
                                estacion=estacion,
                                rol='operador',
                                activo=True
                            )
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'Rol operador asignado a Estación {i}'
                                )
                            )

                        self.stdout.write(
                            self.style.SUCCESS(f'Estación {i} creada')
                        )

                self.stdout.write(
                    self.style.SUCCESS('Datos de demostración creados exitosamente')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando datos de demo: {str(e)}')
            )