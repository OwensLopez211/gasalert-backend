# apps/tanks/admin.py
from django.contrib import admin
from .models import TipoCombustible, Tanque, Lectura, Umbral

@admin.register(TipoCombustible)
class TipoCombustibleAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'descripcion', 'activo')
    search_fields = ('tipo',)
    list_filter = ('activo',)

@admin.register(Tanque)
class TanqueAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo_combustible', 'estacion', 'capacidad_total', 'activo')
    list_filter = ('tipo_combustible', 'estacion', 'activo')
    search_fields = ('nombre', 'estacion__nombre')
    date_hierarchy = 'creado_en'

@admin.register(Lectura)
class LecturaAdmin(admin.ModelAdmin):
    list_display = ('tanque', 'fecha', 'nivel', 'volumen', 'temperatura')
    list_filter = ('tanque__tipo_combustible', 'tanque__estacion')
    search_fields = ('tanque__nombre',)
    date_hierarchy = 'fecha'

@admin.register(Umbral)
class UmbralAdmin(admin.ModelAdmin):
    list_display = ('tanque', 'umbral_maximo', 'umbral_minimo', 'modificado_en', 'modificado_por')
    list_filter = ('tanque__tipo_combustible', 'tanque__estacion')
    search_fields = ('tanque__nombre',)
    date_hierarchy = 'modificado_en'