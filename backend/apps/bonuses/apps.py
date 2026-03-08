from django.apps import AppConfig


class BonusesConfig(AppConfig):
    name = "apps.bonuses"
    verbose_name = "Bonuses"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        import apps.bonuses.signals              
