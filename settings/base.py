# Python modules
import os

# Django modules
from django.utils.translation import gettext_lazy as _

# Project modules
from settings.conf import *  # noqa: F403


# ----------------------------------------------
# Path
#
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
ROOT_URLCONF = 'settings.urls'
WSGI_APPLICATION = 'settings.wsgi.application'
ASGI_APPLICATION = "settings.asgi.application"
AUTH_USER_MODEL = 'users.CustomUser'

os.makedirs(LOGS_DIR, exist_ok=True)

# ----------------------------------------------
# Apps
#
DJANGO_AND_THIRD_PARTY_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'rest_framework',
    'rest_framework_simplejwt',
    'drf_spectacular',
    'debug_toolbar',
    'django_extensions',
   
]
PROJECT_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.users.apps.UsersConfig',
    'apps.blog.apps.BlogConfig',
    'apps.abstracts.apps.AbstractsConfig',
    'apps.notifications.apps.NotificationsConfig',
]
INSTALLED_APPS = DJANGO_AND_THIRD_PARTY_APPS + PROJECT_APPS

# ----------------------------------------------
# Middleware | Templates | Validators
#
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'apps.core.middlewares.CustomLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.abstracts.middleware.DebugRequestLoggingMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ----------------------------------------------
# Internationalization
#
LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


ENGLISH_LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", _("English")),
    ("ru", _("Russian")),
    ("kk", _("Kazakh")),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# ----------------------------------------------
# Static | Media
#
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REDIS_URL = os.getenv("BLOG_REDIS_URL", os.getenv("REDIS_URL", BLOG_REDIS_URL))
CELERY_BROKER_URL = os.getenv("BLOG_CELERY_BROKER_URL", BLOG_CELERY_BROKER_URL)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
FLOWER_BASIC_AUTH = (
    f"{BLOG_FLOWER_USER}:{BLOG_FLOWER_PASSWORD}"
    if BLOG_FLOWER_USER and BLOG_FLOWER_PASSWORD
    else ""
)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "advanced_blog",
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "formatters": {
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)s %(name)s %(module)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "filename": os.path.join(LOGS_DIR, "app.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "verbose",
        },
        "debug_requests_file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "filename": os.path.join(LOGS_DIR, "debug_requests.log"),
            "formatter": "verbose",
            "filters": ["require_debug_true"],
        },
    },
    "loggers": {
        "users": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "blog": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["file"],
            "level": "WARNING",
            "propagate": False,
        },
        "debug_requests": {
            "handlers": ["debug_requests_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ----------------------------------------------
# Celery Configuration
#
_celery_redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"  # noqa: F405
CELERY_BROKER_URL = _celery_redis_url
CELERY_RESULT_BACKEND = _celery_redis_url
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
