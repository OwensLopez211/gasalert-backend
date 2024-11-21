from celery import shared_task
from datetime import datetime
import redis
import json
from apps.tanks.models import Lectura

# Configura Redis
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

@shared_task
def calcular_promedios():
    lock = redis_client.lock("calcular_promedios_lock", timeout=60)

    if not lock.acquire(blocking=False):
        print("Otra tarea ya está procesando lecturas. Saliendo.")
        return

    try:
        lecturas = redis_client.lrange("lecturas_brutas", 0, -1)
        if not lecturas:
            print("No hay lecturas en Redis")
            return

        tanques_data = {}

        # Agrupar lecturas por tanque
        for lectura_json in lecturas:
            try:
                lectura = json.loads(lectura_json)
                tanque_id = lectura.get("tank_id")
                nivel = lectura.get("ultima_lectura", {}).get("nivel")
                volumen = lectura.get("ultima_lectura", {}).get("volumen")

                if tanque_id not in tanques_data:
                    tanques_data[tanque_id] = {"niveles": [], "volumenes": []}

                tanques_data[tanque_id]["niveles"].append(nivel)
                tanques_data[tanque_id]["volumenes"].append(volumen)

            except json.JSONDecodeError:
                print(f"Error decodificando JSON: {lectura_json}")

        # Calcular promedios y almacenar
        for tanque_id, datos in tanques_data.items():
            nivel_promedio = sum(datos["niveles"]) / len(datos["niveles"])
            volumen_promedio = sum(datos["volumenes"]) / len(datos["volumenes"])

            Lectura.objects.create(
                tanque_id=tanque_id,
                fecha=datetime.now(),
                nivel=nivel_promedio,
                volumen=volumen_promedio
            )
            print(f"Promedios guardados para tanque {tanque_id}: Nivel={nivel_promedio}, Volumen={volumen_promedio}")

    finally:
        # Limpiar las lecturas brutas procesadas
        redis_client.delete("lecturas_brutas")
        lock.release()