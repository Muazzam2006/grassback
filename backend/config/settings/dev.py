from decouple import Csv, config

from .base import *  # noqa: F401, F403

DEBUG = True

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="*",
    cast=Csv(),
)

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# ---------------------------------------------------------------------------
# CORS / CSRF — open for local front-end development
# ---------------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = True

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost,http://127.0.0.1",
    cast=Csv(),
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

# ---------------------------------------------------------------------------
# Email — console backend for development
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# Logging — verbose for development
# ---------------------------------------------------------------------------

LOGGING["handlers"]["console"]["formatter"] = "verbose"  # type: ignore[index]
LOGGING["root"]["level"] = "DEBUG"  # type: ignore[index]
LOGGING["loggers"]["django.db.backends"]["level"] = config(  # type: ignore[index]
    "DJANGO_DB_LOG_LEVEL", default="DEBUG"
)

# ---------------------------------------------------------------------------
# Celery — run tasks synchronously in dev unless overridden in .env
# ---------------------------------------------------------------------------

CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", cast=bool, default=False)
CELERY_TASK_EAGER_PROPAGATES = True