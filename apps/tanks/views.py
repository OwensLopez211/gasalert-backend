from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from scipy import stats
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Count, Q
import numpy as np
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, TruncMonth
from .models import TipoCombustible, Tanque, Lectura
import json
from .serializers import (
    TipoCombustibleSerializer,
    TanqueSerializer,
    LecturaSerializer,
    DashboardTanqueSerializer,
    DashboardEstacionSerializer
)
import redis
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

# Initialize Redis and channel layer
r = redis.StrictRedis(host='localhost', port=6379, db=1)
channel_layer = get_channel_layer()

class TipoCombustibleViewSet(viewsets.ModelViewSet):
    queryset = TipoCombustible.objects.all()
    serializer_class = TipoCombustibleSerializer
    permission_classes = [IsAuthenticated]

class TanqueViewSet(viewsets.ModelViewSet):
    serializer_class = TanqueSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Tanque.objects.all()
        estacion_id = self.request.query_params.get('estacion_id')
        
        if estacion_id:
            queryset = queryset.filter(estacion_id=estacion_id)
        
        if not self.request.user.is_superuser:
            estaciones_permitidas = self.request.user.roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            queryset = queryset.filter(estacion_id__in=estaciones_permitidas)
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def mis_tanques(self, request):
        """
        Retorna los tanques asociados a las estaciones permitidas para el usuario.
        """
        if not request.user.is_superuser:
            estaciones_permitidas = request.user.roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            tanques = Tanque.objects.filter(estacion_id__in=estaciones_permitidas)
        else:
            tanques = Tanque.objects.all()

        serializer = TanqueSerializer(tanques, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def registrar_lectura(self, request, pk=None):
        tanque = self.get_object()
        volumen = request.data.get("volumen")
        
        if volumen is None:
            return Response({"error": "Volumen no proporcionado."}, status=status.HTTP_400_BAD_REQUEST)

        # Store volume in Redis with a timestamp key
        timestamp = datetime.now().isoformat()
        r.set(f"tank_data:{timestamp}", volumen)

        # Send the latest reading to WebSocket for real-time frontend update
        async_to_sync(channel_layer.group_send)(
            "tank_updates",
            {
                "type": "send_tank_update",
                "data": {"ultima_lectura": volumen}
            }
        )
        
        return Response({"message": "Lectura registrada en Redis y notificada al WebSocket."})

    @action(detail=True, methods=['get'])
    def lecturas(self, request, pk=None):
        tanque = self.get_object()
        dias = int(request.query_params.get('dias', 7))
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        lecturas = tanque.lecturas.filter(
            fecha__gte=fecha_inicio
        ).order_by('-fecha')
        
        serializer = LecturaSerializer(lecturas, many=True)
        return Response(serializer.data)
    
class LecturaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LecturaSerializer
    permission_classes = [IsAuthenticated]
    
    def _parse_date(self, date_str):
        """Método auxiliar para parsear fechas"""
        if not date_str:
            return None
        try:
            # Solo manejar formato ISO con Z al final
            if date_str.endswith('Z'):
                # Quitar la Z y agregar +00:00 para UTC
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str)
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return None
    
    def get_queryset(self):
        queryset = Lectura.objects.all()
        
        # Filtrar por tanques a los que tiene acceso
        if not self.request.user.is_superuser:
            estaciones_permitidas = self.request.user.roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            queryset = queryset.filter(
                tanque__estacion_id__in=estaciones_permitidas
            )
            
        # Aplicar filtros
        tanque_id = self.request.query_params.get('tanque', None)
        fecha_desde = self._parse_date(self.request.query_params.get('fecha_desde'))
        fecha_hasta = self._parse_date(self.request.query_params.get('fecha_hasta'))
        
        if tanque_id:
            queryset = queryset.filter(tanque_id=tanque_id)
            
        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)
            
        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=fecha_hasta)
            
        return queryset.order_by('-fecha')
    
class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_user_estaciones(self, user):
        """Obtener las estaciones a las que el usuario tiene acceso"""
        if user.is_superuser:
            return None  # Superusuario puede ver todas las estaciones
        return user.roles_estaciones.filter(
            activo=True
        ).values_list('estacion_id', flat=True)

    def _get_tanque(self, tanque_id, user):
        """Método auxiliar para obtener un tanque con permisos"""
        base_query = Q(id=tanque_id)
        estaciones_permitidas = self._get_user_estaciones(user)
        if estaciones_permitidas is not None:
            base_query &= Q(estacion_id__in=estaciones_permitidas)
        return get_object_or_404(Tanque, base_query)

@api_view(['POST'])
def sensor_reading(request):
    """
    Endpoint para recibir datos desde el Arduino.
    """
    try:
        # Validar datos recibidos
        tank_id = request.data.get('tank_id')
        reading = request.data.get('reading')

        if not tank_id or not reading:
            return Response({"error": "Datos incompletos"}, status=status.HTTP_400_BAD_REQUEST)

        nivel = reading.get('nivel')
        volumen = reading.get('volumen')
        temperatura = reading.get('temperatura', None)

        if nivel is None or volumen is None:
            return Response({"error": "Faltan datos clave en la lectura"}, status=status.HTTP_400_BAD_REQUEST)

        # Crear el formato de última lectura
        ultima_lectura = {
            "nivel": nivel,
            "volumen": volumen,
            "temperatura": temperatura,
            "fecha": datetime.now().isoformat()
        }

        # Almacenar en Redis
        redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
        redis_client.rpush("lecturas_brutas", json.dumps({
            "tank_id": tank_id,
            "nivel": nivel,
            "volumen": volumen,
            "temperatura": temperatura,
            "fecha": datetime.now().isoformat()
        }))

        # Notificar a los consumidores WebSocket
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "tank_updates",  # Cambiado a un grupo común
            {
                "type": "tank_update",
                "data": {
                    "tank_id": tank_id,
                    "ultima_lectura": ultima_lectura  # Formato correcto para el frontend
                }
            }
        )

        # Retornar respuesta
        return Response({"message": "Datos procesados exitosamente"}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error en sensor_reading: {str(e)}")  # Agregar logging
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TankAnalyticsViewSet(viewsets.ViewSet):
    """
    ViewSet para análisis y gráficos de datos de tanques.
    """
    permission_classes = [IsAuthenticated]

    def get_trunc_function(self, interval):
        """
        Retorna la función de truncado apropiada según el intervalo.
        """
        trunc_functions = {
            'hour': TruncHour,
            'day': TruncDay,
            'week': TruncWeek,
            'month': TruncMonth
        }
        return trunc_functions.get(interval, TruncHour)

    def get_time_range(self, range_type):
        """
        Calcula el rango de tiempo basado en el tipo especificado.
        """
        now = timezone.now()
        ranges = {
            '1h': now - timedelta(hours=1),
            '6h': now - timedelta(hours=6),
            '12h': now - timedelta(hours=12),
            '24h': now - timedelta(hours=24),
            '7d': now - timedelta(days=7),
            '30d': now - timedelta(days=30),
            '90d': now - timedelta(days=90),
        }
        return ranges.get(range_type, now - timedelta(hours=24))

    @action(detail=False, methods=['get'])
    def nivel_historico(self, request):
        """
        Obtiene datos históricos de nivel para gráficos de línea.
        
        Parámetros:
        - tanque_id: ID del tanque (requerido)
        - range: Rango de tiempo ('1h','6h','12h','24h','7d','30d','90d')
        - interval: Intervalo de agrupación ('hour','day','week','month')
        """
        try:
            # Validar parámetros
            tanque_id = request.query_params.get('tanque_id')
            if not tanque_id:
                return Response(
                    {"error": "tanque_id es requerido"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Obtener tanque
            tanque = Tanque.objects.get(id=tanque_id)
            
            # Obtener rango e intervalo
            range_type = request.query_params.get('range', '24h')
            interval = request.query_params.get('interval', 'hour')
            
            # Calcular fecha inicio
            fecha_inicio = self.get_time_range(range_type)
            
            # Obtener función de truncado
            trunc_func = self.get_trunc_function(interval)
            
            # Consultar datos
            lecturas = (Lectura.objects
                       .filter(tanque=tanque, fecha__gte=fecha_inicio)
                       .annotate(periodo=trunc_func('fecha'))
                       .values('periodo')
                       .annotate(
                           nivel_promedio=Avg('nivel'),
                           nivel_maximo=Max('nivel'),
                           nivel_minimo=Min('nivel'),
                           volumen_promedio=Avg('volumen'),
                           cantidad_lecturas=Count('id')
                       )
                       .order_by('periodo'))

            # Preparar respuesta
            data = {
                'tanque_id': tanque_id,
                'nombre_tanque': tanque.nombre,
                'tipo_combustible': tanque.tipo_combustible.tipo,
                'capacidad_total': tanque.capacidad_total,
                'rango': range_type,
                'intervalo': interval,
                'datos': [{
                    'fecha': lectura['periodo'].isoformat(),
                    'nivel_promedio': round(lectura['nivel_promedio'], 2),
                    'nivel_maximo': round(lectura['nivel_maximo'], 2),
                    'nivel_minimo': round(lectura['nivel_minimo'], 2),
                    'volumen_promedio': round(lectura['volumen_promedio'], 2),
                    'lecturas': lectura['cantidad_lecturas']
                } for lectura in lecturas]
            }

            return Response(data)

        except Tanque.DoesNotExist:
            return Response(
                {"error": "Tanque no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def comparativa_tanques(self, request):
        """
        Obtiene datos comparativos de múltiples tanques.
        
        Parámetros:
        - tank_ids: Lista de IDs de tanques separados por comas
        - range: Rango de tiempo ('24h','7d','30d')
        """
        try:
            # Obtener y validar tanques
            tank_ids = request.query_params.get('tank_ids', '').split(',')
            if not tank_ids or not all(tank_ids):
                return Response(
                    {"error": "Se requiere al menos un tank_id válido"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Obtener rango
            range_type = request.query_params.get('range', '24h')
            fecha_inicio = self.get_time_range(range_type)

            # Preparar datos para cada tanque
            datos_comparativos = []
            for tank_id in tank_ids:
                tanque = Tanque.objects.get(id=tank_id)
                
                # Obtener última lectura y promedios
                lecturas = Lectura.objects.filter(
                    tanque=tanque,
                    fecha__gte=fecha_inicio
                )
                
                ultima_lectura = lecturas.order_by('-fecha').first()
                promedios = lecturas.aggregate(
                    nivel_promedio=Avg('nivel'),
                    volumen_promedio=Avg('volumen')
                )

                datos_comparativos.append({
                    'tanque_id': tank_id,
                    'nombre': tanque.nombre,
                    'tipo_combustible': tanque.tipo_combustible.tipo,
                    'capacidad_total': tanque.capacidad_total,
                    'nivel_actual': ultima_lectura.nivel if ultima_lectura else None,
                    'volumen_actual': ultima_lectura.volumen if ultima_lectura else None,
                    'nivel_promedio': round(promedios['nivel_promedio'], 2) if promedios['nivel_promedio'] else None,
                    'volumen_promedio': round(promedios['volumen_promedio'], 2) if promedios['volumen_promedio'] else None,
                })

            return Response({
                'rango': range_type,
                'fecha_inicio': fecha_inicio.isoformat(),
                'fecha_fin': timezone.now().isoformat(),
                'tanques': datos_comparativos
            })

        except Tanque.DoesNotExist:
            return Response(
                {"error": "Uno o más tanques no encontrados"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    @action(detail=True, methods=['get'], url_path='tank_detail_analysis')
    def tank_detail_analysis(self, request, pk=None):
        """
        Retorna análisis detallado de un tanque específico.
        """
        try:
            # Obtener el tanque
            tanque = Tanque.objects.get(id=pk)

            # Obtener la última lectura del tanque
            ultima_lectura = Lectura.objects.filter(tanque=tanque).order_by('-fecha').first()
            if not ultima_lectura:
                return Response({
                    "error": "No hay lecturas disponibles para este tanque.",
                    "capacidad_total": tanque.capacidad_total,
                    "nivel_actual": None,
                    "promedio_diario": 0,
                    "dias_restantes": None,
                }, status=200)

            # Nivel actual basado en la última lectura
            nivel_actual = ultima_lectura.volumen

            # Calcular consumo diario promedio
            lecturas = Lectura.objects.filter(tanque=tanque).order_by('fecha')
            consumos = []
            for i in range(1, len(lecturas)):
                volumen_anterior = lecturas[i - 1].volumen
                volumen_actual = lecturas[i].volumen
                diferencia = volumen_anterior - volumen_actual
                if diferencia > 0.01:  # Ignorar fluctuaciones menores
                    consumos.append(diferencia)

            # Manejo de consumo cero
            consumo_total = sum(consumos)
            dias_registrados = (lecturas.last().fecha - lecturas.first().fecha).days or 1
            promedio_diario = consumo_total / dias_registrados if dias_registrados > 0 else 0

            if consumo_total == 0:
                # Nivel constante, no hay predicción
                dias_restantes = None
            else:
                # Calcular días restantes
                dias_restantes = nivel_actual / promedio_diario if promedio_diario > 0 else None

            # Respuesta
            data = {
                "capacidad_total": tanque.capacidad_total,
                "nivel_actual": nivel_actual,
                "promedio_diario": round(promedio_diario, 2),
                "dias_restantes": round(dias_restantes, 1) if dias_restantes is not None else "Nivel constante",
            }
            return Response(data)

        except Tanque.DoesNotExist:
            return Response({"error": "Tanque no encontrado"}, status=404)
        except ZeroDivisionError:
            return Response({"error": "División por cero en el cálculo del promedio"}, status=500)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en tank_detail_analysis para tanque ID {pk}: {str(e)}")
            return Response({"error": f"Error interno: {str(e)}"}, status=500)





    @action(detail=False, methods=['get'], url_path='consumo-promedio')
    def consumo_promedio(self, request):
        """
        Calcula el consumo promedio basado en diferencias significativas entre lecturas consecutivas.
        """
        try:
            tanque_id = request.query_params.get('tanque_id', 'all')
            dias = int(request.query_params.get('dias', 30))
            fecha_inicio = timezone.now() - timedelta(days=dias)

            # Filtrar lecturas por tanque y fecha
            queryset = Lectura.objects.filter(fecha__gte=fecha_inicio).order_by('fecha')
            if tanque_id != 'all':
                queryset = queryset.filter(tanque_id=tanque_id)

            # Extraer las lecturas de volumen
            lecturas = list(queryset.values('fecha', 'volumen'))

            # Calcular consumo real
            umbral = 0.01  # Ignorar fluctuaciones menores a 0.01 L
            consumos = []
            for i in range(1, len(lecturas)):
                nivel_anterior = lecturas[i - 1]['volumen']
                nivel_actual = lecturas[i]['volumen']
                diferencia = nivel_anterior - nivel_actual
                if diferencia > umbral:  # Solo diferencias significativas
                    consumos.append(diferencia)

            # Calcular totales
            total_consumo = sum(consumos)
            promedio_diario = total_consumo / dias if dias > 0 else 0

            # Respuesta
            data = {
                "tanque_id": tanque_id,
                "dias": dias,
                "promedio_consumo_diario": round(promedio_diario, 2),
                "total_consumo": round(total_consumo, 2),
                "datos_crudos": lecturas,  # Opcional: para depuración
            }
            return Response(data)

        except ValueError:
            return Response({"error": "El parámetro 'dias' debe ser un número entero"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        
    @action(detail=True, methods=['get'])
    def tendencia_consumo(self, request, pk=None):
        try:
            tanque = Tanque.objects.get(pk=pk)
            
            range_type = request.query_params.get('range', '7d')
            now = timezone.now()
            range_map = {
                '24h': now - timedelta(hours=24),
                '7d': now - timedelta(days=7),
                '30d': now - timedelta(days=30),
            }
            fecha_inicio = range_map.get(range_type, now - timedelta(days=7))

            lecturas = Lectura.objects.filter(
                tanque=tanque,
                fecha__gte=fecha_inicio
            ).order_by('fecha').only('fecha', 'volumen')

            if not lecturas.exists():
                return Response({"message": "No hay datos disponibles."}, status=200)

            tiempos, volumenes, consumos = [], [], []
            primera_fecha = lecturas.first().fecha

            for i in range(1, len(lecturas)):
                anterior = lecturas[i - 1]
                actual = lecturas[i]
                delta_tiempo = (actual.fecha - primera_fecha).total_seconds() / 3600
                tiempos.append(delta_tiempo)
                volumenes.append(actual.volumen)
                consumo = anterior.volumen - actual.volumen
                if consumo > 0:
                    consumos.append(consumo)

            if not consumos:
                return Response({
                    "tanque_id": pk,
                    "nombre_tanque": tanque.nombre,
                    "periodo_analisis": {
                        "inicio": fecha_inicio.isoformat(),
                        "fin": now.isoformat(),
                    },
                    "tendencia_general": {
                        "direccion": None,
                        "confianza": None,
                        "tasa_cambio": None,
                    },
                    "estadisticas": {
                        "consumo_promedio": 0,
                        "desviacion_estandar": 0,
                        "coeficiente_variacion": 0,
                    },
                    "patrones": {
                        "horas_mayor_consumo": [],
                        "horas_menor_consumo": [],
                    },
                    "anomalias": [],
                    "datos_tendencia": [],
                })


            slope, intercept, r_value, *_ = stats.linregress(tiempos, volumenes)
            consumo_promedio = np.mean(consumos)
            consumo_std = np.std(consumos)

            consumos_por_hora = {}
            for i, lectura in enumerate(lecturas[1:], 1):
                hora = lectura.fecha.hour
                consumo = lecturas[i-1].volumen - lectura.volumen
                if hora not in consumos_por_hora:
                    consumos_por_hora[hora] = []
                consumos_por_hora[hora].append(consumo)

            patrones_hora = {
                hora: np.mean(consumos) 
                for hora, consumos in consumos_por_hora.items()
            }

            horas_ordenadas = sorted(
                patrones_hora.items(), 
                key=lambda x: x[1], 
                reverse=True
            )

            tendencia = {
                "direccion": "AUMENTANDO" if slope > 0 else "DISMINUYENDO",
                "confianza": abs(r_value),
                "tasa_cambio": abs(slope),
            }

            umbral_anomalia = consumo_promedio + (2 * consumo_std)
            anomalias = [
                {
                    "fecha": lecturas[i].fecha.isoformat(),
                    "consumo": consumo,
                    "desviacion": (consumo - consumo_promedio) / consumo_std
                }
                for i, consumo in enumerate(consumos)
                if consumo > umbral_anomalia
            ][:50]  # Limitar anomalías a 50

            max_puntos = 500
            step = max(1, len(consumos) // max_puntos)
            datos_tendencia = [
                {
                    "fecha": lecturas[i].fecha.isoformat(),
                    "volumen": lecturas[i].volumen,
                    "consumo": consumo if consumo > 0 else 0,
                    "tendencia_calculada": intercept + slope * tiempos[i - 1]
                }
                for i, consumo in enumerate(consumos, 1)
                if i % step == 0
            ]

            response_data = {
                "tanque_id": pk,
                "nombre_tanque": tanque.nombre,
                "periodo_analisis": {
                    "inicio": fecha_inicio.isoformat(),
                    "fin": now.isoformat(),
                },
                "tendencia_general": tendencia,
                "estadisticas": {
                    "consumo_promedio": round(consumo_promedio, 2),
                    "desviacion_estandar": round(consumo_std, 2),
                    "coeficiente_variacion": round(consumo_std / consumo_promedio * 100, 2),
                },
                "patrones": {
                    "horas_mayor_consumo": [
                        {"hora": hora, "consumo_promedio": round(consumo, 2)} 
                        for hora, consumo in horas_ordenadas[:3]
                    ],
                    "horas_menor_consumo": [
                        {"hora": hora, "consumo_promedio": round(consumo, 2)} 
                        for hora, consumo in horas_ordenadas[-3:]
                    ],
                },
                "anomalias": anomalias,
                "datos_tendencia": datos_tendencia,
            }

            return Response(response_data)

        except Tanque.DoesNotExist:
            return Response({"error": "Tanque no encontrado."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
