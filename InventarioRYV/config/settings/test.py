"""Configuración para el entorno de pruebas."""
from .development import *  # noqa: F401, F403

# Usar el storage estándar para evitar requerir el manifesto de whitenoise
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
