from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Avg, Max, Min, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, TruncMonth
from .models import TipoCombustible, Tanque, Lectura
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
    tank_id = request.data.get('tank_id')
    reading = request.data.get('reading')
    
    if tank_id and reading:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"tank_{tank_id}",
            {
                "type": "tank_update",
                "tank_id": tank_id,
                "reading": reading
            }
        )
        return Response({"status": "ok"})
    return Response({"error": "Invalid data"}, status=400)

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