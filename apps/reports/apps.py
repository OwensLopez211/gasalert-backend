from django.apps import AppConfig

class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reports'  # Asegúrate de que este nombre coincida con el path de la app
    verbose_name = 'Reportes'
