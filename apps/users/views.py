from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserActionLog
from .models import Role, Permission, UserSession
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Obtener el usuario que acaba de autenticarse
                user = User.objects.get(username=request.data.get('username'))
                
                # Crear sesión de usuario
                UserSession.objects.create(
                    usuario=user,
                    ip_usuario=request.META.get('REMOTE_ADDR', '')
                )
                
                # Obtener las estaciones del usuario
                estaciones = user.roles_estaciones.filter(activo=True).values()
                
                # Añadir información adicional a la respuesta
                response.data.update({
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'tipo_usuario': user.tipo_usuario,
                        'estacion_id': user.estacion_id,
                        'estaciones': list(estaciones)
                    }
                })
                
                return response
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
from .serializers import (
    UserSerializer,
    UserDetailSerializer,
    UserProfileSerializer,
    RoleSerializer,
    PermissionSerializer,
    UserSessionSerializer,
    UserActionLogSerializer
)

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            
            if response.status_code == 200:
                # Crear sesión de usuario
                UserSession.objects.create(
                    usuario=request.user,
                    ip_usuario=request.META.get('REMOTE_ADDR', '')
                )
                
                # Añadir información adicional si es necesario
                data = response.data
                user = request.user
                data['user'] = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'tipo_usuario': user.tipo_usuario,
                    'estacion_id': user.estacion_id
                }
                
                return Response(data)
            
            return response
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class CustomPermissions:
    """
    Clase para manejar permisos personalizados
    """
    class IsAdminUser(permissions.BasePermission):
        def has_permission(self, request, view):
            return request.user and request.user.is_staff

    class IsSameUserOrAdmin(permissions.BasePermission):
        def has_object_permission(self, request, view, obj):
            return request.user.is_staff or obj == request.user

    class HasRolePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            required_permissions = getattr(view, 'required_permissions', [])
            user_permissions = request.user.role.permissions.values_list('nombre', flat=True)
            return any(perm in user_permissions for perm in required_permissions)

class LogoutView(APIView):
    """
    Vista para cerrar sesión y invalidar el token JWT.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()
            # Registrar el cierre de sesión
            if hasattr(request.user, 'current_session'):
                request.user.current_session.fecha_fin = timezone.now()
                request.user.current_session.save()
            return Response({"detail": "Logout exitoso"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserListCreateView(generics.ListCreateAPIView):
    """
    Vista para listar y crear usuarios.
    GET: Lista todos los usuarios (admin)
    POST: Crea un nuevo usuario
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [CustomPermissions.IsAdminUser]

    def get_queryset(self):
        queryset = User.objects.all()
        tipo = self.request.query_params.get('tipo_usuario', None)
        if tipo:
            queryset = queryset.filter(tipo_usuario=tipo)
        if not self.request.user.is_superuser:
            queryset = queryset.filter(estacion_id=self.request.user.estacion_id)
        return queryset

class UserRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Vista para ver y actualizar usuarios específicos.
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [CustomPermissions.IsSameUserOrAdmin]

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Vista para que los usuarios vean y actualicen su propio perfil.
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class RoleListView(generics.ListCreateAPIView):
    """
    Vista para listar y crear roles.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [CustomPermissions.IsAdminUser]

class PermissionListView(generics.ListAPIView):
    """
    Vista para listar permisos disponibles.
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [CustomPermissions.IsAdminUser]

class RolePermissionsView(generics.RetrieveUpdateAPIView):
    """
    Vista para gestionar permisos de un rol.
    """
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [CustomPermissions.IsAdminUser]

    def update(self, request, *args, **kwargs):
        role = self.get_object()
        permissions_data = request.data.get('permissions', [])
        role.permissions.set(permissions_data)
        return Response(self.get_serializer(role).data)

class UserSessionListView(generics.ListAPIView):
    """
    Vista para listar sesiones de usuario.
    """
    serializer_class = UserSessionSerializer
    permission_classes = [CustomPermissions.IsSameUserOrAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return UserSession.objects.all()
        return UserSession.objects.filter(usuario=self.request.user)

class UserActionLogView(generics.ListAPIView):
    """
    Vista para listar el registro de acciones de usuarios.
    """
    serializer_class = UserActionLogSerializer
    permission_classes = [CustomPermissions.IsSameUserOrAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return UserActionLog.objects.all()
        return UserActionLog.objects.filter(usuario=self.request.user)