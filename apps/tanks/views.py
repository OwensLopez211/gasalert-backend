from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from datetime import datetime
import pytz
from .models import TipoCombustible, Tanque, Lectura
from .serializers import (
    TipoCombustibleSerializer,
    TanqueSerializer,
    LecturaSerializer,
    DashboardTanqueSerializer,
    DashboardEstacionSerializer
)

class TipoCombustibleViewSet(viewsets.ModelViewSet):
    queryset = TipoCombustible.objects.all()
    serializer_class = TipoCombustibleSerializer
    permission_classes = [IsAuthenticated]

class TanqueViewSet(viewsets.ModelViewSet):
    serializer_class = TanqueSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Tanque.objects.all()
        if not self.request.user.is_superuser:
            # Filtrar por estaciones a las que tiene acceso el usuario
            estaciones_permitidas = self.request.user.roles_estaciones.filter(
                activo=True
            ).values_list('estacion_id', flat=True)
            queryset = queryset.filter(estacion_id__in=estaciones_permitidas)
        return queryset

    @action(detail=True, methods=['post'])
    def registrar_lectura(self, request, pk=None):
        tanque = self.get_object()
        serializer = LecturaSerializer(data={
            **request.data,
            'tanque': tanque.id
        })
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def lecturas(self, request, pk=None):
        tanque = self.get_object()
        dias = int(request.query_params.get('dias', 7))
        fecha_inicio = timezone.now() - timezone.timedelta(days=dias)
        
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

    @action(detail=False, methods=['get'])
    def resumen_estacion(self, request):
        """Obtiene un resumen general de la estación"""
        estacion_id = request.query_params.get('estacion_id')
        if not estacion_id:
            return Response(
                {"error": "Debe especificar una estación"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Filtrar por permisos del usuario
        estaciones_permitidas = self._get_user_estaciones(request.user)
        base_query = Q(estacion_id=estacion_id)
        if estaciones_permitidas is not None:
            base_query &= Q(estacion_id__in=estaciones_permitidas)

        # Obtener tanques de la estación con filtros de permisos
        tanques = Tanque.objects.filter(base_query)
        
        # Calcular estadísticas
        total_tanques = tanques.count()
        tanques_operativos = tanques.filter(activo=True).count()
        
        # Contar tanques en estado crítico y calcular volumen total
        tanques_criticos = 0
        volumen_total = 0
        capacidad_total = tanques.aggregate(total=Sum('capacidad_total'))['total'] or 0
        
        for tanque in tanques:
            ultima_lectura = tanque.lecturas.first()
            if ultima_lectura:
                umbral = tanque.umbrales.first()
                if umbral and ultima_lectura.nivel <= umbral.umbral_minimo:
                    tanques_criticos += 1
                volumen_total += ultima_lectura.volumen

        data = {
            'total_tanques': total_tanques,
            'tanques_operativos': tanques_operativos,
            'tanques_criticos': tanques_criticos,
            'volumen_total': volumen_total,
            'capacidad_total': capacidad_total,
            'porcentaje_capacidad_total': (volumen_total / capacidad_total * 100) if capacidad_total else 0,
            'alertas_activas': 0
        }
        
        serializer = DashboardEstacionSerializer(data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def estado_tanques(self, request):
        """Obtiene el estado actual de todos los tanques de una estación"""
        estacion_id = request.query_params.get('estacion_id')
        if not estacion_id:
            return Response(
                {"error": "Debe especificar una estación"},
                status=status.HTTP_400_BAD_REQUEST
            )

        estaciones_permitidas = self._get_user_estaciones(request.user)
        base_query = Q(estacion_id=estacion_id)
        if estaciones_permitidas is not None:
            base_query &= Q(estacion_id__in=estaciones_permitidas)

        tanques = Tanque.objects.filter(base_query)
        serializer = DashboardTanqueSerializer(tanques, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def historico_niveles(self, request):
        """Obtiene el histórico de niveles para un tanque específico"""
        tanque_id = request.query_params.get('tanque_id')
        if not tanque_id:
            return Response(
                {"error": "Debe especificar un tanque"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tanque = self._get_tanque(tanque_id, request.user)
        dias = int(request.query_params.get('dias', 7))
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        lecturas = tanque.lecturas.filter(
            fecha__gte=fecha_inicio
        ).order_by('fecha')
        
        data = [{
            'fecha': lectura.fecha,
            'nivel': lectura.nivel,
            'volumen': lectura.volumen,
            'temperatura': lectura.temperatura
        } for lectura in lecturas]
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def consumo_diario(self, request):
        """Calcula el consumo diario promedio"""
        tanque_id = request.query_params.get('tanque_id')
        if not tanque_id:
            return Response(
                {"error": "Debe especificar un tanque"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tanque = self._get_tanque(tanque_id, request.user)
        dias = int(request.query_params.get('dias', 7))
        fecha_inicio = timezone.now() - timedelta(days=dias)
        
        lecturas = tanque.lecturas.filter(
            fecha__gte=fecha_inicio
        ).order_by('fecha')
        
        # Calcular consumo diario
        consumos = []
        lecturas_list = list(lecturas)
        for i in range(1, len(lecturas_list)):
            lectura_actual = lecturas_list[i]
            lectura_anterior = lecturas_list[i-1]
            
            # Solo calcular si las lecturas son del mismo día
            if (lectura_actual.fecha - lectura_anterior.fecha).days < 1:
                consumo = max(0, lectura_anterior.volumen - lectura_actual.volumen)
                if consumo > 0:
                    consumos.append({
                        'fecha': lectura_actual.fecha.date(),
                        'consumo': consumo
                    })
        
        return Response(consumos)