from rest_framework import serializers
from .models import ReportGeneration
from apps.tanks.serializers import TanqueSerializer
from apps.alerts.serializers import AlertaSerializer

class ReportGenerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportGeneration
        fields = '__all__'
        read_only_fields = ('usuario', 'fecha_generacion', 'archivo')

class ReportDataSerializer(serializers.Serializer):
    tanks_status = TanqueSerializer(many=True)
    alerts = AlertaSerializer(many=True)
    consumption_metrics = serializers.DictField()
    trends = serializers.DictField()
    recommendations = serializers.ListField()