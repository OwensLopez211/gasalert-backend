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
from .serializers import ConfiguracionUmbralesSerializer, UmbralesConfiguracionSerializer, AlertaSerializer, NotificacionSerializer
from django.utils.timezone import now


class AlertaViewSet(viewsets.ModelViewSet):
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Alerta.objects.all().select_related(
            'tanque',
            'configuracion_umbral'
        )
    

    @action(detail=False, methods=['post'])
    def verificar_nivel(self, request):
        """Verifica si el nivel ha vuelto a la normalidad"""
        tank_id = request.data.get('tank_id')
        nivel_actual = request.data.get('nivel')

        if not tank_id or nivel_actual is None:
            return Response(
                {"error": "Se requiere tank_id y nivel"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            umbrales = ConfiguracionUmbrales.objects.filter(
                tanque_id=tank_id, 
                activo=True
            )
            
            umbral_bajo = umbrales.filter(tipo='BAJO').first()
            umbral_alto = umbrales.filter(tipo='ALTO').first()
            
            if umbral_bajo and umbral_alto:
                if umbral_bajo.valor < nivel_actual < umbral_alto.valor:
                    # Marcar alertas activas como resueltas
                    alertas_actualizadas = Alerta.objects.filter(
                        tanque_id=tank_id,
                        estado__in=['ACTIVA', 'NOTIFICADA']
                    ).update(
                        estado='RESUELTA',
                        fecha_resolucion=now()
                    )
                    
                    return Response({
                        "message": "Nivel normal detectado",
                        "alertas_resueltas": alertas_actualizadas
                    })
            
            return Response({
                "message": "Nivel fuera de rango normal",
                "umbral_bajo": umbral_bajo.valor if umbral_bajo else None,
                "umbral_alto": umbral_alto.valor if umbral_alto else None,
                "nivel_actual": nivel_actual
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """Marca una alerta específica como resuelta"""
        try:
            alerta = self.get_object()
            if alerta.estado == 'RESUELTA':
                return Response({
                    "message": "La alerta ya está resuelta"
                })

            alerta.estado = 'RESUELTA'
            alerta.fecha_resolucion = timezone.now()
            alerta.save()

            return Response({
                "message": "Alerta marcada como resuelta",
                "fecha_resolucion": alerta.fecha_resolucion
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def activas(self, request):
        """Lista todas las alertas activas para un tanque"""
        tank_id = request.query_params.get('tank_id')
        if not tank_id:
            return Response(
                {"error": "Se requiere tank_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        alertas = self.get_queryset().filter(
            tanque_id=tank_id,
            estado__in=['ACTIVA', 'NOTIFICADA']
        )
        
        serializer = self.get_serializer(alertas, many=True)
        return Response(serializer.data)

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
            {"error": "Datos incompletos"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        umbral = ConfiguracionUmbrales.objects.get(id=configuracion_umbral_id)
        
        # Verificar si existe una alerta activa no resuelta
        alerta_activa = Alerta.objects.filter(
            tanque_id=tanque_id,
            configuracion_umbral__tipo=umbral.tipo,
            estado__in=['ACTIVA', 'NOTIFICADA']
        ).exists()

        if not alerta_activa:
            alerta = Alerta.objects.create(
                tanque_id=tanque_id,
                configuracion_umbral=umbral,
                nivel_detectado=nivel_detectado,
                estado='ACTIVA'
            )
            serializer = AlertaSerializer(alerta)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"message": "Ya existe una alerta activa para este umbral"},
                status=status.HTTP_200_OK
            )

    except ConfiguracionUmbrales.DoesNotExist:
        return Response(
            {"error": "Configuración de umbral no encontrada"},
            status=status.HTTP_404_NOT_FOUND,
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
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
        notificaciones = Notificacion.objects.filter(
            destinatario=request.user
        ).select_related(
            'alerta',
            'alerta__configuracion_umbral',
            'alerta__tanque'
        ).order_by('-fecha_envio')

        serializer = NotificacionSerializer(notificaciones, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        """Marca una notificación como leída"""
        try:
            # Buscamos la notificación por su ID propio, no por el ID de la alerta
            notificacion = Notificacion.objects.get(
                pk=pk,
                destinatario=request.user
            )
            notificacion.marcar_como_leida()
            
            return Response({
                "id": notificacion.id,
                "mensaje": f"Alerta: {notificacion.alerta.configuracion_umbral.tipo} en {notificacion.alerta.tanque.nombre}",
                "leido": True,
                "fecha_lectura": notificacion.fecha_lectura,
            })
        except Notificacion.DoesNotExist:
            return Response(
                {"error": "Notificación no encontrada"},
                status=404
            )
        
