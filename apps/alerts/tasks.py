from celery import shared_task
import json
from django.utils.timezone import now
from .models import Alerta, Notificacion
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from apps.tanks.models import Tanque
from apps.alerts.models import ConfiguracionUmbrales
from django.core.mail import send_mail
from django.conf import settings

# Configuración de Redis
import redis
redis_client = redis.StrictRedis(host="127.0.0.1", port=6379, db=0)

@shared_task
def procesar_lecturas_redis():
    """
    Procesa las lecturas almacenadas en Redis inmediatamente.
    """
    lecturas = redis_client.lrange("lecturas_brutas", 0, -1)
    if not lecturas:
        return

    for lectura_raw in lecturas:
        try:
            lectura = json.loads(lectura_raw)
            tank_id = lectura.get("tank_id")
            nivel = lectura.get("nivel")

            # Validación rápida de datos básicos
            if not tank_id or nivel is None or not isinstance(nivel, (int, float)) or nivel < 0 or nivel > 100:
                continue

            # Obtener y procesar umbrales inmediatamente
            umbrales = ConfiguracionUmbrales.objects.filter(
                tanque_id=tank_id,
                activo=True
            ).select_related('tanque').values("tipo", "valor", "id")

            if umbrales:
                generar_alertas_y_notificaciones(tank_id, nivel, {u["tipo"]: u for u in umbrales})

        except Exception as e:
            print(f"Error procesando lectura: {lectura_raw}. Error: {e}")
        finally:
            redis_client.lpush("lecturas_procesadas", lectura_raw)
            redis_client.lrem("lecturas_brutas", 0, lectura_raw)
@shared_task
def generar_alertas_y_notificaciones(tank_id, nivel, umbrales):
    """
    Genera alertas y notificaciones tanto para bajadas como subidas de nivel.
    """
    try:
        alertas_generadas = []
        nivel = float(nivel)

        # Obtener alertas activas
        alertas_activas = Alerta.objects.filter(
            tanque_id=tank_id,
            estado__in=['ACTIVA', 'NOTIFICADA']
        ).select_related('configuracion_umbral')

        for alerta in alertas_activas:
            tipo_umbral = alerta.configuracion_umbral.tipo
            valor_umbral = float(alerta.configuracion_umbral.valor)

            # Verificar si el nivel cruzó el umbral en la dirección opuesta
            if ((tipo_umbral in ["CRITICO", "BAJO"] and nivel > valor_umbral) or 
                (tipo_umbral in ["ALTO", "LIMITE"] and nivel < valor_umbral)):
                
                print(f"Nivel {nivel} cruzó umbral {valor_umbral} - Resolviendo alerta {tipo_umbral}")
                
                # Resolver la alerta actual
                alerta.estado = 'RESUELTA'
                alerta.fecha_resolucion = now()
                alerta.save()
                print(f"Alerta {alerta.id} resuelta.")

        # Verificar nuevas violaciones de umbral
        for tipo, umbral in umbrales.items():
            valor_umbral = float(umbral["valor"])
            
            # Verificar si ya existe una alerta activa para este tipo
            alerta_activa = Alerta.objects.filter(
                tanque_id=tank_id,
                configuracion_umbral__tipo=tipo,
                estado__in=['ACTIVA', 'NOTIFICADA']
            ).exists()

            if not alerta_activa:
                if (tipo in ["CRITICO", "BAJO"] and nivel <= valor_umbral) or \
                   (tipo in ["ALTO", "LIMITE"] and nivel >= valor_umbral):
                    alerta = guardar_alerta(tank_id, tipo, nivel, valor_umbral)
                    if alerta:
                        alertas_generadas.append(alerta)
                        print(f"Nueva alerta generada por cruce de umbral: Tipo {tipo}, Nivel {nivel}")

        # Enviar notificaciones para todas las alertas generadas
        if alertas_generadas:
            enviar_notificaciones_y_websocket(alertas_generadas)
            print(f"Se generaron y notificaron {len(alertas_generadas)} alertas")

        return alertas_generadas

    except Exception as e:
        print(f"Error en generar_alertas_y_notificaciones: {e}")
        import traceback
        print(traceback.format_exc())
        return []

@shared_task
def guardar_alerta(tank_id, tipo, nivel, valor):
    """
    Crea una nueva alerta en la base de datos.
    """
    try:
        tanque = Tanque.objects.get(id=tank_id)
        umbral = ConfiguracionUmbrales.objects.get(
            tanque_id=tank_id, 
            tipo=tipo,
            activo=True
        )

        # Verificar la última alerta para este umbral
        ultima_alerta = Alerta.objects.filter(
            tanque=tanque,
            configuracion_umbral__tipo=tipo
        ).order_by('-fecha_generacion').first()

        # Solo crear nueva alerta si no hay última alerta o la última está resuelta
        if not ultima_alerta or ultima_alerta.estado == 'RESUELTA':
            alerta = Alerta.objects.create(
                tanque=tanque,
                configuracion_umbral=umbral,
                nivel_detectado=nivel,
                estado="ACTIVA",
                fecha_generacion=now(),
            )
            print(f"✅ Alerta creada: {alerta}")
            return alerta
        
        return None

    except Tanque.DoesNotExist:
        print(f"Error: Tanque con ID {tank_id} no encontrado")
    except ConfiguracionUmbrales.DoesNotExist:
        print(f"Error: Configuración de umbral para tanque {tank_id} y tipo {tipo} no encontrada")
    except Exception as e:
        print(f"Error al guardar alerta: {e}")
    return None
@shared_task
def enviar_notificaciones_y_websocket(alertas):
    """
    Envía notificaciones a los usuarios y envía alertas en tiempo real al WebSocket.
    """
    try:
        for alerta in alertas:
            tanque = alerta.tanque
            usuarios = get_user_model().objects.filter(
                roles_estaciones__estacion=tanque.estacion,
                roles_estaciones__activo=True
            ).distinct()

            # Crear notificaciones en bulk
            notificaciones = [
                Notificacion(
                    alerta=alerta,
                    tipo="PLATFORM",
                    destinatario=usuario,
                    estado="PENDIENTE",
                    fecha_envio=now(),
                )
                for usuario in usuarios
            ]
            notificaciones_creadas = Notificacion.objects.bulk_create(notificaciones)

            # Enviar correo electrónico a cada usuario
            for usuario in usuarios:
                subject = f"Nueva alerta: {alerta.configuracion_umbral.tipo} en {tanque.nombre}"
                message = f"Se ha generado una nueva alerta:\n\n" \
                          f"Tanque: {tanque.nombre}\n" \
                          f"Tipo de alerta: {alerta.configuracion_umbral.tipo}\n" \
                          f"Nivel detectado: {alerta.nivel_detectado}%\n" \
                          f"Fecha: {alerta.fecha_generacion.strftime('%Y-%m-%d %H:%M:%S')}"
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient_list = [usuario.email]
                send_mail(subject, message, from_email, recipient_list)

            # Tomar la primera notificación para el mensaje WebSocket
            if notificaciones_creadas:
                primera_notificacion = notificaciones_creadas[0]
                mensaje_ws = {
                    "id": primera_notificacion.id,
                    "mensaje": f"Alerta: {alerta.configuracion_umbral.tipo} en {tanque.nombre}",
                    "fecha_envio": primera_notificacion.fecha_envio.isoformat(),
                    "fecha_lectura": None,
                    "alerta_id": alerta.id,
                    "nivel_detectado": alerta.nivel_detectado,
                    "umbral": alerta.configuracion_umbral.valor,
                    "tipo": alerta.configuracion_umbral.tipo,
                    "notificacion_id": primera_notificacion.id  # Agregar explícitamente
                }

                # Enviar una sola vez por alerta al WebSocket
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"station_{tanque.estacion.id}",
                        {
                            "type": "notify_alert",
                            "message": mensaje_ws
                        },
                    )
                print(f"Notificación enviada con ID: {primera_notificacion.id}")

    except Exception as e:
        print(f"Error al enviar notificaciones o WebSocket: {e}")
        import traceback
        print(traceback.format_exc())