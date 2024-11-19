from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('tanks', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='historialumbrales',
            name='modificado_por',
        ),
        migrations.RemoveField(
            model_name='historialumbrales',
            name='tanque',
        ),
        migrations.RemoveField(
            model_name='umbral',
            name='modificado_por',
        ),
        migrations.RemoveField(
            model_name='umbral',
            name='tanque',
        ),
        migrations.DeleteModel(
            name='HistorialUmbrales',
        ),
        migrations.DeleteModel(
            name='Umbral',
        ),
    ]