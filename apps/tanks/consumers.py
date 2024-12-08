import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from datetime import datetime

class TankStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Unirse al grupo común de actualizaciones
        await self.channel_layer.group_add("tank_updates", self.channel_name)
        print("Cliente WebSocket conectado")

    async def disconnect(self, close_code):
        # Salir del grupo común
        await self.channel_layer.group_discard("tank_updates", self.channel_name)
        print("Cliente WebSocket desconectado")

    async def tank_update(self, event):
        # Enviar los datos al cliente
        print(f"Enviando actualización: {event['data']}")
        await self.send(text_data=json.dumps(event['data']))