from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory
from apps.stations.models import Estacion, EstacionUsuarioRol
from apps.stations.permissions import EstacionPermission

User = get_user_model()

class EstacionPermissionTest(TestCase):
    def setUp(self):
        self.permission = EstacionPermission()
        self.factory = APIRequestFactory()
        
        # Crear usuarios
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        self.normal_user = User.objects.create_user(
            username='user',
            password='user123'
        )
        
        # Crear estación
        self.estacion = Estacion.objects.create(
            nombre='Test Station',
            ubicacion='Test Location',
            creado_por=self.admin_user
        )

    def test_has_permission(self):
        # Usuario anónimo
        request = self.factory.get('/')
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, None))
        
        # Usuario autenticado
        request.user = self.normal_user
        self.assertTrue(self.permission.has_permission(request, None))

    def test_has_object_permission(self):
        request = self.factory.get('/')
        request.user = self.normal_user
        
        # Usuario sin rol - no debe tener acceso
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.estacion)
        )
        
        # Agregar rol de operador
        rol = EstacionUsuarioRol.objects.create(
            usuario=self.normal_user,
            estacion=self.estacion,
            rol='operador',
            activo=True
        )
        
        # Operador puede leer
        request = self.factory.get('/')
        request.user = self.normal_user
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.estacion)
        )
        
        # Operador no puede modificar
        request = self.factory.put('/')
        request.user = self.normal_user
        self.assertFalse(
            self.permission.has_object_permission(request, None, self.estacion)
        )
        
        # Cambiar a rol admin
        rol.rol = 'admin'
        rol.save()
        
        # Admin puede modificar
        self.assertTrue(
            self.permission.has_object_permission(request, None, self.estacion)
        )