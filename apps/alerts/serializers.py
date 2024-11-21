from rest_framework import serializers
from .models import ConfiguracionUmbrales, Alerta, Notificacion

class ConfiguracionUmbralesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionUmbrales
        fields = ['id', 'tanque', 'tipo', 'valor', 'activo']
        read_only_fields = ['modificado_en']

    def validate(self, data):
        # Valores predeterminados para cada tipo
        valores_predeterminados = {
            'CRITICO': 15.0,
            'BAJO': 30.0,
            'MEDIO': 50.0,
            'ALTO': 75.0,
            'LIMITE': 90.0,
        }

        tipo = data.get('tipo', self.instance.tipo if self.instance else None)
        valor = data.get('valor', None)

        # Asignar el valor predeterminado si no se especifica
        if valor is None and tipo in valores_predeterminados:
            data['valor'] = valores_predeterminados[tipo]

        # Validar el orden lógico
        if 'tanque' in data or self.instance:
            tanque = data.get('tanque', self.instance.tanque if self.instance else None)
            umbrales_existentes = ConfiguracionUmbrales.objects.filter(
                tanque=tanque,
                activo=True
            ).exclude(tipo=tipo)

            orden = {
                'CRITICO': 1,
                'BAJO': 2,
                'MEDIO': 3,
                'ALTO': 4,
                'LIMITE': 5
            }

            for umbral in umbrales_existentes:
                if orden[tipo] < orden[umbral.tipo] and data['valor'] >= umbral.valor:
                    raise serializers.ValidationError(
                        f'El valor del umbral {tipo} debe ser menor que el umbral {umbral.tipo} ({umbral.valor}).'
                    )
                elif orden[tipo] > orden[umbral.tipo] and data['valor'] <= umbral.valor:
                    raise serializers.ValidationError(
                        f'El valor del umbral {tipo} debe ser mayor que el umbral {umbral.tipo} ({umbral.valor}).'
                    )

        return data

    def create(self, validated_data):
        # Desactivar cualquier umbral activo del mismo tipo para el tanque
        ConfiguracionUmbrales.objects.filter(
            tanque=validated_data['tanque'],
            tipo=validated_data['tipo'],
            activo=True
        ).update(activo=False)

        # Crear el nuevo umbral
        return super().create(validated_data)


class UmbralesConfiguracionSerializer(serializers.Serializer):
    critico = serializers.FloatField(min_value=0, max_value=100)
    bajo = serializers.FloatField(min_value=0, max_value=100)
    medio = serializers.FloatField(min_value=0, max_value=100)
    alto = serializers.FloatField(min_value=0, max_value=100)
    limite = serializers.FloatField(min_value=0, max_value=100)

    def validate(self, data):
        # Validar que los valores estén en orden ascendente
        valores = [data['critico'], data['bajo'], data['medio'], data['alto'], data['limite']]
        nombres = ['crítico', 'bajo', 'medio', 'alto', 'límite']

        for i in range(len(valores) - 1):
            if valores[i] >= valores[i + 1]:
                raise serializers.ValidationError(
                    f"El valor del umbral '{nombres[i]}' ({valores[i]}) debe ser menor que el umbral '{nombres[i + 1]}' ({valores[i + 1]})"
                )
        return data
    
class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'  # O puedes especificar los campos manualmente

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = '__all__'

