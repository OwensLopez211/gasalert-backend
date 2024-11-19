from channels.testing import WebsocketCommunicator
from django.test import TestCase
from core.asgi import application  # Adjust the import to match your ASGI config

class WebSocketTests(TestCase):
    async def test_tank_updates(self):
        communicator = WebsocketCommunicator(application, "/ws/tank_status/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send a simulated tank update message
        await communicator.send_json_to({
            "tank_name": "Tank 1",
            "ultima_lectura": {
                "volumen": 6000,
                "nivel": 70,
                "fecha": "2024-11-14T14:00:00"
            }
        })

        # Receive the message and check if it matches the expected output
        response = await communicator.receive_json_from()
        self.assertEqual(response, {
            "tank_name": "Tank 1",
            "ultima_lectura": {
                "volumen": 6000,
                "nivel": 70,
                "fecha": "2024-11-14T14:00:00"
            }
        })

        await communicator.disconnect()
