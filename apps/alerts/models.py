from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.utils import timezone
from apps.tanks.models import Tanque

class ConfiguracionUmbrales(models.Model):
    """Configuración de umbrales para cada tanque"""
    TIPO_UMBRAL = [
        ('CRITICO', 'Crítico'),
        ('BAJO', 'Bajo'),
        ('MEDIO', 'Medio'),
        ('ALTO', 'Alto'),
        ('LIMITE', 'Límite'),
    ]

    tanque = models.ForeignKey(
        Tanque,
        on_delete=models.CASCADE,
        related_name='configuraciones_umbrales'
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_UMBRAL
    )
    valor = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Valor del umbral en porcentaje (0-100)"
    )
    activo = models.BooleanField(default=True)
    modificado_en = models.DateTimeField(auto_now=True)
    modificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='umbrales_configurados'
    )

    class Meta:
        db_table = 'configuracion_umbrales'
        verbose_name = 'Configuración de Umbral'
        verbose_name_plural = 'Configuraciones de Umbrales'
        unique_together = ['tanque', 'tipo']
        ordering = ['tanque', 'tipo', 'activo']

class Alerta(models.Model):
    """Alertas generadas por violación de umbrales y tendencias"""
    ESTADO_CHOICES = [
        ('ACTIVA', 'Activa'),
        ('NOTIFICADA', 'Notificada'),
        ('RESUELTA', 'Resuelta'),
    ]

    TIPO_TENDENCIA = [
        ('CONSUMO_INUSUAL', 'Consumo Inusual'),
        ('PATRON_REPOSICION', 'Patrón de Reposición Irregular'),
        ('FRECUENCIA_CRITICA', 'Frecuencia Crítica Alta'),
    ]

    tanque = models.ForeignKey(
        Tanque,
        on_delete=models.CASCADE,
        related_name='alertas'
    )
    # Campo existente para alertas por umbrales
    configuracion_umbral = models.ForeignKey(
        ConfiguracionUmbrales,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alertas'
    )
    # Nuevo campo para tipo de tendencia
    tipo_tendencia = models.CharField(
        max_length=20,
        choices=TIPO_TENDENCIA,
        null=True,
        blank=True,
        help_text="Tipo de tendencia detectada"
    )
    # Nuevos campos para almacenar datos de tendencia
    valor_anterior = models.FloatField(
        null=True,
        blank=True,
        help_text="Valor anterior para comparación de tendencia"
    )
    tasa_cambio = models.FloatField(
        null=True,
        blank=True,
        help_text="Tasa de cambio detectada"
    )
    valor_esperado = models.FloatField(
        null=True,
        blank=True,
        help_text="Valor esperado según tendencia histórica"
    )
    desviacion = models.FloatField(
        null=True,
        blank=True,
        help_text="Desviación del valor esperado"
    )
    # Campos existentes
    nivel_detectado = models.FloatField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='ACTIVA'
    )
    fecha_atencion = models.DateTimeField(null=True, blank=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='alertas_atendidas'
    )
    notas = models.TextField(blank=True)

    class Meta:
        db_table = 'alerta'
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-fecha_generacion']

    def es_alerta_tendencia(self):
        """Verifica si es una alerta de tendencia"""
        return self.tipo_tendencia is not None

    def get_tipo_display(self):
        """Devuelve el tipo de alerta (umbral o tendencia)"""
        if self.configuracion_umbral:
            return self.configuracion_umbral.get_tipo_display()
        elif self.tipo_tendencia:
            return dict(self.TIPO_TENDENCIA).get(self.tipo_tendencia)
        return "Desconocido"

class Notificacion(models.Model):
    """Notificaciones enviadas por las alertas"""
    TIPO_CHOICES = [
        ('EMAIL', 'Email'),
        ('PLATFORM', 'Plataforma'),
        ('SMS', 'SMS'),
    ]
    
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ENVIADA', 'Enviada'),
        ('ERROR', 'Error'),
    ]

    alerta = models.ForeignKey(
        Alerta,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notificaciones_recibidas'
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='PENDIENTE'
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    intentos = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        db_table = 'notificacion'
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_envio']

    def marcar_como_enviada(self):
        self.estado = 'ENVIADA'
        self.fecha_envio = timezone.now()
        self.save()

    def marcar_como_leida(self):
        self.fecha_lectura = timezone.now()
        self.save()

    def registrar_error(self, error_message):
        self.estado = 'ERROR'
        self.error = error_message
        self.intentos += 1
        self.save()