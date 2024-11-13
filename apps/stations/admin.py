from django.contrib import admin
from .models import Region, Comuna, Estacion, Ubicacion

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'region')
    list_filter = ('region',)
    search_fields = ('nombre', 'region__nombre')

@admin.register(Estacion)
class EstacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion', 'creado_en')
    list_filter = ('creado_en',)
    search_fields = ('nombre', 'ubicacion')
    date_hierarchy = 'creado_en'

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('estacion', 'comuna')
    list_filter = ('comuna__region',)
    search_fields = ('estacion__nombre', 'comuna__nombre')