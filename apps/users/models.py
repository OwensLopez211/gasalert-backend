from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    """
    Custom user model based on GasAlertDB schema.
    """
    email = models.EmailField(unique=True)
    tipo_usuario = models.CharField(max_length=50, null=True, blank=True)
    estacion_id = models.IntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

class Role(models.Model):
    """
    Role model for user permissions based on GasAlertDB schema.
    """
    nombre = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        db_table = 'roles'

    def __str__(self):
        return self.nombre

class Permission(models.Model):
    """
    Permission model based on GasAlertDB schema.
    """
    nombre = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        db_table = 'permisos'

    def __str__(self):
        return self.nombre

class RolePermission(models.Model):
    """
    Relationship model between roles and permissions based on GasAlertDB schema.
    """
    rol = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='permisos'
    )
    permiso = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='roles'
    )

    class Meta:
        verbose_name = 'Rol Permiso'
        verbose_name_plural = 'Roles Permisos'
        db_table = 'roles_permisos'
        unique_together = ['rol', 'permiso']

    def __str__(self):
        return f"{self.rol.nombre} - {self.permiso.nombre}"

class UserSession(models.Model):
    """
    User session tracking model based on GasAlertDB schema.
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sesiones'
    )
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    ip_usuario = models.CharField(max_length=45)

    class Meta:
        verbose_name = 'Sesión'
        verbose_name_plural = 'Sesiones'
        db_table = 'sesiones'
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"Sesión de {self.usuario.email} - {self.fecha_inicio}"

class UserHistory(models.Model):
    """
    User history tracking model based on GasAlertDB schema.
    """
    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    campo_modificado = models.CharField(max_length=50)
    valor_anterior = models.TextField()
    valor_nuevo = models.TextField()
    fecha_modificacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Historial de Usuario'
        verbose_name_plural = 'Historiales de Usuario'
        db_table = 'historial_usuarios'
        ordering = ['-fecha_modificacion']

    def __str__(self):
        return f"Modificación de {self.usuario.email} - {self.campo_modificado}"

class UserActionLog(models.Model):
    """
    User action logging model based on GasAlertDB schema.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='log_acciones'
    )
    descripcion_accion = models.CharField(max_length=100)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Acción'
        verbose_name_plural = 'Log de Acciones'
        db_table = 'log_acciones'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.usuario} - {self.descripcion_accion} - {self.fecha}"