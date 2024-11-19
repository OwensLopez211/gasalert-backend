from rest_framework import serializers
from .models import ConfiguracionUmbrales

class ConfiguracionUmbralesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionUmbrales
        fields = '__all__'
        read_only_fields = ['modificado_en', 'modificado_por']

class ConfiguracionUmbralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionUmbrales
        fields = ['tanque', 'tipo', 'valor', 'activo']

    def validate_valor(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("El valor debe estar entre 0 y 100.")
        return value

