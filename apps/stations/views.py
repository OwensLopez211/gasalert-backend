from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework_simplejwt.authentication import JWTAuthentication
import logging
from django.utils import timezone
from django.db.models import Q
from .models import (
    Region, 
    Comuna, 
    Estacion, 
    Ubicacion, 
    EstacionUsuarioRol
)
from .serializers import (
    RegionSerializer,
    ComunaSerializer,
    EstacionSerializer,
    EstacionUsuarioRolSerializer
)

logger = logging.getLogger(__name__)

class RegionListView(generics.ListAPIView):
    """
    Lista todas las regiones.
    """
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]

class ComunasByRegionView(generics.ListAPIView):
    """
    Lista las comunas de una región específica.
    """
    serializer_class = ComunaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        region_id = self.kwargs.get('region_id')
        return Comuna.objects.filter(region_id=region_id)

class EstacionListCreateView(generics.ListCreateAPIView):
    """
    Lista y crea estaciones.
    """
    serializer_class = EstacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        logger.info(
            f"Usuario {request.user.username} creando estación",
            extra={
                'user_id': request.user.id,
                'timestamp': timezone.now(),
                'data': request.data
            }
        )
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        logger.debug(
            f"Usuario {request.user.username} listando estaciones",
            extra={
                'user_id': request.user.id,
                'timestamp': timezone.now(),
                'filters': request.query_params
            }
        )
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        
        # Superusuario ve todo
        if user.is_superuser:
            return Estacion.objects.all()
            
        # Obtener roles del usuario
        roles = EstacionUsuarioRol.objects.filter(usuario=user, activo=True)
        
        # Construir query basado en roles
        queryset = Estacion.objects.none()
        for rol in roles:
            if rol.rol == 'admin':
                queryset |= Estacion.objects.all()
            elif rol.rol == 'supervisor':
                if rol.region_alcance:
                    queryset |= Estacion.objects.filter(
                        ubicacion_detalle__comuna__region=rol.region_alcance
                    )
                elif rol.comuna_alcance:
                    queryset |= Estacion.objects.filter(
                        ubicacion_detalle__comuna=rol.comuna_alcance
                    )
            else:  # operador
                queryset |= Estacion.objects.filter(id=rol.estacion.id)
                
        return queryset.distinct()

class EstacionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Recupera, actualiza o elimina una estación.
    """
    serializer_class = EstacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Estacion.objects.all()
    
    def check_object_permissions(self, request, obj):
        user = request.user
        if user.is_superuser:
            return True
            
        # Verificar roles del usuario
        roles = EstacionUsuarioRol.objects.filter(
            usuario=user,
            activo=True,
            estacion=obj
        )
        
        if not roles.exists():
            raise PermissionDenied("No tiene permisos para esta estación.")
            
        # Para modificaciones, verificar que sea admin
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not roles.filter(rol='admin').exists():
                raise PermissionDenied("Solo administradores pueden modificar estaciones.")
            
@api_view(['GET'])
def initial_data(request):
    """Endpoint para obtener datos iniciales necesarios en el frontend"""
    return Response({
        'regiones': RegionSerializer(
            Region.objects.all(),
            many=True
        ).data,
        'roles': [
            {'id': 'admin', 'nombre': 'Administrador'},
            {'id': 'supervisor', 'nombre': 'Supervisor'},
            {'id': 'operador', 'nombre': 'Operador'}
        ],
        'user_permissions': {
            'can_create_station': request.user.is_superuser or
                EstacionUsuarioRol.objects.filter(
                    usuario=request.user,
                    rol='admin'
                ).exists(),
            'can_manage_users': request.user.is_superuser
        }
    })