import os
import django
from django.conf import settings

# Configurar Django antes de ejecutar los tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.base')
django.setup()