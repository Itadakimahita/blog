from django.apps import AppConfig


class AbstractsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.abstracts'

    def ready(self) -> None:
        from django.conf import settings

        from apps.abstracts.i18n_compile import compile_project_locales

        compile_project_locales(list(getattr(settings, "LOCALE_PATHS", [])))
