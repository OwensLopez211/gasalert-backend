# Generated by Django 5.0.1 on 2024-11-13 00:05

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stations', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comuna',
            options={'ordering': ['nombre'], 'verbose_name': 'Comuna', 'verbose_name_plural': 'Comunas'},
        ),
        migrations.AlterModelOptions(
            name='estacion',
            options={'ordering': ['-creado_en'], 'verbose_name': 'Estación', 'verbose_name_plural': 'Estaciones'},
        ),
        migrations.AlterModelOptions(
            name='region',
            options={'ordering': ['nombre'], 'verbose_name': 'Región', 'verbose_name_plural': 'Regiones'},
        ),
        migrations.AddField(
            model_name='estacion',
            name='activa',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='estacion',
            name='creado_por',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, related_name='estaciones_creadas', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ubicacion',
            name='coordenadas',
            field=models.CharField(blank=True, help_text='Formato: latitud,longitud', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='ubicacion',
            name='direccion_detalle',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='region',
            name='nombre',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='comuna',
            unique_together={('nombre', 'region')},
        ),
        migrations.CreateModel(
            name='EstacionUsuarioRol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.CharField(choices=[('admin', 'Administrador'), ('supervisor', 'Supervisor'), ('operador', 'Operador')], max_length=20)),
                ('activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('modificado_en', models.DateTimeField(auto_now=True)),
                ('comuna_alcance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='supervisores', to='stations.comuna')),
                ('estacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usuarios_roles', to='stations.estacion')),
                ('region_alcance', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='supervisores', to='stations.region')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles_estaciones', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Rol de Usuario en Estación',
                'verbose_name_plural': 'Roles de Usuarios en Estaciones',
                'db_table': 'estacion_usuario_rol',
                'ordering': ['-creado_en'],
                'unique_together': {('usuario', 'estacion', 'rol')},
            },
        ),
    ]
