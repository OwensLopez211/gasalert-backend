from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from apps.stations.models import Estacion
from apps.tanks.models import (
    TipoCombustible,
    Tanque,
    Lectura,
    Umbral
)
from zoneinfo import ZoneInfo 
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

class TanksAPITestBase(APITestCase):
    """Clase base para las pruebas de la API de tanques"""
    
    def setUp(self):
        # Crear usuarios
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        
        self.normal_user = User.objects.create_user(
            username='normal',
            email='normal@test.com',
            password='normal123'
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
        
        # Cliente API
        self.client = APIClient()

class TipoCombustibleViewTests(TanksAPITestBase):
    """Pruebas para las vistas de TipoCombustible"""
    
    def test_listar_tipos_combustible_sin_auth(self):
        """Verificar que no se puede acceder sin autenticación"""
        url = reverse('tanks:tipocombustible-list')  # Este nombre de URL viene del DefaultRouter
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_listar_tipos_combustible_con_auth(self):
        """Verificar listado de tipos de combustible con autenticación"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:tipocombustible-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['tipo'], '93')

    def test_crear_tipo_combustible(self):
        """Verificar creación de tipo de combustible"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:tipocombustible-list')
        data = {
            'tipo': '95',
            'descripcion': 'Gasolina 95 octanos'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TipoCombustible.objects.count(), 2)
        self.assertEqual(response.data['tipo'], '95')

class TanqueViewTests(TanksAPITestBase):
    """Pruebas para las vistas de Tanque"""
    
    def setUp(self):
        super().setUp()
        self.tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=1000.0
        )

    def test_listar_tanques(self):
        """Verificar listado de tanques"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:tanque-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['nombre'], 'Tanque Test')

    def test_crear_tanque(self):
        """Verificar creación de tanque"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:tanque-list')
        data = {
            'nombre': 'Nuevo Tanque',
            'tipo_combustible': self.tipo_combustible.id,
            'estacion': self.estacion.id,
            'capacidad_total': 2000.0,
            'descripcion': 'Tanque de prueba'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tanque.objects.count(), 2)
        self.assertEqual(response.data['nombre'], 'Nuevo Tanque')

    def test_registrar_lectura(self):
        """Verificar registro de lectura en tanque"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:tanque-registrar-lectura', args=[self.tanque.id])
        data = {
            'nivel': 75.5,
            'volumen': 755.0,
            'temperatura': 25.0,
            'fecha': timezone.now().isoformat()
        }
        response = self.client.post(url, data, format='json')
        
        # Agregar esto para debug
        if response.status_code != status.HTTP_201_CREATED:
            print("Error Response:", response.data)
            
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lectura.objects.count(), 1)
        self.assertEqual(Lectura.objects.first().nivel, 75.5)

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.stations.models import Estacion
from apps.tanks.models import TipoCombustible, Tanque, Lectura

class LecturaViewTests(TanksAPITestBase):
    def setUp(self):
        super().setUp()
        self.tanque = Tanque.objects.create(
            nombre='Tanque Test',
            tipo_combustible=self.tipo_combustible,
            estacion=self.estacion,
            capacidad_total=1000.0
        )
        
        # Crear lecturas con tiempos específicos y asegurar que están en UTC
        self.now = timezone.now()
        
        # Primera lectura: hace 3 horas
        self.lectura1 = Lectura.objects.create(
            tanque=self.tanque,
            fecha=self.now - timedelta(hours=3),
            nivel=80.0,
            volumen=800.0,
            temperatura=25.0
        )
        
        # Segunda lectura: hace 2 horas
        self.lectura2 = Lectura.objects.create(
            tanque=self.tanque,
            fecha=self.now - timedelta(hours=2),
            nivel=70.0,
            volumen=700.0,
            temperatura=25.0
        )
        
        # Tercera lectura: hace 1 hora
        self.lectura3 = Lectura.objects.create(
            tanque=self.tanque,
            fecha=self.now - timedelta(hours=1),
            nivel=60.0,
            volumen=600.0,
            temperatura=25.0
        )

    def format_datetime(self, dt):
        """Formatear datetime para URL"""
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

    def test_filtrar_lecturas_por_fecha(self):
        """Verificar filtrado de lecturas por fecha"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Filtrar para obtener solo las últimas 2 lecturas
        fecha_desde = self.now - timedelta(hours=2, minutes=30)
        fecha_desde_str = self.format_datetime(fecha_desde)
        
        url = f"{reverse('tanks:lectura-list')}?fecha_desde={fecha_desde_str}"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(float(response.data[0]['nivel']), 60.0)
        self.assertEqual(float(response.data[1]['nivel']), 70.0)

    def test_obtener_lecturas_por_rango(self):
        """Verificar obtención de lecturas por rango de fechas"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Definir rango para obtener solo la lectura del medio
        fecha_desde = self.now - timedelta(hours=2, minutes=30)
        fecha_hasta = self.now - timedelta(hours=1, minutes=30)
        
        fecha_desde_str = self.format_datetime(fecha_desde)
        fecha_hasta_str = self.format_datetime(fecha_hasta)
        
        url = (f"{reverse('tanks:lectura-list')}?"
               f"fecha_desde={fecha_desde_str}&"
               f"fecha_hasta={fecha_hasta_str}")
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(float(response.data[0]['nivel']), 70.0)

    def test_listar_lecturas(self):
        """Verificar listado de lecturas"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('tanks:lectura-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Verificar orden descendente por fecha
        self.assertEqual(float(response.data[0]['nivel']), 60.0)
        self.assertEqual(float(response.data[1]['nivel']), 70.0)
        self.assertEqual(float(response.data[2]['nivel']), 80.0)

    def test_permisos_lecturas(self):
        """Verificar permisos de acceso a lecturas"""
        url = reverse('tanks:lectura-list')
        
        # Probar sin autenticación
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Probar con usuario sin permisos
        usuario_sin_permisos = User.objects.create_user(
            username='sinpermisos',
            password='test123'
        )
        self.client.force_authenticate(user=usuario_sin_permisos)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)