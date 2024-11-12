from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import *

urlpatterns = [
    # Autenticación
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    
    # Usuarios
    path('users/', UserListCreateView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', UserRetrieveUpdateView.as_view(), name='user-detail'),
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
    
    # Roles y Permisos
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path('roles/<int:pk>/permissions/', RolePermissionsView.as_view(), name='role-permissions'),
    
    # Auditoría
    path('audit/sessions/', UserSessionListView.as_view(), name='session-list'),
    path('audit/actions/', UserActionLogView.as_view(), name='action-log'),
]