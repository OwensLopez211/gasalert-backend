from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from decouple import config
from dotenv import load_dotenv

# Cargar las variables del archivo .env explícitamente
load_dotenv()

# Verificar que las variables de entorno se cargaron correctamente
print("DB_NAME (celery):", config('DB_NAME', default=None))
print("DB_USER (celery):", config('DB_USER', default=None))
print("DB_PASSWORD (celery):", config('DB_PASSWORD', default=None))
print("DB_HOST (celery):", config('DB_HOST', default=None))
print("DB_PORT (celery):", config('DB_PORT', default=None))

# Configuración del entorno Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Crear instancia de Celery
app = Celery('core')

# Configuración del broker y el backend
app.conf.broker_url = 'redis://localhost:6379/0'
app.conf.result_backend = 'redis://localhost:6379/0'

# Configuración de Celery basada en settings de Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configuración adicional para optimización
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Santiago',
    enable_utc=False,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos máximo por tarea
    worker_max_tasks_per_child=50,  # Reiniciar worker después de 50 tareas
    broker_connection_retry_on_startup=True,
)

# Descubrir tareas automáticamente en todas las aplicaciones instaladas
app.autodiscover_tasks([
    'apps.tanks',
    'apps.alerts',
])

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

# Manejador de errores para tareas
@app.task(bind=True)
def handle_task_error(self, uuid):
    result = app.AsyncResult(uuid)
    print(f'Task {uuid} failed: {result.result}')