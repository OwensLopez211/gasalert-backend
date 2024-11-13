from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from apps.stations.models import Region, Comuna, Estacion, EstacionUsuarioRol
from django.contrib.auth import get_user_model

User = get_user_model()

class RegionViewsTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        self.region = Region.objects.create(nombre="Región Test")

    def test_list_regions_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('stations:region-list')
        response = self.client.get(url)
        self.assertEqual(
            response.status_code, 
            status.HTTP_401_UNAUTHORIZED,
            "Se esperaba HTTP 401 UNAUTHORIZED para usuario no autenticado"
        )

    def test_list_regions(self):
        url = reverse('stations:region-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_list_regions_unauthenticated(self):
        self.client.force_authenticate(user=None)
        url = reverse('stations:region-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class ComunaViewsTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        self.region = Region.objects.create(nombre="Región Test")
        self.comuna = Comuna.objects.create(
            nombre="Comuna Test",
            region=self.region
        )

    def test_list_comunas_by_region(self):
        url = reverse('stations:comuna-by-region', args=[self.region.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nombre'], 'Comuna Test')

    def test_list_comunas_invalid_region(self):
        url = reverse('stations:comuna-by-region', args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

class EstacionViewsTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.client.force_authenticate(user=self.user)
        self.region = Region.objects.create(nombre="Región Test")
        self.comuna = Comuna.objects.create(
            nombre="Comuna Test",
            region=self.region
        )
        self.estacion_data = {
            'nombre': 'Estación Test',
            'ubicacion': 'Ubicación Test',
            'descripcion': 'Descripción Test',
            'ubicacion_detalle': {
                'comuna': self.comuna.id
            }
        }

    def test_create_estacion(self):
        url = reverse('stations:estacion-list-create')
        response = self.client.post(url, self.estacion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Estacion.objects.count(), 1)
        self.assertEqual(Estacion.objects.get().nombre, 'Estación Test')

    def test_list_estaciones(self):
        # Crear algunas estaciones primero
        Estacion.objects.create(
            nombre="Estación 1",
            ubicacion="Ubicación 1",
            creado_por=self.user
        )
        Estacion.objects.create(
            nombre="Estación 2",
            ubicacion="Ubicación 2",
            creado_por=self.user
        )

        url = reverse('stations:estacion-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_update_estacion(self):
        estacion = Estacion.objects.create(
            nombre="Estación Test",
            ubicacion="Ubicación Test",
            creado_por=self.user
        )
        url = reverse('stations:estacion-detail', args=[estacion.id])
        updated_data = {
            'nombre': 'Estación Actualizada',
            'ubicacion': 'Nueva Ubicación'
        }
        response = self.client.patch(url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Estacion.objects.get(id=estacion.id).nombre,
            'Estación Actualizada'
        )

    def test_delete_estacion(self):
        estacion = Estacion.objects.create(
            nombre="Estación Test",
            ubicacion="Ubicación Test",
            creado_por=self.user
        )
        url = reverse('stations:estacion-detail', args=[estacion.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Estacion.objects.count(), 0)


class EstacionViewsAdditionalTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='testuser',
            password='testpass123',
            email='test@test.com'
        )
        self.client.force_authenticate(user=self.user)
        
        # Crear datos de prueba
        self.region = Region.objects.create(nombre="Región Test")
        self.comuna = Comuna.objects.create(
            nombre="Comuna Test",
            region=self.region
        )
        
        # Crear algunas estaciones
        self.estacion1 = Estacion.objects.create(
            nombre="Estación 1",
            ubicacion="Ubicación 1",
            creado_por=self.user
        )
        self.estacion2 = Estacion.objects.create(
            nombre="Estación 2",
            ubicacion="Ubicación 2",
            creado_por=self.user
        )

    def test_list_estaciones_by_role(self):
        # Crear usuario no admin
        user_normal = User.objects.create_user(
            username='normal',
            password='normal123'
        )
        
        # Asignar rol
        EstacionUsuarioRol.objects.create(
            usuario=user_normal,
            estacion=self.estacion1,
            rol='operador'
        )
        
        # Probar como operador
        self.client.force_authenticate(user=user_normal)
        response = self.client.get(reverse('stations:estacion-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # Probar como admin
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('stations:estacion-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_estacion_detail_permissions(self):
        # Crear usuario normal
        user_normal = User.objects.create_user(
            username='normal',
            password='normal123'
        )
        
        # Intentar acceder sin permisos
        self.client.force_authenticate(user=user_normal)
        response = self.client.get(
            reverse('stations:estacion-detail', args=[self.estacion1.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Dar permisos y probar nuevamente
        EstacionUsuarioRol.objects.create(
            usuario=user_normal,
            estacion=self.estacion1,
            rol='admin'
        )
        response = self.client.get(
            reverse('stations:estacion-detail', args=[self.estacion1.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_estacion(self):
        url = reverse('stations:estacion-detail', args=[self.estacion1.id])
        data = {'nombre': 'Estación Actualizada'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Estacion.objects.get(id=self.estacion1.id).nombre,
            'Estación Actualizada'
        )