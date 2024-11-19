from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from apps.stations.models import Estacion
from django.utils import timezone

class TipoCombustible(models.Model):
    """Modelo para los diferentes tipos de combustible"""
    tipo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'tipos_combustible'
        verbose_name = 'Tipo de Combustible'
        verbose_name_plural = 'Tipos de Combustible'
        app_label = 'tanks'  # Asegúrate de que el nombre coincida con el de tu app
        ordering = ['tipo']

    def __str__(self):
        return self.tipo

class Tanque(models.Model):
    """Modelo para los tanques de combustible"""
    nombre = models.CharField(max_length=255)
    tipo_combustible = models.ForeignKey(
        TipoCombustible,
        on_delete=models.PROTECT,
        related_name='tanques'
    )
    estacion = models.ForeignKey(
        Estacion,
        on_delete=models.CASCADE,
        related_name='tanques'
    )
    capacidad_total = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Capacidad total en litros"
    )
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tanque'
        verbose_name = 'Tanque'
        verbose_name_plural = 'Tanques'
        ordering = ['estacion', 'nombre']
        app_label = 'tanks'  # Asegúrate de que el nombre coincida con el de tu app
        unique_together = ['nombre', 'estacion']

    def __str__(self):
        return f"{self.nombre} - {self.estacion.nombre}"

class Lectura(models.Model):
    """Modelo para las lecturas de nivel de los tanques"""
    tanque = models.ForeignKey(
        'Tanque',
        on_delete=models.CASCADE,
        related_name='lecturas'
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        help_text="Fecha y hora de la lectura"
    )
    nivel = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Nivel en porcentaje (0-100)"
    )
    volumen = models.FloatField(
        validators=[MinValueValidator(0.0)],
        help_text="Volumen en litros"
    )
    temperatura = models.FloatField(
        null=True, 
        blank=True,
        help_text="Temperatura en grados Celsius"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lectura'
        verbose_name = 'Lectura'
        verbose_name_plural = 'Lecturas'
        app_label = 'tanks'  # Asegúrate de que el nombre coincida con el de tu app
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tanque.nombre} - {self.fecha}"

    def save(self, *args, **kwargs):
        if not self.fecha:
            self.fecha = timezone.now()
        super().save(*args, **kwargs)

