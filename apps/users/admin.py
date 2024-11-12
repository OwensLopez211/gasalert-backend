from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Role, Permission, RolePermission, UserSession, UserHistory, UserActionLog

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'tipo_usuario', 'estacion_id', 'is_active', 'creado_en')
    list_filter = ('tipo_usuario', 'is_active', 'creado_en')
    search_fields = ('username', 'email')
    ordering = ('-creado_en',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('email', 'tipo_usuario', 'estacion_id')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'tipo_usuario', 'password1', 'password2'),
        }),
    )

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ('rol', 'permiso')
    list_filter = ('rol', 'permiso')
    search_fields = ('rol__nombre', 'permiso__nombre')

@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_inicio', 'fecha_fin', 'ip_usuario')
    list_filter = ('fecha_inicio', 'fecha_fin')
    search_fields = ('usuario__email', 'ip_usuario')
    ordering = ('-fecha_inicio',)

@admin.register(UserHistory)
class UserHistoryAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'campo_modificado', 'fecha_modificacion')
    list_filter = ('campo_modificado', 'fecha_modificacion')
    search_fields = ('usuario__email', 'campo_modificado')
    ordering = ('-fecha_modificacion',)

@admin.register(UserActionLog)
class UserActionLogAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'descripcion_accion', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('usuario__email', 'descripcion_accion')
    ordering = ('-fecha',)