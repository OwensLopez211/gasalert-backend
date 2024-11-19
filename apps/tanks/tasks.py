from celery import shared_task
from datetime import datetime
import redis
import json
from apps.tanks.models import Lectura  # Asegúrate de importar tu modelo correctamente

# Configura Redis
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

@shared_task
def calcular_promedios():
    # Recupera las lecturas almacenadas en Redis
    lecturas = redis_client.lrange("lecturas_tanques", 0, -1)

    # Si no hay lecturas, finaliza la tarea
    if not lecturas:
        print("No hay lecturas en Redis")
        return

    print("Lecturas obtenidas de Redis:", lecturas)

    tanques_data = {}

    # Procesa cada lectura
    for lectura_json in lecturas:
        lectura = json.loads(lectura_json)
        if "tank_id" not in lectura:
            print(f"Error: Falta la clave 'tank_id' en la lectura: {lectura}")
            continue

        tanque_id = lectura["tank_id"]

        if tanque_id not in tanques_data:
            tanques_data[tanque_id] = {
                "niveles": [],
                "volumenes": []
            }

        tanques_data[tanque_id]["niveles"].append(lectura["ultima_lectura"]["nivel"])
        tanques_data[tanque_id]["volumenes"].append(lectura["ultima_lectura"]["volumen"])

    # Calcula los promedios y guarda en la base de datos
    for tanque_id, datos in tanques_data.items():
        nivel_promedio = sum(datos["niveles"]) / len(datos["niveles"])
        volumen_promedio = sum(datos["volumenes"]) / len(datos["volumenes"])

        print(f"Tanque {tanque_id}: Nivel promedio: {nivel_promedio}, Volumen promedio: {volumen_promedio}")

        # Guarda en la base de datos
        try:
            Lectura.objects.create(
                tanque_id=tanque_id,
                fecha=datetime.now(),  # Fecha actual
                nivel=nivel_promedio,
                volumen=volumen_promedio
            )
            print(f"Datos guardados en la base de datos para el tanque {tanque_id}")
        except Exception as e:
            print(f"Error al guardar en la base de datos para el tanque {tanque_id}: {e}")

    # Limpia las lecturas en Redis
    redis_client.delete("lecturas_tanques")
    print("Redis limpiado tras calcular promedios.")
