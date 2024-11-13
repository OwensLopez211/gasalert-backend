from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.stations.models import Estacion
from apps.tanks.models import TipoCombustible
from apps.tanks.serializers import TipoCombustibleSerializer

User = get_user_model()

class SerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.estacion = Estacion.objects.create(
            nombre='Estación Test',
            ubicacion='Ubicación Test',
            creado_por=self.user
        )

class TipoCombustibleSerializerTest(SerializerTestCase):
    def test_tipo_combustible_serializer(self):
        """Probar serialización de tipo de combustible"""
        tipo_combustible = TipoCombustible.objects.create(
            tipo='93',
            descripcion='Gasolina 93 octanos'
        )
        serializer = TipoCombustibleSerializer(tipo_combustible)
        self.assertEqual(serializer.data['tipo'], '93')
        self.assertEqual(serializer.data['descripcion'], 'Gasolina 93 octanos')