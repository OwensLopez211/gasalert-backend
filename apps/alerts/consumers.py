from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timezone import now
from .models import ConfiguracionUmbrales, Alerta
from .services import AlertaNotificationService
import logging

logger = logging.getLogger(__name__)

class AlertaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            logger.warning("Intento de conexión no autenticado")
        else:
            estaciones = await self._get_user_stations()
            for estacion_id in estaciones:
                await self.channel_layer.group_add(f"station_{estacion_id}", self.channel_name)
            await self.accept()
            logger.info(f"Usuario {self.user.id} conectado al WebSocket")

    async def disconnect(self, close_code):
        if not self.user.is_anonymous:
            estaciones = await self._get_user_stations()
            for estacion_id in estaciones:
                await self.channel_layer.group_discard(f"station_{estacion_id}", self.channel_name)
            logger.info(f"Usuario {self.user.id} desconectado del WebSocket")

    async def receive_json(self, content):
        message_type = content.get("type")

        if message_type == "tank_reading":
            if "tank_id" not in content or "nivel" not in content:
                logger.error("Datos incompletos en lectura de tanque")
                await self.send_json({"error": "Datos incompletos para lectura de tanque"})
                return
            await self._handle_tank_reading(content)
        else:
            logger.warning(f"Tipo de mensaje no soportado: {message_type}")
            await self.send_json({"error": "Tipo de mensaje no soportado"})

    async def notify_alert(self, event):
        """Envía notificación al cliente"""
        try:
            await self.send_json(event["message"])
            logger.info(f"Notificación enviada: {event['message']}")
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")

    @database_sync_to_async
    def _get_user_stations(self):
        """Obtiene las estaciones asociadas al usuario"""
        return list(self.user.roles_estaciones.filter(activo=True).values_list("estacion_id", flat=True))

    async def _handle_tank_reading(self, content):
        """Maneja las lecturas de tanque y verifica umbrales"""
        tank_id = content.get("tank_id")
        nivel = content.get("nivel")

        if tank_id is None or nivel is None:
            logger.error("Lectura de tanque sin datos necesarios")
            return

        # Verificar umbrales y generar/resolver alertas si es necesario
        alerts = await self._check_thresholds(tank_id, nivel)
        if alerts:
            for alert in alerts:
                notification_service = AlertaNotificationService()
                await database_sync_to_async(notification_service.send_notifications)(alert)

    @database_sync_to_async
    def _check_thresholds(self, tank_id, nivel):
        """
        Verifica los umbrales y genera/resuelve alertas según corresponda.
        """
        try:
            umbrales = ConfiguracionUmbrales.objects.filter(tanque_id=tank_id, activo=True).select_related("tanque")
            alertas_generadas = []

            for umbral in umbrales:
                alerta_existente = Alerta.objects.filter(
                    tanque_id=tank_id,
                    configuracion_umbral=umbral,
                    estado__in=["ACTIVA", "NOTIFICADA"]
                ).first()

                # Si se excede el umbral y no hay alerta activa
                if self._should_create_alert(nivel, umbral) and not alerta_existente:
                    alerta = Alerta.objects.create(
                        tanque_id=tank_id,
                        configuracion_umbral=umbral,
                        nivel_detectado=nivel,
                        estado="ACTIVA",
                        fecha_generacion=now()
                    )
                    logger.info(f"Alerta creada: {alerta}")
                    alertas_generadas.append(alerta)

                # Resolver alertas activas si el nivel vuelve a la normalidad
                elif alerta_existente and not self._should_create_alert(nivel, umbral):
                    alerta_existente.estado = "RESUELTA"
                    alerta_existente.fecha_resolucion = now()
                    alerta_existente.save()
                    logger.info(f"Alerta resuelta: {alerta_existente}")
                    alertas_generadas.append(alerta_existente)

            return alertas_generadas
        except Exception as e:
            logger.error(f"Error verificando umbrales: {e}")
            return []

    def _should_create_alert(self, nivel, umbral):
        """Determina si se debe crear una alerta basada en el umbral"""
        if umbral.tipo in ["CRITICO", "BAJO"]:
            return nivel <= umbral.valor
        elif umbral.tipo in ["ALTO", "LIMITE"]:
            return nivel >= umbral.valor
        return False
