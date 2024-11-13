from rest_framework import serializers
from .models import TipoCombustible, Tanque, Lectura
from django.db.models import Avg, Min, Max
from datetime import timedelta
from django.utils import timezone

class TipoCombustibleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoCombustible
        fields = ['id', 'tipo', 'descripcion', 'activo']

class LecturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lectura
        fields = ['id', 'tanque', 'fecha', 'nivel', 'volumen', 'temperatura', 'creado_en']
        read_only_fields = ['creado_en']

class TanqueSerializer(serializers.ModelSerializer):
    tipo_combustible_nombre = serializers.CharField(source='tipo_combustible.tipo', read_only=True)
    estacion_nombre = serializers.CharField(source='estacion.nombre', read_only=True)
    ultima_lectura = serializers.SerializerMethodField()
    
    class Meta:
        model = Tanque
        fields = [
            'id', 'nombre', 'tipo_combustible', 'tipo_combustible_nombre',
            'estacion', 'estacion_nombre', 'capacidad_total', 'descripcion',
            'activo', 'creado_en', 'modificado_en', 'ultima_lectura'
        ]
        read_only_fields = ['creado_en', 'modificado_en']

    def get_ultima_lectura(self, obj):
        ultima = obj.lecturas.first()
        if ultima:
            return {
                'nivel': ultima.nivel,
                'volumen': ultima.volumen,
                'fecha': ultima.fecha,
                'temperatura': ultima.temperatura
            }
        return None

    def validate_nombre(self, value):
        """Validar que el nombre no esté duplicado en la misma estación"""
        estacion_id = self.initial_data.get('estacion')
        if self.instance is None:  # Solo para creación
            if Tanque.objects.filter(
                nombre__iexact=value,
                estacion_id=estacion_id
            ).exists():
                raise serializers.ValidationError(
                    "Ya existe un tanque con este nombre en esta estación"
                )
        return value

class DashboardTanqueSerializer(serializers.ModelSerializer):
    ultima_lectura = serializers.SerializerMethodField()
    promedio_24h = serializers.SerializerMethodField()
    min_24h = serializers.SerializerMethodField()
    max_24h = serializers.SerializerMethodField()
    tendencia = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    porcentaje_capacidad = serializers.SerializerMethodField()
    
    class Meta:
        model = Tanque
        fields = [
            'id', 'nombre', 'tipo_combustible', 'capacidad_total',
            'ultima_lectura', 'promedio_24h', 'min_24h', 'max_24h',
            'tendencia', 'estado', 'porcentaje_capacidad'
        ]

    def get_ultima_lectura(self, obj):
        ultima = obj.lecturas.first()
        if ultima:
            return {
                'nivel': ultima.nivel,
                'volumen': ultima.volumen,
                'fecha': ultima.fecha,
                'temperatura': ultima.temperatura
            }
        return None

    def get_promedio_24h(self, obj):
        return self._get_estadisticas_24h(obj).get('promedio', None)

    def get_min_24h(self, obj):
        return self._get_estadisticas_24h(obj).get('minimo', None)

    def get_max_24h(self, obj):
        return self._get_estadisticas_24h(obj).get('maximo', None)

    def get_tendencia(self, obj):
        """Calcula la tendencia basada en las últimas lecturas"""
        ultimas_lecturas = obj.lecturas.order_by('-fecha')[:2]
        if len(ultimas_lecturas) < 2:
            return 'estable'
        
        diferencia = ultimas_lecturas[0].nivel - ultimas_lecturas[1].nivel
        if abs(diferencia) < 1:  # Menos de 1% de cambio
            return 'estable'
        return 'subiendo' if diferencia > 0 else 'bajando'

    def get_estado(self, obj):
        """Determina el estado del tanque basado en umbrales"""
        ultima = obj.lecturas.first()
        if not ultima:
            return 'sin_datos'
            
        umbral = obj.umbrales.first()
        if not umbral:
            return 'sin_umbrales'
            
        if ultima.nivel >= umbral.umbral_maximo:
            return 'alto'
        elif ultima.nivel <= umbral.umbral_minimo:
            return 'bajo'
        return 'normal'

    def get_porcentaje_capacidad(self, obj):
        """Calcula el porcentaje de capacidad utilizada"""
        ultima = obj.lecturas.first()
        if not ultima or not obj.capacidad_total:
            return 0
        return (ultima.volumen / obj.capacidad_total) * 100

    def _get_estadisticas_24h(self, obj):
        """Método auxiliar para calcular estadísticas de las últimas 24 horas"""
        fecha_24h = timezone.now() - timedelta(hours=24)
        lecturas_24h = obj.lecturas.filter(fecha__gte=fecha_24h)
        
        stats = lecturas_24h.aggregate(
            promedio=Avg('nivel'),
            minimo=Min('nivel'),
            maximo=Max('nivel')
        )
        
        return {
            'promedio': round(stats['promedio'], 2) if stats['promedio'] else None,
            'minimo': stats['minimo'],
            'maximo': stats['maximo']
        }

class DashboardEstacionSerializer(serializers.Serializer):
    """Serializer para estadísticas generales de la estación"""
    total_tanques = serializers.IntegerField()
    tanques_operativos = serializers.IntegerField()
    tanques_criticos = serializers.IntegerField()
    volumen_total = serializers.FloatField()
    capacidad_total = serializers.FloatField()
    porcentaje_capacidad_total = serializers.FloatField()
    alertas_activas = serializers.IntegerField()