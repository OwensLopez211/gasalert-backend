from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Lectura, Umbral, Tanque

@receiver(post_save, sender=Lectura)
def verificar_umbrales_lectura(sender, instance, created, **kwargs):
    """
    Verifica los umbrales cuando se crea una nueva lectura
    y genera alertas si es necesario
    """
    if created:
        try:
            umbral = instance.tanque.umbrales.latest('modificado_en')
            if instance.nivel >= umbral.umbral_maximo:
                # Aquí irá la lógica para generar alerta por nivel alto
                pass
            elif instance.nivel <= umbral.umbral_minimo:
                # Aquí irá la lógica para generar alerta por nivel bajo
                pass
        except Umbral.DoesNotExist:
            pass

@receiver(post_save, sender=Umbral)
def registrar_cambio_umbral(sender, instance, created, **kwargs):
    """
    Registra los cambios en el historial cuando se modifica un umbral
    """
    if not created:
        from .models import HistorialUmbrales
        umbral_anterior = Umbral.objects.filter(
            tanque=instance.tanque
        ).exclude(id=instance.id).order_by('-modificado_en').first()
        
        if umbral_anterior:
            HistorialUmbrales.objects.create(
                tanque=instance.tanque,
                umbral_anterior=umbral_anterior.umbral_maximo,
                umbral_nuevo=instance.umbral_maximo,
                fecha_modificacion=timezone.now(),
                modificado_por=instance.modificado_por
            )

@receiver(post_save, sender=Tanque)
def crear_umbral_inicial(sender, instance, created, **kwargs):
    """
    Crea un umbral inicial cuando se crea un nuevo tanque
    """
    if created:
        Umbral.objects.create(
            tanque=instance,
            umbral_maximo=90.0,  # Valores por defecto
            umbral_minimo=20.0,
            modificado_por=instance.estacion.creado_por
        )