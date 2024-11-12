# Usar una imagen oficial de Python como imagen base
FROM python:3.10-slim as python-base

# Variables de entorno Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.4.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1 \
    PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# Imagen base para desarrollo y producción
FROM python-base as base
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        # deps for installing poetry
        curl \
        # deps for building python deps
        build-essential \
        # deps for psycopg2
        libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Copiar solo los archivos necesarios para instalar dependencias
WORKDIR $PYSETUP_PATH
COPY ./poetry.lock ./pyproject.toml ./
RUN poetry install --no-dev

# Imagen de desarrollo
FROM base as development
ENV DJANGO_SETTINGS_MODULE=core.settings.local
WORKDIR $PYSETUP_PATH
RUN poetry install

# Copiar el proyecto
COPY . .

# Imagen de producción
FROM base as production
ENV DJANGO_SETTINGS_MODULE=core.settings.production
WORKDIR $PYSETUP_PATH

# Copiar el proyecto
COPY . .

# Crear usuario no root
RUN addgroup --system django \
    && adduser --system --ingroup django django

# Crear directorios necesarios y asignar permisos
RUN mkdir -p /var/www/static \
    && mkdir -p /var/www/media \
    && chown -R django:django /var/www

USER django

# Comando para iniciar la aplicación
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]