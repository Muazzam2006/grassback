from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"
    verbose_name = "Users"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        import apps.users.signals  
