from django.apps import AppConfig

class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.alerts'
    verbose_name = 'Alertas'

    def ready(self):
        try:
            import apps.alerts.signals  # noqa
        except ImportError:
            pass