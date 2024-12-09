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
        lecturas = redis_client.lrange("lecturas_procesadas", 0, -1)
        if not lecturas:
            print("No hay lecturas en Redis para procesar.")
            return

        tanques_data = {}

        # Procesar cada lectura
        for lectura_json in lecturas:
            try:
                lectura = json.loads(lectura_json)
                tanque_id = lectura.get("tank_id")
                nivel = lectura.get("nivel")
                volumen = lectura.get("volumen")
                temperatura = lectura.get("temperatura")
                fecha = lectura.get("fecha")

                # Validar datos
                if None in [tanque_id, nivel, volumen, fecha]:
                    print(f"❌ Lectura inválida: {lectura_json}")
                    continue

                # Agrupar datos por tanque
                if tanque_id not in tanques_data:
                    tanques_data[tanque_id] = {"niveles": [], "volumenes": [], "temperaturas": []}

                tanques_data[tanque_id]["niveles"].append(nivel)
                tanques_data[tanque_id]["volumenes"].append(volumen)
                tanques_data[tanque_id]["temperaturas"].append(temperatura)

                # Guardar la lectura individual en la base de datos
                Lectura.objects.create(
                    tanque_id=tanque_id,
                    nivel=nivel,
                    volumen=volumen,
                    temperatura=temperatura,
                    fecha=fecha,
                )
                print(f"✅ Lectura guardada: {lectura}")

            except json.JSONDecodeError as e:
                print(f"❌ Error decodificando JSON: {lectura_json} - Error: {e}")

        # Calcular promedios y almacenar
        for tanque_id, datos in tanques_data.items():
            if datos["niveles"] and datos["volumenes"]:
                nivel_promedio = sum(datos["niveles"]) / len(datos["niveles"])
                volumen_promedio = sum(datos["volumenes"]) / len(datos["volumenes"])
                temperatura_promedio = (
                    sum(datos["temperaturas"]) / len(datos["temperaturas"])
                    if datos["temperaturas"]
                    else None
                )

                Lectura.objects.create(
                    tanque_id=tanque_id,
                    fecha=datetime.now(),
                    nivel=nivel_promedio,
                    volumen=volumen_promedio,
                    temperatura=temperatura_promedio,
                )
                print(
                    f"✅ Promedios guardados para tanque {tanque_id}: "
                    f"Nivel={nivel_promedio}, Volumen={volumen_promedio}, Temperatura={temperatura_promedio}"
                )
            else:
                print(f"❌ No hay suficientes datos válidos para calcular promedios del tanque {tanque_id}")

    finally:
        # Limpiar las lecturas brutas procesadas
        redis_client.delete("lecturas_procesadas")
        lock.release()
