import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import Alerta, Notificacion
from .services import NotificacionService, AlertaService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def procesar_notificaciones(self):
    """Procesa las notificaciones pendientes"""
    try:
        logger.info("Iniciando procesamiento de notificaciones")
        NotificacionService.procesar_notificaciones_pendientes()
        logger.info("Procesamiento de notificaciones completado")
    except Exception as e:
        logger.error(f"Error procesando notificaciones: {str(e)}")
        self.retry(countdown=60)  # Reintentar en 1 minuto

@shared_task(bind=True)
def verificar_alertas_no_atendidas(self):
    """Verifica alertas que no han sido atendidas y reenvía notificaciones"""
    try:
        # Buscar alertas no atendidas después de cierto tiempo
        tiempo_limite = timezone.now() - timedelta(hours=1)
        alertas_no_atendidas = Alerta.objects.filter(
            estado__in=['ACTIVA', 'NOTIFICADA'],
            fecha_generacion__lt=tiempo_limite
        )

        for alerta in alertas_no_atendidas:
            # Crear nueva notificación de recordatorio
            Notificacion.objects.create(
                alerta=alerta,
                tipo='EMAIL',
                destinatario=alerta.tanque.estacion.creado_por,
                estado='PENDIENTE'
            )
            
            logger.info(f"Recordatorio creado para alerta {alerta.id}")

    except Exception as e:
        logger.error(f"Error verificando alertas no atendidas: {str(e)}")

@shared_task
def limpiar_alertas_antiguas():
    """Limpia alertas resueltas antiguas"""
    try:
        # Eliminar alertas resueltas con más de 30 días
        fecha_limite = timezone.now() - timedelta(days=30)
        
        alertas_antiguas = Alerta.objects.filter(
            estado='RESUELTA',
            fecha_resolucion__lt=fecha_limite
        )
        
        total_eliminadas = alertas_antiguas.count()
        alertas_antiguas.delete()
        
        logger.info(f"Se eliminaron {total_eliminadas} alertas antiguas")
        
    except Exception as e:
        logger.error(f"Error limpiando alertas antiguas: {str(e)}")

@shared_task(bind=True)
def procesar_alerta(self, lectura_id):
    """Procesa una lectura específica para generar alertas si es necesario"""
    from apps.tanks.models import Lectura
    
    try:
        lectura = Lectura.objects.get(id=lectura_id)
        AlertaService.procesar_lectura(lectura)
        logger.info(f"Lectura {lectura_id} procesada para alertas")
    except Lectura.DoesNotExist:
        logger.error(f"No se encontró la lectura {lectura_id}")
    except Exception as e:
        logger.error(f"Error procesando alerta para lectura {lectura_id}: {str(e)}")
        self.retry(countdown=30)