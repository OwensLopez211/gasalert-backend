from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.stations.models import Estacion
from apps.tanks.models import (
    TipoCombustible,
    Tanque,
    Lectura,
    Umbral
)
import random

User = get_user_model()

class DashboardTestCase(APITestCase):
    def setUp(self):
        # Crear usuario admin
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        
        # Crear estación
        self.estacion = Estacion.objects.create(
            nombre='Estación Test',
            ubicacion='Ubicación Test',
            creado_por=self.admin_user
        )
        
        # Crear tipo de combustible
        self.tipo_combustible = TipoCombustible.objects.create(
            tipo='93',
            descripcion='Gasolina 93 octanos'
        )
        
        # Crear tanque
        self.tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=10000.0
        )
        
        # Crear umbral
        self.umbral = Umbral.objects.create(
            tanque=self.tanque,
            umbral_maximo=90.0,
            umbral_minimo=20.0,
            modificado_por=self.admin_user
        )
        
        # Crear lecturas para los últimos 2 días
        self.now = timezone.now()
        nivel = 70.0
        
        for i in range(48):  # 48 horas
            Lectura.objects.create(
                tanque=self.tanque,
                fecha=self.now - timedelta(hours=i),
                nivel=nivel,
                volumen=(nivel/100) * self.tanque.capacidad_total,
                temperatura=25.0
            )
            # Simular pequeños cambios en el nivel
            nivel = max(20.0, min(90.0, nivel + random.uniform(-2.0, 2.0)))

    def test_resumen_estacion_sin_auth(self):
        """Verificar que no se puede acceder al resumen sin autenticación"""
        url = f"{reverse('tanks:dashboard-resumen-estacion')}?estacion_id={self.estacion.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_resumen_estacion_con_auth(self):
        """Verificar resumen de estación con autenticación"""
        self.client.force_authenticate(user=self.admin_user)
        url = f"{reverse('tanks:dashboard-resumen-estacion')}?estacion_id={self.estacion.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tanques'], 1)
        self.assertEqual(response.data['tanques_operativos'], 1)
        self.assertTrue('volumen_total' in response.data)
        self.assertEqual(response.data['capacidad_total'], 10000.0)

    def test_resumen_estacion_sin_id(self):
        """Verificar que se requiere el ID de la estación"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:dashboard-resumen-estacion')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_estado_tanques(self):
        """Verificar estado de tanques"""
        self.client.force_authenticate(user=self.admin_user)
        url = f"{reverse('tanks:dashboard-estado-tanques')}?estacion_id={self.estacion.id}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        tanque_data = response.data[0]
        self.assertEqual(tanque_data['nombre'], 'Tanque Test')
        self.assertTrue('ultima_lectura' in tanque_data)
        self.assertTrue('promedio_24h' in tanque_data)
        self.assertTrue('tendencia' in tanque_data)

    def test_historico_niveles(self):
        """Verificar histórico de niveles"""
        self.client.force_authenticate(user=self.admin_user)
        url = f"{reverse('tanks:dashboard-historico-niveles')}?tanque_id={self.tanque.id}&dias=2"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 48)  # 48 horas de datos
        self.assertTrue(all(
            'fecha' in lectura and 
            'nivel' in lectura and 
            'volumen' in lectura 
            for lectura in response.data
        ))

    def test_consumo_diario(self):
        """Verificar cálculo de consumo diario"""
        self.client.force_authenticate(user=self.admin_user)
        url = f"{reverse('tanks:dashboard-consumo-diario')}?tanque_id={self.tanque.id}&dias=2"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for consumo in response.data:
            self.assertTrue('fecha' in consumo)
            self.assertTrue('consumo' in consumo)

    def test_validacion_parametros(self):
        """Verificar validación de parámetros"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Probar histórico sin tanque_id
        url = reverse('tanks:dashboard-historico-niveles')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Probar consumo diario con tanque inválido
        url = f"{reverse('tanks:dashboard-consumo-diario')}?tanque_id=999"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_permisos_usuario_normal(self):
        """Verificar permisos para usuario normal"""
        usuario_normal = User.objects.create_user(
            username='normal',
            password='normal123'
        )
        self.client.force_authenticate(user=usuario_normal)
        
        # Intentar acceder al resumen de estación
        url = f"{reverse('tanks:dashboard-resumen-estacion')}?estacion_id={self.estacion.id}"
        response = self.client.get(url)
        
        # Debería poder ver pero sin datos
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_tanques'], 0)