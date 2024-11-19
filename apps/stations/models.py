from django.db import models
from django.conf import settings

class Region(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    
    class Meta:
        app_label = 'stations'  # Add this line
        db_table = 'region'
        verbose_name = 'Región'
        verbose_name_plural = 'Regiones'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre

class Comuna(models.Model):
    nombre = models.CharField(max_length=255)
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='comunas'
    )
    
    class Meta:
        app_label = 'stations'  # Add this line
        db_table = 'comuna'
        verbose_name = 'Comuna'
        verbose_name_plural = 'Comunas'
        ordering = ['nombre']
        unique_together = ['nombre', 'region']
    
    def __str__(self):
        return f"{self.nombre} ({self.region.nombre})"

class Estacion(models.Model):
    nombre = models.CharField(max_length=255)
    ubicacion = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='estaciones_creadas'
    )
    activa = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'stations'  # Add this line
        db_table = 'estacion'
        verbose_name = 'Estación'
        verbose_name_plural = 'Estaciones'
        ordering = ['-creado_en']
    
    def __str__(self):
        return self.nombre

class Ubicacion(models.Model):
    estacion = models.OneToOneField(
        Estacion,
        on_delete=models.CASCADE,
        related_name='ubicacion_detalle'
    )
    comuna = models.ForeignKey(
        Comuna,
        on_delete=models.PROTECT,
        related_name='estaciones'
    )
    direccion_detalle = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    coordenadas = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Formato: latitud,longitud"
    )
    
    class Meta:
        app_label = 'stations'  # Add this line
        db_table = 'ubicaciones'
        verbose_name = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'
    
    def __str__(self):
        return f"{self.estacion.nombre} - {self.comuna.nombre}"

class EstacionUsuarioRol(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('supervisor', 'Supervisor'),
        ('operador', 'Operador'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roles_estaciones'
    )
    estacion = models.ForeignKey(
        Estacion,
        on_delete=models.CASCADE,
        related_name='usuarios_roles'
    )
    rol = models.CharField(
        max_length=20,
        choices=ROLES
    )
    region_alcance = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='supervisores'
    )
    comuna_alcance = models.ForeignKey(
        Comuna,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='supervisores'
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'stations'  # Add this line
        db_table = 'estacion_usuario_rol'
        verbose_name = 'Rol de Usuario en Estación'
        verbose_name_plural = 'Roles de Usuarios en Estaciones'
        unique_together = ['usuario', 'estacion', 'rol']
        ordering = ['-creado_en']

    def __str__(self):
        return f"{self.usuario.username} - {self.estacion.nombre} - {self.get_rol_display()}"

    def save(self, *args, **kwargs):
        if self.rol == 'operador':
            self.region_alcance = None
            self.comuna_alcance = None
        super().save(*args, **kwargs)