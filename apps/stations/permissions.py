from rest_framework import permissions

class EstacionPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        # Los usuarios anónimos no tienen acceso
        if not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        # Si el usuario no está autenticado, denegar acceso
        if not request.user.is_authenticated:
            return False
            
        # Superusuarios tienen acceso total
        if request.user.is_superuser:
            return True

        # Verificar si el usuario tiene algún rol en la estación
        user_rol = obj.usuarios_roles.filter(
            usuario=request.user,
            activo=True
        ).first()

        if not user_rol:
            return False

        # Para métodos seguros (GET, HEAD, OPTIONS), cualquier rol tiene acceso
        if request.method in permissions.SAFE_METHODS:
            return True

        # Para modificaciones, solo rol admin
        return user_rol.rol == 'admin'