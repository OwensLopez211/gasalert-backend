from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from .models import ConfiguracionUmbrales, Alerta
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class AlertaConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        """
        Establece la conexión del WebSocket y autentica al usuario.
        """
        print("Intento de conexión a AlertaConsumer")

        try:
            self.user = await self._authenticate_user()
        except Exception as e:
            print(f"Error durante la autenticación: {e}")
            self.user = None

        if not self.user or self.user.is_anonymous:
            print("Usuario no autenticado - cerrando conexión")
            await self.close()
            logger.warning("Intento de conexión no autenticado")
            return

        estaciones = await self._get_user_stations()
        if not estaciones:
            print("Usuario no tiene estaciones asociadas")
            await self.close()
            return

        for estacion_id in estaciones:
            await self.channel_layer.group_add(f"station_{estacion_id}", self.channel_name)
        await self.accept()
        print(f"Conexión aceptada para usuario {self.user.id}")
        logger.info(f"Usuario {self.user.id} conectado al WebSocket")

    async def disconnect(self, close_code):
        """
        Maneja la desconexión del WebSocket.
        """
        if self.user and not self.user.is_anonymous:
            estaciones = await self._get_user_stations()
            for estacion_id in estaciones:
                await self.channel_layer.group_discard(f"station_{estacion_id}", self.channel_name)
            print(f"Desconexión de usuario {self.user.id}")
            logger.info(f"Usuario {self.user.id} desconectado del WebSocket")

    async def receive_json(self, content):
        """
        Procesa los mensajes recibidos del cliente.
        """
        print(f"Mensaje recibido: {content}")
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
        """Envía notificación al cliente."""
        try:
            message = event["message"]
            print(f"Enviando notificación al cliente: {message}")  # Debug log
            await self.send_json(message)
        except Exception as e:
            print(f"Error enviando notificación: {e}")

    @database_sync_to_async
    def _authenticate_user(self):
        """
        Autentica al usuario usando el token JWT enviado en la query string.
        """
        token_key = self.scope.get("query_string", b"").decode().split("token=")[-1]
        if token_key:
            try:
                # Verificar el token JWT
                UntypedToken(token_key)
                payload = UntypedToken(token_key).payload
                user_id = payload.get("user_id")
                return User.objects.get(id=user_id)
            except (InvalidToken, TokenError, User.DoesNotExist) as e:
                logger.warning(f"Token inválido o usuario no encontrado: {e}")
                return AnonymousUser()

        return self.scope.get("user", AnonymousUser())

    @database_sync_to_async
    def _get_user_stations(self):
        """
        Obtiene las estaciones asociadas al usuario.
        """
        return list(self.user.roles_estaciones.filter(activo=True).values_list("estacion_id", flat=True))

    async def _handle_tank_reading(self, content):
        """
        Maneja las lecturas de tanque.
        """
        tank_id = content.get("tank_id")
        nivel = content.get("nivel")

        if not tank_id or nivel is None:
            logger.error("Lectura de tanque sin datos necesarios")
            return

        # Lógica para manejar lecturas de tanque
        print(f"Leyendo datos de tanque {tank_id} con nivel {nivel}")

    @database_sync_to_async
    def _check_thresholds(self, tank_id, nivel):
        """
        Verifica los umbrales y genera alertas si es necesario.
        """
        try:
            umbrales = ConfiguracionUmbrales.objects.filter(tanque_id=tank_id, activo=True).select_related("tanque")
            alertas_generadas = []

            for umbral in umbrales:
                if self._should_create_alert(nivel, umbral):
                    alerta = Alerta.objects.create(
                        tanque_id=tank_id,
                        configuracion_umbral=umbral,
                        nivel_detectado=nivel,
                        estado="ACTIVA",
                        fecha_generacion=now()
                    )
                    logger.info(f"Alerta creada: {alerta}")
                    alertas_generadas.append(alerta)

            return alertas_generadas
        except Exception as e:
            logger.error(f"Error verificando umbrales: {e}")
            return []

    def _should_create_alert(self, nivel, umbral):
        """
        Determina si se debe crear una alerta basada en el umbral.
        """
        if umbral.tipo in ["CRITICO", "BAJO"]:
            return nivel <= umbral.valor
        elif umbral.tipo == "LIMITE":
            return nivel >= umbral.valor
        return False
