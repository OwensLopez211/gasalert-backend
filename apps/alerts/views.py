from rest_framework import viewsets, status
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import pre_delete
from django.shortcuts import get_object_or_404
from .models import Alerta, ConfiguracionUmbrales, Tanque, Notificacion
from .serializers import ConfiguracionUmbralesSerializer, UmbralesConfiguracionSerializer, AlertaSerializer


class UmbralesViewSet(viewsets.ModelViewSet):
    serializer_class = ConfiguracionUmbralesSerializer
    permission_classes = [IsAuthenticated]
    queryset = ConfiguracionUmbrales.objects.all()

    def get_queryset(self):
        queryset = ConfiguracionUmbrales.objects.all()  # Quitamos el filtro activo=True
        tanque_id = self.request.query_params.get('tanque_id')
        if tanque_id:
            return queryset.filter(tanque_id=tanque_id).select_related(
                'tanque',
                'modificado_por'
            )
        return queryset

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(ConfiguracionUmbrales, pk=pk)

    def perform_update(self, serializer):
        serializer.save(modificado_por=self.request.user)

    def perform_create(self, serializer):
        serializer.save(modificado_por=self.request.user)

    @action(detail=False, methods=['post'])
    def configurar_todos(self, request):
        """Configura todos los umbrales para un tanque"""
        tanque_id = request.data.get('tanque_id')
        serializer = UmbralesConfiguracionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Desactivar umbrales anteriores
                ConfiguracionUmbrales.objects.filter(
                    tanque_id=tanque_id
                ).update(activo=False)

                # Crear nuevos umbrales
                umbrales_data = [
                    ('CRITICO', serializer.validated_data['critico']),
                    ('BAJO', serializer.validated_data['bajo']),
                    ('MEDIO', serializer.validated_data['medio']),
                    ('ALTO', serializer.validated_data['alto']),
                    ('LIMITE', serializer.validated_data['limite'])
                ]

                for tipo, valor in umbrales_data:
                    ConfiguracionUmbrales.objects.create(
                        tanque_id=tanque_id,
                        tipo=tipo,
                        valor=valor,
                        activo=True,
                        modificado_por=request.user
                    )

                return Response({
                    'message': 'Umbrales configurados exitosamente',
                    'umbrales': serializer.validated_data
                })

        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def inicializar_umbrales(self, request):
        """Inicializa los umbrales predeterminados para un tanque"""
        tanque_id = request.data.get('tanque_id')
        if not tanque_id:
            return Response(
                {"error": "El ID del tanque es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valores_predeterminados = {
            'CRITICO': 15.0,
            'BAJO': 30.0,
            'MEDIO': 50.0,
            'ALTO': 75.0,
            'LIMITE': 90.0,
        }

        try:
            with transaction.atomic():
                umbrales_creados = []
                for tipo, valor in valores_predeterminados.items():
                    if not ConfiguracionUmbrales.objects.filter(
                        tanque_id=tanque_id, tipo=tipo
                    ).exists():
                        umbral = ConfiguracionUmbrales.objects.create(
                            tanque_id=tanque_id,
                            tipo=tipo,
                            valor=valor,
                            activo=True,
                            modificado_por=request.user
                        )
                        umbrales_creados.append(umbral)

                return Response(
                    {
                        "message": "Umbrales inicializados correctamente.",
                        "umbrales": ConfiguracionUmbralesSerializer(
                            umbrales_creados, many=True
                        ).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """Activa un umbral específico"""
        umbral = self.get_object()
        umbral.activo = True
        umbral.save()
        serializer = self.get_serializer(umbral)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """Desactiva un umbral específico"""
        umbral = self.get_object()
        umbral.activo = False
        umbral.save()
        serializer = self.get_serializer(umbral)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Actualiza parcialmente un umbral"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generar_alerta(request):
    """Generar una alerta basada en los datos recibidos"""
    tanque_id = request.data.get('tanque_id')
    nivel_detectado = request.data.get('nivel_detectado')
    configuracion_umbral_id = request.data.get('configuracion_umbral_id')

    if not tanque_id or not nivel_detectado or not configuracion_umbral_id:
        return Response(
            {"error": "Datos incompletos. Se requiere tanque_id, nivel_detectado y configuracion_umbral_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        umbral = ConfiguracionUmbrales.objects.get(id=configuracion_umbral_id)
        alerta = Alerta.objects.create(
            tanque_id=tanque_id,
            configuracion_umbral=umbral,
            nivel_detectado=nivel_detectado,
            estado='ACTIVA'
        )
        serializer = AlertaSerializer(alerta)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except ConfiguracionUmbrales.DoesNotExist:
        return Response(
            {"error": "Configuración de umbral no encontrada."},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": f"Error al generar la alerta: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    
@receiver(pre_delete, sender=ConfiguracionUmbrales)
def actualizar_alertas_al_eliminar_umbral(sender, instance, **kwargs):
    Alerta.objects.filter(configuracion_umbral=instance).update(
        estado='RESUELTA',
        configuracion_umbral=None
    )
class NotificacionesViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Lista las notificaciones del usuario autenticado"""
        notificaciones = Notificacion.objects.filter(destinatario=request.user).order_by('-fecha_envio')
        data = [
            {
                "id": n.id,
                "message": f"Alerta: {n.alerta.configuracion_umbral.tipo} en {n.alerta.tanque.nombre}",
                "leido": n.fecha_lectura is not None,
            }
            for n in notificaciones
        ]
        return Response(data)

    def partial_update(self, request, pk=None):
        """Marca una notificación como leída"""
        try:
            notificacion = Notificacion.objects.get(pk=pk, destinatario=request.user)
            notificacion.marcar_como_leida()
            return Response({"message": "Notificación marcada como leída"})
        except Notificacion.DoesNotExist:
            return Response({"error": "Notificación no encontrada"}, status=404)
