# Generated by Django 5.0.1 on 2024-11-19 20:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alerts", "0004_alter_configuracionumbrales_unique_together"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alerta",
            name="configuracion_umbral",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="alertas",
                to="alerts.configuracionumbrales",
            ),
        ),
    ]
