from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.stations.models import Estacion
from apps.tanks.models import TipoCombustible, Tanque, Lectura, Umbral
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Genera datos de prueba para el dashboard de tanques'

    def handle(self, *args, **options):
        # Crear usuario administrador si no existe
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'is_staff': True,
                'is_superuser': True,
                'email': 'admin@example.com'
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Usuario admin creado'))

        # Crear estación
        estacion, created = Estacion.objects.get_or_create(
            nombre='Estación de Prueba',
            defaults={
                'ubicacion': 'Ubicación de Prueba',
                'creado_por': admin_user
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Estación creada'))

        # Crear tipos de combustible
        tipos_combustible = [
            {'tipo': '93', 'descripcion': 'Gasolina 93 octanos'},
            {'tipo': '95', 'descripcion': 'Gasolina 95 octanos'},
            {'tipo': '97', 'descripcion': 'Gasolina 97 octanos'},
            {'tipo': 'Diesel', 'descripcion': 'Petróleo Diesel'}
        ]

        for tipo_data in tipos_combustible:
            tipo, created = TipoCombustible.objects.get_or_create(
                tipo=tipo_data['tipo'],
                defaults={'descripcion': tipo_data['descripcion']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Tipo de combustible {tipo.tipo} creado'))

        # Crear tanques
        capacidades = {
            '93': 20000,
            '95': 15000,
            '97': 10000,
            'Diesel': 25000
        }

        for tipo in TipoCombustible.objects.all():
            tanque, created = Tanque.objects.get_or_create(
                nombre=f'Tanque {tipo.tipo}',
                defaults={
                    'tipo_combustible': tipo,
                    'estacion': estacion,
                    'capacidad_total': capacidades[tipo.tipo],
                    'descripcion': f'Tanque de {tipo.tipo}'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Tanque {tanque.nombre} creado'))
                
                # Crear umbral para el tanque
                Umbral.objects.get_or_create(
                    tanque=tanque,
                    defaults={
                        'umbral_maximo': 90.0,
                        'umbral_minimo': 20.0,
                        'modificado_por': admin_user
                    }
                )

                # Generar lecturas para los últimos 7 días
                now = timezone.now()
                nivel_actual = random.uniform(40.0, 80.0)
                
                for i in range(7 * 24):  # 7 días x 24 horas
                    fecha = now - timedelta(hours=i)
                    # Simular consumo y recargas
                    if nivel_actual < 30.0:  # Simular recarga
                        nivel_actual = random.uniform(70.0, 90.0)
                    else:  # Simular consumo normal
                        nivel_actual -= random.uniform(0.1, 1.0)
                        nivel_actual = max(10.0, nivel_actual)  # No bajar de 10%

                    volumen = (nivel_actual / 100.0) * tanque.capacidad_total
                    
                    Lectura.objects.create(
                        tanque=tanque,
                        fecha=fecha,
                        nivel=nivel_actual,
                        volumen=volumen,
                        temperatura=random.uniform(20.0, 30.0)
                    )

        self.stdout.write(self.style.SUCCESS('Datos de prueba generados exitosamente'))