from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from .models import Alerta, Notificacion

logger = logging.getLogger(__name__)

class AlertaNotificationService:
    def __init__(self):
        self.channel_layer = get_channel_layer()

    def send_notifications(self, alerta):
        """
        Método principal para enviar todas las notificaciones
        """
        try:
            with transaction.atomic():
                # Obtener destinatarios
                destinatarios = self._get_alert_recipients(alerta)
                
                # Enviar notificaciones
                self._send_email_notification(alerta, destinatarios)
                self._send_websocket_notification(alerta)
                self._create_notification_records(alerta, destinatarios)
                
                # Actualizar estado de la alerta
                alerta.estado = 'NOTIFICADA'
                alerta.save()
                
                logger.info(f"Notificaciones enviadas exitosamente para alerta {alerta.id}")
                
        except Exception as e:
            logger.error(f"Error enviando notificaciones para alerta {alerta.id}: {str(e)}")
            raise

    def _get_alert_recipients(self, alerta):
        """Obtiene los usuarios que deben recibir la notificación"""
        return alerta.tanque.estacion.usuarios_roles.filter(
            activo=True,
            rol__in=['admin', 'supervisor']
        ).select_related('usuario')

    def _send_email_notification(self, alerta, destinatarios):
        """Envía notificación por email"""
        try:
            # Construir mensaje de email
            subject = f"Alerta de nivel en tanque {alerta.tanque.nombre}"
            message = f"""
            Se ha detectado un nivel {alerta.configuracion_umbral.get_tipo_display()} en el tanque:

            Estación: {alerta.tanque.estacion.nombre}
            Tanque: {alerta.tanque.nombre}
            Nivel detectado: {alerta.nivel_detectado}%
            Umbral: {alerta.configuracion_umbral.valor}%
            Fecha: {alerta.fecha_generacion.strftime('%d/%m/%Y %H:%M:%S')}

            Por favor, ingrese a la plataforma para ver más detalles y tomar las acciones necesarias.

            Este es un mensaje automático, por favor no responda a este correo.
            """
            
            # Enviar email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.usuario.email for user in destinatarios],
                fail_silently=False
            )
            
            logger.info(f"Email enviado exitosamente para alerta {alerta.id}")
            
        except Exception as e:
            logger.error(f"Error enviando email para alerta {alerta.id}: {str(e)}")
            raise

    def _send_websocket_notification(self, alerta):
        try:
            alert_data = {
                "id": alerta.id,
                "tipo": alerta.configuracion_umbral.tipo,
                "tanque_id": alerta.tanque.id,
                "tanque_nombre": alerta.tanque.nombre,
                "nivel_detectado": alerta.nivel_detectado,
                "umbral": alerta.configuracion_umbral.valor,
                "fecha_generacion": alerta.fecha_generacion.isoformat(),
                "estado": "NOTIFICADA",
            }

            async_to_sync(self.channel_layer.group_send)(
                f"station_{alerta.tanque.estacion.id}",
                {
                    "type": "notify_alert",
                    "message": {
                        "type": "new_alert",
                        "data": alert_data,
                    },
                },
            )
            logger.info(f"Notificación WebSocket enviada para alerta {alerta.id}")
        except Exception as e:
            logger.error(f"Error enviando notificación WebSocket para alerta {alerta.id}: {e}")


    def _create_notification_records(self, alerta, destinatarios):
        """Crea registros de notificación en la base de datos"""
        try:
            notifications = []
            for rol_usuario in destinatarios:
                # Notificación de plataforma
                notifications.append(
                    Notificacion(
                        alerta=alerta,
                        tipo='PLATFORM',
                        destinatario=rol_usuario.usuario,
                        estado='ENVIADA',
                        fecha_envio=timezone.now()
                    )
                )
                
                # Notificación de email
                notifications.append(
                    Notificacion(
                        alerta=alerta,
                        tipo='EMAIL',
                        destinatario=rol_usuario.usuario,
                        estado='ENVIADA',
                        fecha_envio=timezone.now()
                    )
                )
            
            # Crear todas las notificaciones en una sola operación
            Notificacion.objects.bulk_create(notifications)
            
            logger.info(f"Registros de notificación creados para alerta {alerta.id}")
            
        except Exception as e:
            logger.error(f"Error creando registros de notificación para alerta {alerta.id}: {str(e)}")
            raise

class AlertaService:
    def __init__(self):
        self.notification_service = AlertaNotificationService()

    def check_threshold_violation(self, tanque_id, nivel_actual):
        """Verifica violaciones de umbrales y genera alertas"""
        try:
            # Obtener umbrales activos del tanque
            umbrales = ConfiguracionUmbrales.objects.filter(
                tanque_id=tanque_id,
                activo=True
            ).select_related('tanque')

            alertas_generadas = []
            for umbral in umbrales:
                alerta_necesaria = self._evaluar_umbral(umbral, nivel_actual)
                if alerta_necesaria:
                    alerta = self._crear_alerta(umbral, nivel_actual)
                    alertas_generadas.append(alerta)
                    # Enviar notificaciones
                    self.notification_service.send_notifications(alerta)

            return alertas_generadas

        except Exception as e:
            logger.error(f"Error verificando umbrales para tanque {tanque_id}: {str(e)}")
            raise

    def _evaluar_umbral(self, umbral, nivel_actual):
        """Evalúa si se debe generar una alerta según el tipo de umbral"""
        # Verificar si ya existe una alerta activa para este umbral
        alerta_activa = Alerta.objects.filter(
            configuracion_umbral=umbral,
            estado__in=['ACTIVA', 'NOTIFICADA']
        ).exists()

        if alerta_activa:
            return False

        # Evaluar según el tipo de umbral
        if umbral.tipo in ['CRITICO', 'BAJO']:
            return nivel_actual <= umbral.valor
        elif umbral.tipo in ['ALTO', 'LIMITE']:
            return nivel_actual >= umbral.valor
        
        return False

    def _crear_alerta(self, umbral, nivel_actual):
        """Crea una nueva alerta en la base de datos"""
        return Alerta.objects.create(
            tanque=umbral.tanque,
            configuracion_umbral=umbral,
            nivel_detectado=nivel_actual,
            estado='ACTIVA'
        )

    def resolve_alert(self, alerta_id, user, notas=''):
        """Resuelve una alerta existente"""
        try:
            alerta = Alerta.objects.get(id=alerta_id)
            alerta.estado = 'RESUELTA'
            alerta.fecha_resolucion = timezone.now()
            alerta.atendida_por = user
            alerta.notas = notas
            alerta.save()
            
            return alerta

        except Alerta.DoesNotExist:
            logger.error(f"Alerta {alerta_id} no encontrada")
            raise