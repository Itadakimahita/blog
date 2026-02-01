# Project modules
from decouple import config
from datetime import timedelta

# ----------------------------------------------
# Env id
#
ENV_POSSIBLE_OPTIONS = (
    "local",
    "prod",
)
ENV_ID = config("BLOG_ENV_ID", cast=str)

SECRET_KEY = 'django-insecure-i#z7u29m#1puniov0f=pe@oy#8jy*260qdv%jbat@$325xy6(i'

