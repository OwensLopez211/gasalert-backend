from django.apps import AppConfig

class TanksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tanks'  # Asegúrate de que este nombre coincida con el path de la app
    verbose_name = 'Tanques'
