from django.test import TestCase
from django.contrib.auth import get_user_model  # Agregar esta importación
from rest_framework.test import APIRequestFactory
from apps.stations.serializers import UbicacionSerializer, EstacionSerializer
from apps.stations.models import Region, Comuna, Estacion, Ubicacion

User = get_user_model()  # Agregar esta línea

class SerializerTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()  # Agregar esto al setUp
        self.region = Region.objects.create(nombre="Región Test")
        self.comuna = Comuna.objects.create(
            nombre="Comuna Test",
            region=self.region
        )
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )


    def test_ubicacion_coordenadas_validation(self):
        data = {'coordenadas': '-33.4569,-70.6483', 'comuna': self.comuna.id}
        serializer = UbicacionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        data['coordenadas'] = 'invalid'
        serializer = UbicacionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('coordenadas', serializer.errors)

    def test_estacion_unique_nombre(self):
        # Crear una estación primero
        Estacion.objects.create(
            nombre="Estación Test",
            ubicacion="Ubicación Test",
            creado_por=self.user
        )
        
        # Intentar crear otra con el mismo nombre
        serializer = EstacionSerializer(data={
            'nombre': "Estación Test",
            'ubicacion': "Otra Ubicación",
            'creado_por': self.user.id
        }, context={'request': type('Request', (), {'user': self.user})()})
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('nombre', serializer.errors)

    def test_estacion_creation_with_ubicacion(self):
        request = self.factory.post('/')
        request.user = self.user
        request.data = {
            'nombre': 'Nueva Estación',
            'ubicacion': 'Nueva Ubicación',
            'ubicacion_detalle': {
                'comuna': self.comuna.id,
                'direccion_detalle': 'Dirección detallada',
                'coordenadas': '-33.4569,-70.6483'
            }
        }
        
        serializer = EstacionSerializer(
            data=request.data,
            context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        
        estacion = serializer.save()
        self.assertEqual(estacion.nombre, 'Nueva Estación')