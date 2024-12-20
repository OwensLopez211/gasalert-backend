from websocket_server import WebsocketServer
import json
import time
import threading
import redis

# Configuración de Redis
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

# Diccionario para almacenar los estados de los tanques
tanques = {
    4: {"capacidad": 25000.0, "volumen": 25000.0, "tasa_de_venta": 2.5},  # Tanque id 4
    2: {"capacidad": 15000.0, "volumen": 15000.0, "tasa_de_venta": 1.5},  # Tanque id 2
    3: {"capacidad": 10000.0, "volumen": 10000.0, "tasa_de_venta": 1.4},  # Tanque id 3
    5: {"capacidad": 12, "volumen": 12, "tasa_de_venta": 0.1},         # Tanque id 5
}

# Lista para rastrear clientes conectados
clientes = []

# Función para calcular el nivel en porcentaje basado en la capacidad total
def calcular_nivel(volumen, capacidad):
    if capacidad <= 0:
        return 0  # Evitar divisiones por 0
    return (volumen / capacidad) * 100

# Función que actualiza los datos de los tanques continuamente
def actualizar_estado_tanques():
    while True:
        for tank_id, estado in tanques.items():
            # Disminuir el volumen basado en la tasa de venta
            if estado["volumen"] > 0:
                estado["volumen"] = max(0, estado["volumen"] - estado["tasa_de_venta"])
                if estado["volumen"] == 0:
                    print(f"Tanque {tank_id} está vacío")  # Notificación de tanque vacío
        time.sleep(1)  # Simula el paso del tiempo en segundos

# Función que envía los datos de los tanques a los clientes conectados
def enviar_datos_a_todos():
    while True:
        for tank_id, estado in tanques.items():
            # Calcular el nivel basado en el volumen actual y la capacidad total
            nivel = calcular_nivel(estado["volumen"], estado["capacidad"])

            # Crear datos simulados
            mock_data = {
                "tank_id": tank_id,
                "ultima_lectura": {
                    "nivel": round(nivel, 2),  # Nivel en porcentaje
                    "volumen": round(estado["volumen"], 2),  # Volumen en litros
                    "fecha": time.strftime('%Y-%m-%dT%H:%M:%S'),  # Fecha en formato ISO
                }
            }

            # Almacenar los datos en Redis en `lecturas_brutas`
            try:
                redis_client.rpush("lecturas_brutas", json.dumps(mock_data))
                redis_client.ltrim("lecturas_brutas", -100, -1)  # Mantener solo las últimas 100 lecturas
                print(f"Dato almacenado en Redis para tanque {tank_id}: {mock_data}")  # Log de confirmación
            except Exception as e:
                print(f"Error al almacenar en Redis para tanque {tank_id}: {e}")

            # Enviar datos simulados a los clientes conectados
            for client in clientes[:]:
                try:
                    server.send_message(client, json.dumps(mock_data))
                except Exception as e:
                    print(f"Error al enviar datos al cliente {client['id']}: {e}")
                    clientes.remove(client)  # Eliminar cliente desconectado

        time.sleep(5)  # Enviar datos cada 5 segundos a los clientes conectados

# Función para manejar nuevas conexiones
def new_client(client, server):
    print(f"Nuevo cliente conectado: {client['id']}")
    clientes.append(client)  # Agregar cliente a la lista

# Función para manejar desconexiones de clientes
def client_left(client, server):
    print(f"Cliente desconectado: {client['id']}")
    clientes.remove(client)

# Crear el servidor WebSocket
server = WebsocketServer(host="127.0.0.1", port=8001)
server.set_fn_new_client(new_client)
server.set_fn_client_left(client_left)

# Hilo que actualiza continuamente el estado de los tanques
threading.Thread(target=actualizar_estado_tanques, daemon=True).start()

# Hilo único para enviar datos a todos los clientes conectados
threading.Thread(target=enviar_datos_a_todos, daemon=True).start()

print("Servidor WebSocket en ejecución en ws://127.0.0.1:8001")
server.run_forever()
