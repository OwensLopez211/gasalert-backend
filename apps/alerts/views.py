from rest_framework import viewsets, permissions
from rest_framework.response import Response
from apps.alerts.models import ConfiguracionUmbrales
from apps.tanks.models import Tanque
from .serializers import ConfiguracionUmbralesSerializer, ConfiguracionUmbralCreateSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from rest_framework.exceptions import ValidationError

class ConfiguracionUmbralesViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ConfiguracionUmbrales.objects.filter(
            tanque__estacion__in=user.estaciones.all()
        )

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ConfiguracionUmbralCreateSerializer
        return ConfiguracionUmbralesSerializer

    def perform_create(self, serializer):
        tanque = serializer.validated_data['tanque']
        user = self.request.user

        # Validar que el tanque pertenece a una estación del usuario
        if not tanque.estacion in user.estaciones.all():
            raise PermissionDenied("No tienes permiso para configurar este tanque.")

        # Validar el valor del umbral (por si lo recibimos mal desde un cliente externo)
        if not 0 <= serializer.validated_data['valor'] <= 100:
            raise ValidationError("El valor del umbral debe estar entre 0 y 100.")

        serializer.save(modificado_por=user)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def update_thresholds(request, tank_id):
    try:
        # Verifica que el tanque pertenece a una estación del usuario autenticado
        user = request.user
        tanque = get_object_or_404(Tanque, id=tank_id, estacion__in=user.estaciones.all())

        if request.method == 'GET':
            # Retorna los umbrales activos asociados al tanque
            umbrales = ConfiguracionUmbrales.objects.filter(tanque=tanque, activo=True)
            
            if not umbrales.exists():
                # Si no hay umbrales, devolver valores predeterminados
                tipos = ['CRITICO', 'BAJO', 'MEDIO', 'ALTO', 'LIMITE']
                data = {tipo: 50.0 for tipo in tipos}  # Valores predeterminados
                return Response(data)

            data = {umbral.tipo: umbral.valor for umbral in umbrales}
            return Response(data)

        elif request.method == 'POST':
            # Procesa la actualización de umbrales como antes
            umbrales = request.data.get('umbrales', {})
            if not umbrales:
                return Response(
                    {"detail": "No se proporcionaron umbrales."},
                    status=HTTP_400_BAD_REQUEST
                )

            for tipo, valor in umbrales.items():
                if not isinstance(valor, (int, float)) or not 0 <= valor <= 100:
                    return Response(
                        {"detail": f"El valor para el umbral '{tipo}' debe estar entre 0 y 100."},
                        status=HTTP_400_BAD_REQUEST
                    )

                ConfiguracionUmbrales.objects.update_or_create(
                    tanque=tanque,
                    tipo=tipo,
                    defaults={
                        'valor': valor,
                        'modificado_por': user,
                        'activo': True,
                    },
                )
            return Response({"detail": "Umbrales actualizados correctamente"})
    except Exception as e:
        return Response({"detail": f"Error inesperado: {str(e)}"}, status=HTTP_400_BAD_REQUEST)

    

@api_view(['GET'])
def test_alert(request):
    return Response({"detail": "Test alert endpoint working correctly."})