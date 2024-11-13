from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stations.models import Estacion
from .models import TipoCombustible, Tanque, Lectura, Umbral

User = get_user_model()

class TanqueTests(TestCase):
    def setUp(self):
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Crear estación de prueba
        self.estacion = Estacion.objects.create(
            nombre='Estación Test',
            ubicacion='Ubicación Test',
            creado_por=self.user
        )
        
        # Crear tipo de combustible
        self.tipo_combustible = TipoCombustible.objects.create(
            tipo='93',
            descripcion='Gasolina 93 octanos'
        )

    def test_crear_tanque(self):
        tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=1000.0
        )
        self.assertEqual(tanque.nombre, 'Tanque Test')
        self.assertEqual(tanque.capacidad_total, 1000.0)
        self.assertTrue(tanque.activo)

    def test_crear_lectura(self):
        tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=1000.0
        )
        
        lectura = Lectura.objects.create(
            tanque=tanque,
            fecha='2024-01-01T12:00:00Z',
            nivel=75.5,
            volumen=755.0
        )
        
        self.assertEqual(lectura.nivel, 75.5)
        self.assertEqual(lectura.volumen, 755.0)

    def test_crear_umbral(self):
        tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=1000.0
        )
        
        umbral = Umbral.objects.create(
            tanque=tanque,
            umbral_maximo=90.0,
            umbral_minimo=20.0,
            modificado_por=self.user
        )
        
        self.assertEqual(umbral.umbral_maximo, 90.0)
        self.assertEqual(umbral.umbral_minimo, 20.0)