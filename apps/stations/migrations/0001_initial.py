# Generated by Django 5.0.1 on 2024-11-19 00:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
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
                ("nombre", models.CharField(max_length=255, unique=True)),
            ],
            options={
                "verbose_name": "Región",
                "verbose_name_plural": "Regiones",
                "db_table": "region",
                "ordering": ["nombre"],
            },
        ),
        migrations.CreateModel(
            name="Estacion",
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
                ("ubicacion", models.CharField(max_length=255)),
                ("descripcion", models.TextField(blank=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("activa", models.BooleanField(default=True)),
                (
                    "creado_por",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="estaciones_creadas",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Estación",
                "verbose_name_plural": "Estaciones",
                "db_table": "estacion",
                "ordering": ["-creado_en"],
            },
        ),
        migrations.CreateModel(
            name="Comuna",
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
                    "region",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="comunas",
                        to="stations.region",
                    ),
                ),
            ],
            options={
                "verbose_name": "Comuna",
                "verbose_name_plural": "Comunas",
                "db_table": "comuna",
                "ordering": ["nombre"],
                "unique_together": {("nombre", "region")},
            },
        ),
        migrations.CreateModel(
            name="Ubicacion",
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
                    "direccion_detalle",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "coordenadas",
                    models.CharField(
                        blank=True,
                        help_text="Formato: latitud,longitud",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "comuna",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="estaciones",
                        to="stations.comuna",
                    ),
                ),
                (
                    "estacion",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ubicacion_detalle",
                        to="stations.estacion",
                    ),
                ),
            ],
            options={
                "verbose_name": "Ubicación",
                "verbose_name_plural": "Ubicaciones",
                "db_table": "ubicaciones",
            },
        ),
        migrations.CreateModel(
            name="EstacionUsuarioRol",
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
                    "rol",
                    models.CharField(
                        choices=[
                            ("admin", "Administrador"),
                            ("supervisor", "Supervisor"),
                            ("operador", "Operador"),
                        ],
                        max_length=20,
                    ),
                ),
                ("activo", models.BooleanField(default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("modificado_en", models.DateTimeField(auto_now=True)),
                (
                    "comuna_alcance",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supervisores",
                        to="stations.comuna",
                    ),
                ),
                (
                    "estacion",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="usuarios_roles",
                        to="stations.estacion",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="roles_estaciones",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "region_alcance",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supervisores",
                        to="stations.region",
                    ),
                ),
            ],
            options={
                "verbose_name": "Rol de Usuario en Estación",
                "verbose_name_plural": "Roles de Usuarios en Estaciones",
                "db_table": "estacion_usuario_rol",
                "ordering": ["-creado_en"],
                "unique_together": {("usuario", "estacion", "rol")},
            },
        ),
    ]
