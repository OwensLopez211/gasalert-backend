# Generated by Django 5.0.1 on 2024-11-19 14:19

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("alerts", "0003_alter_configuracionumbrales_options"),
        ("tanks", "0002_remove_threshold_models"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="configuracionumbrales",
            unique_together={("tanque", "tipo")},
        ),
    ]