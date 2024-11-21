from celery import shared_task
import json
from django.utils.timezone import now
from .models import Alerta, Notificacion
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from apps.tanks.models import Tanque
from apps.alerts.models import ConfiguracionUmbrales

# Configuración de Redis (si aún no la tienes configurada)
import redis
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

@shared_task
def procesar_lecturas_redis():
    """
    Procesa las lecturas almacenadas en Redis, compara con los umbrales
    configurados y genera alertas si es necesario.
    También resuelve alertas activas si los niveles vuelven a la normalidad.
    """
    lecturas = redis_client.lrange("lecturas_brutas", 0, -1)  # Leer lecturas brutas
    if not lecturas:
        print("No hay lecturas en Redis")
        return

    for lectura_raw in lecturas:
        try:
            lectura = json.loads(lectura_raw)
            tank_id = lectura.get("tank_id")
            nivel = lectura.get("ultima_lectura", {}).get("nivel")

            # Validar datos básicos
            if not tank_id or nivel is None:
                print(f"Lectura inválida: {lectura_raw}")
                continue

            if not isinstance(nivel, (int, float)) or nivel < 0 or nivel > 100:
                print(f"Nivel inválido detectado para tanque {tank_id}: {nivel}")
                continue

            # Procesar umbrales
            umbrales = obtener_umbrales_para_tanque(tank_id)
            if not umbrales:
                print(f"No se encontraron umbrales para el tanque {tank_id}")
                continue

            # Generar nuevas alertas si es necesario
            alertas = verificar_violaciones_de_umbrales(tank_id, nivel, umbrales)
            for alerta in alertas:
                print(f"Alerta generada: Tanque {alerta['tank_id']}, Tipo: {alerta['tipo']}, Nivel detectado: {alerta['nivel']}, Umbral: {alerta['valor']}")
                guardar_y_enviar_alerta(alerta)

            # Resolver alertas activas si los niveles vuelven a la normalidad
            resolver_alertas_activas(tank_id, nivel, umbrales)

        except json.JSONDecodeError:
            print(f"Error decodificando JSON: {lectura_raw}")
        except Exception as e:
            print(f"Error procesando lectura: {lectura_raw}. Error: {e}")
        finally:
            # Elimina la lectura de Redis después de procesarla
            redis_client.lrem("lecturas_brutas", 0, lectura_raw)


def resolver_alertas_activas(tank_id, nivel, umbrales):
    """
    Marca alertas activas como resueltas si el nivel actual ya no viola los umbrales.
    """
    from .models import Alerta

    alertas_activas = Alerta.objects.filter(
        tanque_id=tank_id,
        estado="ACTIVA"
    ).select_related('configuracion_umbral')

    for alerta in alertas_activas:
        tipo = alerta.configuracion_umbral.tipo
        umbral = umbrales.get(tipo)

        if not umbral:
            continue

        # Condiciones para resolver alertas
        if (tipo in ["CRITICO", "BAJO"] and nivel > umbral) or \
           (tipo in ["ALTO", "LIMITE"] and nivel < umbral) or \
           (tipo == "MEDIO" and nivel >= umbral):
            alerta.estado = "RESUELTA"
            alerta.fecha_resolucion = now()
            alerta.save()
            print(f"Alerta resuelta automáticamente: {alerta.id} para tanque {tank_id}")


def obtener_umbrales_para_tanque(tank_id):
    """
    Obtiene los umbrales activos desde la base de datos para un tanque específico.
    """
    from .models import ConfiguracionUmbrales
    umbrales = ConfiguracionUmbrales.objects.filter(
        tanque_id=tank_id, activo=True
    ).values("tipo", "valor")
    return {u["tipo"]: u["valor"] for u in umbrales}

def verificar_violaciones_de_umbrales(tank_id, nivel, umbrales):
    alertas = []
    
    for tipo, valor in umbrales.items():
        # Verifica si existe una alerta activa para este umbral y tanque
        alerta_activa_existe = Alerta.objects.filter(
            tanque_id=tank_id,
            configuracion_umbral__tipo=tipo,
            estado="ACTIVA"
        ).exists()

        # Si no hay alerta activa, evaluar condiciones para generar una nueva alerta
        if not alerta_activa_existe:
            if tipo == "CRITICO" and nivel <= valor:
                # Generar alerta si el nivel está por debajo o igual al umbral CRITICO
                alertas.append({"tank_id": tank_id, "tipo": tipo, "valor": valor, "nivel": nivel})
            elif tipo == "BAJO" and nivel <= valor:
                # Generar alerta si el nivel está por debajo o igual al umbral BAJO
                alertas.append({"tank_id": tank_id, "tipo": tipo, "valor": valor, "nivel": nivel})
            elif tipo == "MEDIO" and nivel < valor:
                # Generar alerta si el nivel está estrictamente por debajo del umbral MEDIO
                alertas.append({"tank_id": tank_id, "tipo": tipo, "valor": valor, "nivel": nivel})
            elif tipo == "ALTO" and nivel >= valor:
                # Generar alerta si el nivel está por encima o igual al umbral ALTO
                alertas.append({"tank_id": tank_id, "tipo": tipo, "valor": valor, "nivel": nivel})
            elif tipo == "LIMITE" and nivel >= valor:
                # Generar alerta si el nivel está por encima o igual al umbral LIMITE
                alertas.append({"tank_id": tank_id, "tipo": tipo, "valor": valor, "nivel": nivel})
    
    return alertas


def guardar_y_enviar_alerta(alerta):
    try:
        # Validar campos requeridos en la alerta
        required_fields = ["tank_id", "tipo", "nivel"]
        for field in required_fields:
            if field not in alerta:
                print(f"Falta el campo requerido '{field}' en la alerta.")
                return

        # Obtener tanque y configuración de umbral
        tanque = Tanque.objects.get(id=alerta["tank_id"])
        umbral = ConfiguracionUmbrales.objects.get(
            tanque_id=alerta["tank_id"],
            tipo=alerta["tipo"]
        )

        # Crear la alerta
        alerta_obj = Alerta.objects.create(
            tanque=tanque,
            configuracion_umbral=umbral,
            nivel_detectado=alerta["nivel"],
            estado="ACTIVA",
            fecha_generacion=now()
        )
        print(f"Alerta creada: {alerta_obj}")

        # Obtener usuarios relacionados con la estación del tanque
        User = get_user_model()
        usuarios = User.objects.filter(
            roles_estaciones__estacion=tanque.estacion,
            roles_estaciones__activo=True
        ).distinct()

        if not usuarios.exists():
            print(f"No hay usuarios asociados a la estación {tanque.estacion.id}.")
        else:
            # Crear notificaciones para los usuarios
            for usuario in usuarios:
                Notificacion.objects.create(
                    alerta=alerta_obj,
                    tipo="PLATFORM",
                    destinatario=usuario,
                    estado="PENDIENTE"
                )
            print(f"Notificaciones creadas para {len(usuarios)} usuarios en la estación {tanque.estacion.id}.")

        # Enviar notificación en tiempo real al WebSocket
        channel_layer = get_channel_layer()
        if channel_layer is not None:
            async_to_sync(channel_layer.group_send)(
                f"station_{tanque.estacion.id}",
                {
                    "type": "notify_alert",
                    "message": {
                        "id": alerta_obj.id,
                        "tanque_id": tanque.id,
                        "tipo": alerta["tipo"],
                        "nivel_detectado": alerta["nivel"],
                        "umbral": alerta["valor"],
                        "fecha_generacion": alerta_obj.fecha_generacion.isoformat(),
                    },
                },
            )
            print(f"Notificación enviada al WebSocket para estación {tanque.estacion.id}.")
        else:
            print("Error: No se pudo obtener el channel_layer para enviar notificación.")

    except Tanque.DoesNotExist:
        print(f"Error: Tanque con ID {alerta['tank_id']} no encontrado.")
    except ConfiguracionUmbrales.DoesNotExist:
        print(f"Error: Configuración de umbral para tanque {alerta['tank_id']} y tipo {alerta['tipo']} no encontrada.")
    except Exception as e:
        print(f"Error al guardar o enviar alerta: {e}")
