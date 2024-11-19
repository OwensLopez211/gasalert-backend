# apps/tanks/management/commands/calcular_promedios_iniciales.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg
from apps.tanks.models import Tanque, Lectura, PromedioLectura

class Command(BaseCommand):
    help = 'Calcula los promedios iniciales para todos los tanques'

    def handle(self, *args, **options):
        now = timezone.now()
        interval_start = now - timedelta(minutes=10)
        tanques = Tanque.objects.filter(activo=True)
        
        for tanque in tanques:
            try:
                lecturas = Lectura.objects.filter(
                    tanque=tanque,
                    fecha__gte=interval_start,
                    fecha__lte=now
                )
                
                if lecturas.exists():
                    promedios = lecturas.aggregate(
                        nivel_promedio=Avg('nivel'),
                        volumen_promedio=Avg('volumen'),
                        temperatura_promedio=Avg('temperatura')
                    )
                    
                    PromedioLectura.objects.create(
                        tanque=tanque,
                        fecha_inicio=interval_start,
                        fecha_fin=now,
                        nivel_promedio=promedios['nivel_promedio'],
                        volumen_promedio=promedios['volumen_promedio'],
                        temperatura_promedio=promedios['temperatura_promedio'],
                        cantidad_lecturas=lecturas.count()
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Promedios calculados para tanque {tanque.nombre}'
                        )
                    )
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Error calculando promedios para tanque {tanque.nombre}: {str(e)}'
                    )
                )