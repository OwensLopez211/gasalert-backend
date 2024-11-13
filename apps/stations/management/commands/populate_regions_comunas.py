import os
import django
from django.core.management.base import BaseCommand  # Añadida esta importación

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')  # Cambiado a tu configuración
django.setup()

import json
from apps.stations.models import Region, Comuna  # Cambiado a tus modelos

class Command(BaseCommand):
    help = 'Populate Regions and Comunas from JSON file'

    def handle(self, *args, **options):
        # Construye la ruta al archivo JSON en la carpeta `data`
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        json_path = os.path.join(base_dir, 'data', 'regiones_comunas.json')  # Cambiado el nombre del archivo

        # Imprimir la ruta completa para verificarla
        self.stdout.write(f"Ruta completa al archivo JSON: {json_path}")

        # Abrir y leer el archivo JSON
        try:
            with open(json_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Archivo JSON cargado correctamente. Total de regiones: {len(data['regiones'])}"
                    )
                )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR("Error: No se encontró el archivo JSON.")
            )
            return
        except json.JSONDecodeError:
            self.stdout.write(
                self.style.ERROR("Error: El archivo JSON no tiene un formato válido.")
            )
            return

        # Iterar sobre las regiones y comunas
        for region_data in data['regiones']:
            region_name = region_data['region']
            self.stdout.write(f"Procesando región: {region_name}")

            # Crear o obtener la región
            region_instance, created = Region.objects.get_or_create(
                nombre=region_name
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Región creada: {region_name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Región ya existente: {region_name}")
                )

            # Iterar sobre las comunas de la región
            for comuna_name in region_data['comunas']:
                # Crear o obtener la comuna y asociarla con la región
                comuna_instance, created = Comuna.objects.get_or_create(
                    nombre=comuna_name,
                    region=region_instance
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Comuna creada: {comuna_name}")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Comuna ya existente: {comuna_name}")
                    )

        self.stdout.write(
            self.style.SUCCESS("Regiones y comunas cargadas exitosamente.")
        )