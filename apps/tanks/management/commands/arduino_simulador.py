import requests
import time
import random
import json
from datetime import datetime

class ArduinoSimulator:
    def __init__(self, server_url="http://localhost:8000/api/tanks/sensor-reading/"):
        self.server_url = server_url
        self.headers = {
            "Content-Type": "application/json"
        }
        self.tank_capacity = 12  # Capacidad total del tanque en litros

    def generate_reading(self, tank_id, current_volume):
        """Genera una lectura basada en el volumen actual"""
        # Calcular el nivel como porcentaje del volumen actual sobre la capacidad total
        nivel = (current_volume / self.tank_capacity) * 100

        # Temperatura simulada entre 20 y 30 grados
        temperatura = random.uniform(20, 30)

        return {
            "tank_id": tank_id,
            "reading": {
                "nivel": round(nivel, 2),
                "volumen": round(current_volume, 2),
                "temperatura": round(temperatura, 2)
            }
        }

    def send_reading(self, reading_data):
        """Envía la lectura al servidor"""
        try:
            response = requests.post(
                self.server_url,
                headers=self.headers,
                json=reading_data
            )
            print(f"[{datetime.now()}] Enviando datos: {json.dumps(reading_data)}")
            
            if response.status_code == 201:
                print(f"✅ Datos enviados correctamente: {response.json()}")
                return True
            else:
                print(f"❌ Error enviando datos. Status: {response.status_code}")
                print(f"Respuesta: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error de conexión: {e}")
            return False

    def start_simulation(self, tank_id=5, initial_volume=12, step=0.5, interval=5, duration=None):
        """
        Inicia la simulación con valores decrecientes y luego crecientes en un ciclo.

        tank_id: ID del tanque a simular.
        initial_volume: Volumen inicial en litros.
        step: Cantidad a incrementar o decrementar en cada iteración (litros).
        interval: Segundos entre lecturas.
        duration: Duración total en segundos (None para ejecutar indefinidamente).
        """
        current_volume = initial_volume
        direction = "decreasing"  # Direcciones: "decreasing" o "increasing"
        start_time = time.time()
        iteration = 0
        
        print(f"🚀 Iniciando simulación para el tanque ID {tank_id}")
        print(f"📊 Capacidad total del tanque: {self.tank_capacity} litros")
        print(f"📉 Volumen inicial: {initial_volume} litros, paso: {step} litros por iteración")
        print(f"⏱️  Intervalo: {interval} segundos")
        print(f"⏱️  Duración: {'Indefinida' if duration is None else f'{duration} segundos'}")
        
        try:
            while True:
                reading = self.generate_reading(tank_id, current_volume)
                self.send_reading(reading)

                # Cambiar dirección cuando llegue al límite
                if direction == "decreasing":
                    current_volume = max(0, current_volume - step)
                    if current_volume == 0:
                        direction = "increasing"
                        print("🔄 Cambiando a modo creciente (increasing)")
                elif direction == "increasing":
                    current_volume = min(self.tank_capacity, current_volume + step)
                    if current_volume == self.tank_capacity:
                        direction = "decreasing"
                        print("🔄 Cambiando a modo decreciente (decreasing)")

                iteration += 1
                print(f"\n--- Iteración {iteration} completada ---\n")
                
                if duration and (time.time() - start_time) >= duration:
                    print(f"✨ Simulación completada después de {iteration} iteraciones")
                    break
                    
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n⚡ Simulación detenida por el usuario")

if __name__ == "__main__":
    # Ejemplo de uso
    simulator = ArduinoSimulator()
    
    # Simular el tanque 5 con 12 litros, alternando entre decreciente y creciente
    simulator.start_simulation(
        tank_id=5,  # ID del tanque
        initial_volume=12,  # Volumen inicial en litros
        step=0.5,  # Paso por iteración en litros
        interval=5,  # Intervalo de envío en segundos
        duration=None  # Ejecutar indefinidamente (o ajusta la duración en segundos)
    )
