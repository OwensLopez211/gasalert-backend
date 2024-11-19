# Generated by Django 5.0.1 on 2024-11-18 23:17

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("stations", "__first__"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TipoCombustible",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("tipo", models.CharField(max_length=50, unique=True)),
                ("descripcion", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Tipo de Combustible",
                "verbose_name_plural": "Tipos de Combustible",
                "db_table": "tipos_combustible",
                "ordering": ["tipo"],
            },
        ),
        migrations.CreateModel(
            name="Tanque",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nombre", models.CharField(max_length=255)),
                (
                    "capacidad_total",
                    models.FloatField(
                        help_text="Capacidad total en litros",
                        validators=[django.core.validators.MinValueValidator(0.0)],
                    ),
                ),
                ("descripcion", models.TextField(blank=True)),
                ("activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("modificado_en", models.DateTimeField(auto_now=True)),
                (
                    "estacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tanques",
                        to="stations.estacion",
                    ),
                ),
                (
                    "tipo_combustible",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tanques",
                        to="tanks.tipocombustible",
                    ),
                ),
            ],
            options={
                "verbose_name": "Tanque",
                "verbose_name_plural": "Tanques",
                "db_table": "tanque",
                "ordering": ["estacion", "nombre"],
                "unique_together": {("nombre", "estacion")},
            },
        ),
        migrations.CreateModel(
            name="Lectura",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "fecha",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="Fecha y hora de la lectura",
                    ),
                ),
                (
                    "nivel",
                    models.FloatField(
                        help_text="Nivel en porcentaje (0-100)",
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(100.0),
                        ],
                    ),
                ),
                (
                    "volumen",
                    models.FloatField(
                        help_text="Volumen en litros",
                        validators=[django.core.validators.MinValueValidator(0.0)],
                    ),
                ),
                (
                    "temperatura",
                    models.FloatField(
                        blank=True, help_text="Temperatura en grados Celsius", null=True
                    ),
                ),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                (
                    "tanque",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecturas",
                        to="tanks.tanque",
                    ),
                ),
            ],
            options={
                "verbose_name": "Lectura",
                "verbose_name_plural": "Lecturas",
                "db_table": "lectura",
                "ordering": ["-fecha"],
            },
        ),
        migrations.CreateModel(
            name="HistorialUmbrales",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("umbral_anterior", models.FloatField()),
                ("umbral_nuevo", models.FloatField()),
                ("fecha_modificacion", models.DateTimeField(auto_now_add=True)),
                (
                    "modificado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="historial_umbrales_modificados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tanque",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historial_umbrales",
                        to="tanks.tanque",
                    ),
                ),
            ],
            options={
                "verbose_name": "Historial de Umbral",
                "verbose_name_plural": "Historial de Umbrales",
                "db_table": "historial_umbrales",
                "ordering": ["-fecha_modificacion"],
            },
        ),
        migrations.CreateModel(
            name="Umbral",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "umbral_maximo",
                    models.FloatField(
                        help_text="Umbral máximo en porcentaje (0-100)",
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(100.0),
                        ],
                    ),
                ),
                (
                    "umbral_minimo",
                    models.FloatField(
                        help_text="Umbral mínimo en porcentaje (0-100)",
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(100.0),
                        ],
                    ),
                ),
                ("modificado_en", models.DateTimeField(auto_now=True)),
                (
                    "modificado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="umbrales_modificados",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tanque",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="umbrales",
                        to="tanks.tanque",
                    ),
                ),
            ],
            options={
                "verbose_name": "Umbral",
                "verbose_name_plural": "Umbrales",
                "db_table": "umbral",
                "ordering": ["-modificado_en"],
                "get_latest_by": "modificado_en",
            },
        ),
    ]
