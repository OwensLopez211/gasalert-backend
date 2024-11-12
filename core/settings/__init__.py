import os
from decouple import config

# Por defecto usar configuración local
settings_module = config('DJANGO_SETTINGS_MODULE', default='core.settings.local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)