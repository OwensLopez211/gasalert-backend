from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Permission, UserSession, UserActionLog

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer para listado y creación de usuarios.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'tipo_usuario', 'estacion_id', 
                 'first_name', 'last_name', 'is_active', 'creado_en')
        read_only_fields = ('creado_en',)
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

class UserDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalles y actualización de usuarios.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'tipo_usuario', 'estacion_id',
                 'first_name', 'last_name', 'is_active', 'creado_en',
                 'groups', 'user_permissions')
        read_only_fields = ('creado_en',)

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer para el perfil del usuario.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                 'tipo_usuario', 'estacion_id')
        read_only_fields = ('username', 'email', 'tipo_usuario', 'estacion_id')

class RoleSerializer(serializers.ModelSerializer):
    """
    Serializer para roles.
    """
    class Meta:
        model = Role
        fields = '__all__'

class PermissionSerializer(serializers.ModelSerializer):
    """
    Serializer para permisos.
    """
    class Meta:
        model = Permission
        fields = '__all__'

class UserSessionSerializer(serializers.ModelSerializer):
    """
    Serializer para sesiones de usuario.
    """
    class Meta:
        model = UserSession
        fields = ('id', 'usuario', 'fecha_inicio', 'fecha_fin', 'ip_usuario')

class UserActionLogSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de acciones.
    """
    class Meta:
        model = UserActionLog
        fields = ('id', 'usuario', 'descripcion_accion', 'fecha')