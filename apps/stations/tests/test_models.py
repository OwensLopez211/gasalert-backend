from django.test import TestCase
from apps.stations.models import Region, Comuna, Estacion, Ubicacion  # Importación absoluta
from django.contrib.auth import get_user_model

User = get_user_model()

class RegionModelTest(TestCase):
    def setUp(self):
        self.region = Region.objects.create(
            nombre="Región Test"
        )

    def test_region_creation(self):
        self.assertEqual(self.region.nombre, "Región Test")
        self.assertTrue(isinstance(self.region, Region))
        self.assertEqual(str(self.region), "Región Test")

class ComunaModelTest(TestCase):
    def setUp(self):
        self.region = Region.objects.create(
            nombre="Región Test"
        )
        self.comuna = Comuna.objects.create(
            nombre="Comuna Test",
            region=self.region
        )

    def test_comuna_creation(self):
        self.assertEqual(self.comuna.nombre, "Comuna Test")
        self.assertEqual(self.comuna.region, self.region)
        self.assertTrue(isinstance(self.comuna, Comuna))
        self.assertEqual(str(self.comuna), "Comuna Test (Región Test)")

class EstacionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.estacion = Estacion.objects.create(
            nombre="Estación Test",
            ubicacion="Ubicación Test",
            descripcion="Descripción Test",
            creado_por=self.user
        )

    def test_estacion_creation(self):
        self.assertEqual(self.estacion.nombre, "Estación Test")
        self.assertEqual(self.estacion.ubicacion, "Ubicación Test")
        self.assertTrue(isinstance(self.estacion, Estacion))
        self.assertEqual(str(self.estacion), "Estación Test")