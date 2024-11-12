from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'  # Importante: debe incluir el prefijo 'apps'
    verbose_name = 'Usuarios'