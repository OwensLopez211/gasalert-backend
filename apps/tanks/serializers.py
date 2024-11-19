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

class DashboardTanqueSerializer(serializers.ModelSerializer):
    ultima_lectura = serializers.SerializerMethodField()
    estadisticas_24h = serializers.SerializerMethodField()
    tendencia = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    
    class Meta:
        model = Tanque
        fields = [
            'id', 'nombre', 'tipo_combustible', 'capacidad_total',
            'ultima_lectura', 'estadisticas_24h', 'tendencia', 'estado'
        ]

    def get_ultima_lectura(self, obj):
        ultima = obj.lecturas.first()
        return LecturaSerializer(ultima).data if ultima else None

    def get_estadisticas_24h(self, obj):
        fecha_24h = timezone.now() - timedelta(hours=24)
        lecturas = obj.lecturas.filter(fecha__gte=fecha_24h)
        
        if not lecturas.exists():
            return None
            
        stats = {
            'promedio_nivel': lecturas.aggregate(Avg('nivel'))['nivel__avg'],
            'min_nivel': lecturas.aggregate(Min('nivel'))['nivel__min'],
            'max_nivel': lecturas.aggregate(Max('nivel'))['nivel__max'],
            'promedio_volumen': lecturas.aggregate(Avg('volumen'))['volumen__avg']
        }
        
        return {k: round(v, 2) if v is not None else None for k, v in stats.items()}

    def get_tendencia(self, obj):
        lecturas = obj.lecturas.order_by('-fecha')[:2]
        if len(lecturas) < 2:
            return 'estable'
        
        diferencia = lecturas[0].nivel - lecturas[1].nivel
        if abs(diferencia) < 1:
            return 'estable'
        return 'subiendo' if diferencia > 0 else 'bajando'

    def get_estado(self, obj):
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
    
class DashboardEstacionSerializer(serializers.Serializer):
    total_tanques = serializers.IntegerField()
    tanques_operativos = serializers.IntegerField()
    tanques_criticos = serializers.IntegerField()
    volumen_total = serializers.FloatField()
    capacidad_total = serializers.FloatField()
    porcentaje_capacidad_total = serializers.FloatField()
    alertas_activas = serializers.IntegerField()

    def get_alertas_activas(self, obj):
        tanques = obj['tanques']
        alertas = 0
        for tanque in tanques:
            ultima_lectura = tanque.lecturas.first()
            if ultima_lectura and (
                ultima_lectura.nivel <= tanque.umbral_minimo or
                ultima_lectura.nivel >= tanque.umbral_maximo
            ):
                alertas += 1
        return alertas
