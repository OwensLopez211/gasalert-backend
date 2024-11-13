from rest_framework import serializers
from .models import (
    Region, 
    Comuna, 
    Estacion, 
    Ubicacion, 
    EstacionUsuarioRol
)

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'nombre']

class ComunaSerializer(serializers.ModelSerializer):
    region_nombre = serializers.CharField(source='region.nombre', read_only=True)
    
    class Meta:
        model = Comuna
        fields = ['id', 'nombre', 'region', 'region_nombre']

class UbicacionSerializer(serializers.ModelSerializer):
    comuna_nombre = serializers.CharField(source='comuna.nombre', read_only=True)
    region_nombre = serializers.CharField(source='comuna.region.nombre', read_only=True)
    
    class Meta:
        model = Ubicacion
        fields = [
            'id', 
            'comuna', 
            'comuna_nombre',
            'region_nombre',
            'direccion_detalle',
            'coordenadas'
        ]

    def validate_coordenadas(self, value):
        """Validar formato de coordenadas"""
        if value:
            try:
                lat, lon = value.split(',')
                lat, lon = float(lat), float(lon)
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    raise ValueError
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "Formato inválido. Use: latitud,longitud (ej: -33.4569,-70.6483)"
                )
        return value

class EstacionSerializer(serializers.ModelSerializer):
    ubicacion_detalle = UbicacionSerializer(read_only=True)
    creado_por_username = serializers.CharField(source='creado_por.username', read_only=True)
    
    class Meta:
        model = Estacion
        fields = [
            'id',
            'nombre',
            'ubicacion',
            'descripcion',
            'creado_en',
            'creado_por',
            'creado_por_username',
            'activa',
            'ubicacion_detalle'
        ]
        read_only_fields = ['creado_en', 'creado_por']

    def validate_nombre(self, value):
        """Validar que el nombre no esté duplicado"""
        if Estacion.objects.filter(nombre__iexact=value).exists():
            raise serializers.ValidationError("Ya existe una estación con este nombre.")
        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        if 'ubicacion_detalle' in self.context['request'].data:
            ubicacion_data = self.context['request'].data['ubicacion_detalle']
            if not ubicacion_data.get('comuna'):
                raise serializers.ValidationError({
                    "ubicacion_detalle": "Debe especificar una comuna."
                })
        return data

    def create(self, validated_data):
        # Obtener datos de ubicación del contexto
        ubicacion_data = self.context['request'].data.get('ubicacion_detalle', {})
        
        # Asignar el usuario que crea la estación
        validated_data['creado_por'] = self.context['request'].user
        
        # Crear la estación
        estacion = super().create(validated_data)
        
        # Si hay datos de ubicación, crear la ubicación
        if ubicacion_data:
            Ubicacion.objects.create(
                estacion=estacion,
                comuna_id=ubicacion_data.get('comuna'),
                direccion_detalle=ubicacion_data.get('direccion_detalle'),
                coordenadas=ubicacion_data.get('coordenadas')
            )
        
        return estacion

class EstacionUsuarioRolSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    estacion_nombre = serializers.CharField(source='estacion.nombre', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    
    class Meta:
        model = EstacionUsuarioRol
        fields = [
            'id',
            'usuario',
            'usuario_nombre',
            'estacion',
            'estacion_nombre',
            'rol',
            'rol_display',
            'region_alcance',
            'comuna_alcance',
            'activo',
            'creado_en',
            'modificado_en'
        ]
        read_only_fields = ['creado_en', 'modificado_en']