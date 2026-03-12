from decouple import Csv, config

from .base import *                    

DEBUG = True

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="*",
    cast=Csv(),
)

INTERNAL_IPS = ["127.0.0.1", "localhost"]

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost,http://127.0.0.1",
    cast=Csv(),
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

LOGGING["handlers"]["console"]["formatter"] = "verbose"                       
LOGGING["root"]["level"] = "DEBUG"                       
LOGGING["loggers"]["django.db.backends"]["level"] = config(                       
    "DJANGO_DB_LOG_LEVEL", default="DEBUG"
)

CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", cast=bool, default=False)
CELERY_TASK_EAGER_PROPAGATES = True