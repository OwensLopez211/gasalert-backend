import logging
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import ConfiguracionUmbrales, Alerta, Notificacion

logger = logging.getLogger(__name__)

class AlertaService:
    @staticmethod
    def procesar_lectura(lectura):
        """
        Procesa una lectura y genera alertas si es necesario
        """
        try:
            with transaction.atomic():
                tanque = lectura.tanque
                umbrales = ConfiguracionUmbrales.objects.filter(
                    tanque=tanque,
                    activo=True
                ).select_related('tanque')

                for umbral in umbrales:
                    if AlertaService._debe_generar_alerta(lectura.nivel, umbral):
                        alerta = AlertaService._crear_alerta(lectura, umbral)
                        if alerta:
                            AlertaService._generar_notificaciones(alerta)

        except Exception as e:
            logger.error(f"Error procesando lectura {lectura.id}: {str(e)}")
            raise

    @staticmethod
    def _debe_generar_alerta(nivel, umbral):
        """Determina si se debe generar una alerta basada en el umbral"""
        if umbral.tipo in ['CRITICO', 'BAJO']:
            return nivel <= umbral.valor
        elif umbral.tipo in ['ALTO', 'LIMITE']:
            return nivel >= umbral.valor
        return False

    @staticmethod
    def _crear_alerta(lectura, umbral):
        """
        Crea una nueva alerta si no existe una activa para el mismo umbral
        """
        # Verificar si ya existe una alerta activa para este umbral
        alerta_existente = Alerta.objects.filter(
            tanque=lectura.tanque,
            configuracion_umbral=umbral,
            estado__in=['ACTIVA', 'NOTIFICADA']
        ).first()

        if not alerta_existente:
            return Alerta.objects.create(
                tanque=lectura.tanque,
                configuracion_umbral=umbral,
                nivel_detectado=lectura.nivel
            )
        return None

    @staticmethod
    def _generar_notificaciones(alerta):
        """Genera las notificaciones para una alerta"""
        # Obtener usuarios a notificar (administradores y supervisores de la estación)
        usuarios = AlertaService._obtener_usuarios_notificacion(alerta.tanque)

        for usuario in usuarios:
            # Notificación por email
            Notificacion.objects.create(
                alerta=alerta,
                tipo='EMAIL',
                destinatario=usuario,
                estado='PENDIENTE'
            )

            # Notificación en plataforma
            Notificacion.objects.create(
                alerta=alerta,
                tipo='PLATFORM',
                destinatario=usuario,
                estado='PENDIENTE'
            )

    @staticmethod
    def _obtener_usuarios_notificacion(tanque):
        """Obtiene los usuarios que deben ser notificados de una alerta"""
        from apps.stations.models import EstacionUsuarioRol
        return tanque.estacion.usuarios_roles.filter(
            activo=True,
            rol__in=['admin', 'supervisor']
        ).values_list('usuario', flat=True)

class NotificacionService:
    @staticmethod
    def procesar_notificaciones_pendientes():
        """Procesa las notificaciones pendientes"""
        notificaciones = Notificacion.objects.filter(
            estado='PENDIENTE'
        ).select_related('alerta', 'destinatario')

        for notificacion in notificaciones:
            try:
                if notificacion.tipo == 'EMAIL':
                    NotificacionService._enviar_email(notificacion)
                elif notificacion.tipo == 'PLATFORM':
                    NotificacionService._enviar_platform(notificacion)
            except Exception as e:
                logger.error(f"Error enviando notificación {notificacion.id}: {str(e)}")
                notificacion.registrar_error(str(e))

    @staticmethod
    def _enviar_email(notificacion):
        """Envía notificación por email"""
        try:
            alerta = notificacion.alerta
            subject = f"Alerta de nivel {alerta.configuracion_umbral.get_tipo_display()} en {alerta.tanque.nombre}"
            message = f"""
            Se ha detectado un nivel {alerta.configuracion_umbral.get_tipo_display()} en el tanque {alerta.tanque.nombre}

            Nivel detectado: {alerta.nivel_detectado}%
            Umbral: {alerta.configuracion_umbral.valor}%
            Fecha: {alerta.fecha_generacion}

            Por favor, revise la plataforma para más detalles.
            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [notificacion.destinatario.email],
                fail_silently=False
            )

            notificacion.marcar_como_enviada()

        except Exception as e:
            logger.error(f"Error enviando email: {str(e)}")
            notificacion.registrar_error(str(e))

    @staticmethod
    def _enviar_platform(notificacion):
        """Envía notificación a través de websocket"""
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{notificacion.destinatario.id}",
                {
                    "type": "notify_alert",
                    "message": {
                        "alerta_id": notificacion.alerta.id,
                        "tipo": notificacion.alerta.configuracion_umbral.tipo,
                        "tanque": notificacion.alerta.tanque.nombre,
                        "nivel": notificacion.alerta.nivel_detectado,
                        "fecha": notificacion.alerta.fecha_generacion.isoformat()
                    }
                }
            )

            notificacion.marcar_como_enviada()

        except Exception as e:
            logger.error(f"Error enviando notificación websocket: {str(e)}")
            notificacion.registrar_error(str(e))