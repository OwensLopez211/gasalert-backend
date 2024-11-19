from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Alerta
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

class AlertaConsumer(JsonWebsocketConsumer):
    def connect(self):
        """Maneja la conexión del WebSocket"""
        # Verificar si el usuario está autenticado
        if self.scope["user"].is_anonymous:
            self.close()
        else:
            # Añadir al grupo específico del usuario
            self.user_group = f"user_{self.scope['user'].id}"
            async_to_sync(self.channel_layer.group_add)(
                self.user_group,
                self.channel_name
            )
            
            # Añadir a grupos basados en las estaciones del usuario
            estaciones = self.scope["user"].roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            
            for estacion_id in estaciones:
                group_name = f"estacion_{estacion_id}"
                async_to_sync(self.channel_layer.group_add)(
                    group_name,
                    self.channel_name
                )
            
            self.accept()
            
            # Enviar alertas activas al conectar
            self.send_active_alerts()

    def disconnect(self, close_code):
        """Maneja la desconexión del WebSocket"""
        if not self.scope["user"].is_anonymous:
            # Remover del grupo del usuario
            async_to_sync(self.channel_layer.group_discard)(
                self.user_group,
                self.channel_name
            )
            
            # Remover de los grupos de estaciones
            estaciones = self.scope["user"].roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            
            for estacion_id in estaciones:
                group_name = f"estacion_{estacion_id}"
                async_to_sync(self.channel_layer.group_discard)(
                    group_name,
                    self.channel_name
                )

    def send_active_alerts(self):
        """Envía las alertas activas al cliente cuando se conecta"""
        try:
            # Obtener alertas activas relevantes para el usuario
            alertas = Alerta.objects.filter(
                estado__in=['ACTIVA', 'NOTIFICADA'],
                tanque__estacion__in=self.scope["user"].roles_estaciones.filter(
                    activo=True
                ).values_list('estacion_id', flat=True)
            ).select_related('tanque', 'configuracion_umbral')

            # Enviar cada alerta
            for alerta in alertas:
                self.send_json({
                    'type': 'alert.active',
                    'alert': {
                        'id': alerta.id,
                        'tanque': alerta.tanque.nombre,
                        'tipo': alerta.configuracion_umbral.tipo,
                        'nivel': alerta.nivel_detectado,
                        'umbral': alerta.configuracion_umbral.valor,
                        'fecha': alerta.fecha_generacion.isoformat(),
                        'estado': alerta.estado
                    }
                })
        except Exception as e:
            logger.error(f"Error enviando alertas activas: {str(e)}")

    def notify_alert(self, event):
        """Maneja la notificación de nuevas alertas"""
        try:
            self.send_json(event["message"])
        except Exception as e:
            logger.error(f"Error enviando notificación de alerta: {str(e)}")

    def receive_json(self, content, **kwargs):
        """Maneja los mensajes recibidos del cliente"""
        try:
            action = content.get('action')
            
            if action == 'mark_as_read':
                alerta_id = content.get('alert_id')
                self.mark_alert_as_read(alerta_id)
            elif action == 'acknowledge':
                alerta_id = content.get('alert_id')
                self.acknowledge_alert(alerta_id)
        except Exception as e:
            logger.error(f"Error procesando mensaje del cliente: {str(e)}")
            self.send_json({
                'type': 'error',
                'message': str(e)
            })

    def mark_alert_as_read(self, alerta_id):
        """Marca una alerta como leída"""
        try:
            alerta = Alerta.objects.get(
                id=alerta_id,
                tanque__estacion__in=self.scope["user"].roles_estaciones.filter(
                    activo=True
                ).values_list('estacion_id', flat=True)
            )
            
            if alerta.estado == 'ACTIVA':
                alerta.estado = 'NOTIFICADA'
                alerta.save()
                
                self.send_json({
                    'type': 'alert.updated',
                    'alert_id': alerta_id,
                    'status': 'NOTIFICADA'
                })
        except Alerta.DoesNotExist:
            self.send_json({
                'type': 'error',
                'message': 'Alerta no encontrada o sin permisos'
            })

    def acknowledge_alert(self, alerta_id):
        """Reconoce una alerta"""
        try:
            alerta = Alerta.objects.get(
                id=alerta_id,
                tanque__estacion__in=self.scope["user"].roles_estaciones.filter(
                    activo=True
                ).values_list('estacion_id', flat=True)
            )
            
            if alerta.estado in ['ACTIVA', 'NOTIFICADA']:
                alerta.estado = 'ATENDIDA'
                alerta.atendida_por = self.scope["user"]
                alerta.fecha_atencion = timezone.now()
                alerta.save()
                
                self.send_json({
                    'type': 'alert.updated',
                    'alert_id': alerta_id,
                    'status': 'ATENDIDA'
                })
        except Alerta.DoesNotExist:
            self.send_json({
                'type': 'error',
                'message': 'Alerta no encontrada o sin permisos'
            })