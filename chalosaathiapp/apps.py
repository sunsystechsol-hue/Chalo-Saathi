from django.apps import AppConfig


class ChalosaathiappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chalosaathiapp'

from django.apps import AppConfig

class ChalosaathiappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chalosaathiapp'

    def ready(self):
        import chalosaathiapp.signals

