import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class TankStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("Cliente WebSocket conectado.")  # Log de conexión

    async def disconnect(self, close_code):
        print("Cliente WebSocket desconectado.")  # Log de desconexión

    async def receive(self, text_data):
        """
        Procesa los mensajes recibidos del WebSocket.
        """
        try:
            data = json.loads(text_data)
            print(f"Mensaje recibido del WebSocket: {data}")  # Log de recepción

            # Extrae los datos enviados por el cliente
            tanque_id = data.get("tanque_id")
            nivel = data.get("nivel")
            volumen = data.get("volumen")
            temperatura = data.get("temperatura", None)  # Opcional
            fecha = datetime.now().isoformat()

            # Publica los datos en Redis
            redis_client = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
            redis_client.rpush("lecturas_tanques", json.dumps({
                "tanque_id": tanque_id,
                "nivel": nivel,
                "volumen": volumen,
                "temperatura": temperatura,
                "fecha": fecha
            }))
            print(f"Dato almacenado en Redis: {data}")  # Log de almacenamiento

            # Envía los datos de vuelta al frontend
            await self.send(text_data=json.dumps({
                "tanque_id": tanque_id,
                "nivel": nivel,
                "volumen": volumen,
                "temperatura": temperatura,
                "fecha": fecha
            }))
        except Exception as e:
            print(f"Error en WebSocket: {e}")  # Log de error
