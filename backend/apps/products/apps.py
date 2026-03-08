from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = "apps.products"
    verbose_name = "Products"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        import apps.products.signals  
