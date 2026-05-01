# Project modules
from settings.base import *
import os


DEBUG = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv("BLOG_SQLITE_PATH", BLOG_SQLITE_PATH),
    },
}
