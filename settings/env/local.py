# Project modules
from settings.base import *


DEBUG = True
ALLOWED_HOSTS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'db.sqlite3',
    },
}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
