import os
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# ---------------------------------------------------------------------------
# libpq / psycopg2 encoding fix (must be set BEFORE any DB connection)
#
# On Windows with a Russian-locale PostgreSQL installation, libpq sends
# authentication error messages in CP1251 (Cyrillic).  psycopg2 then tries
# to decode them as UTF-8 and raises:
#   UnicodeDecodeError: 'utf-8' codec can't decode byte 0xc2 ...
#
# Setting PGCLIENTENCODING here (before django.setup() ever touches the DB)
# instructs libpq to request UTF-8 from the server for ALL text communication,
# including error messages.
# ---------------------------------------------------------------------------
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

SECRET_KEY = config("DJANGO_SECRET_KEY")

DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

AUTH_USER_MODEL = "users.User"

TIME_ZONE = "Asia/Dushanbe"
LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "mptt",                                         # C-1: was missing — required for User MPTT tree
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.users",
    "apps.products",
    "apps.withdrawals",
    "apps.orders",
    "apps.bonuses",
    "apps.mlm",
    "apps.delivery",
    "apps.reservations",
    "apps.notifications",
    "apps.common",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware  (M-8: CorsMiddleware moved before SessionMiddleware)
# ---------------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",            # M-8: must precede CommonMiddleware & SessionMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database (PostgreSQL)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": config("DB_CONN_MAX_AGE", cast=int, default=60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            # S-4: "prefer" is acceptable for base/dev; prod.py overrides to "require".
            "sslmode": config("DB_SSLMODE", default="prefer"),
            # Force UTF-8 client encoding regardless of PostgreSQL server locale.
            # Prevents psycopg2 UnicodeDecodeError when server is configured
            # with WIN1251, LATIN1, or any non-UTF-8 server_encoding.
            "client_encoding": "UTF8",
        },
    }
}

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

ADMIN_FRONTEND_STATIC_DIR = BASE_DIR.parent / "admin_frontend" / "static"
STATICFILES_DIRS = [
    ADMIN_FRONTEND_STATIC_DIR,
] if ADMIN_FRONTEND_STATIC_DIR.exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": config("DRF_PAGE_SIZE", cast=int, default=20),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": config("DRF_THROTTLE_ANON", default="100/min"),
        "user": config("DRF_THROTTLE_USER", default="1000/min"),
    },
}

# ---------------------------------------------------------------------------
# Simple JWT  (S-3: JWT_SIGNING_KEY has no default — must be set explicitly
#              in the environment so it is independent from SECRET_KEY)
# ---------------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=config("JWT_ACCESS_LIFETIME_MIN", cast=int, default=15)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=config("JWT_REFRESH_LIFETIME_DAYS", cast=int, default=7)
    ),
    "ROTATE_REFRESH_TOKENS": config("JWT_ROTATE_REFRESH_TOKENS", cast=bool, default=True),
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": config("JWT_SIGNING_KEY"),           # S-3: mandatory, no fallback to SECRET_KEY
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

# ---------------------------------------------------------------------------
# drf-spectacular
# ---------------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE": "Grass MLM API",
    "DESCRIPTION": "Grass MLM backend API documentation",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "OrderStatusEnum": "apps.orders.models.OrderStatus.choices",
        "DeliveryStatusEnum": "apps.delivery.models.DeliveryStatus.choices",
        "ReservationStatusEnum": "apps.reservations.models.ReservationStatus.choices",
        "WithdrawalStatusEnum": "apps.withdrawals.models.WithdrawalStatus.choices",
        "BonusStatusEnum": "apps.bonuses.models.BonusStatus.choices",
        "UserStatusEnum": "apps.users.models.UserStatus.choices",
    },
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_EXPOSE_HEADERS = ["Content-Type", "Authorization"]

# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False

# ---------------------------------------------------------------------------
# Celery / Redis
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", cast=int, default=300)
CELERY_TASK_SOFT_TIME_LIMIT = config("CELERY_TASK_SOFT_TIME_LIMIT", cast=int, default=240)
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# ---------------------------------------------------------------------------
# Redis cache
# ---------------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_CACHE_URL", default="redis://redis:6379/2"),
        "TIMEOUT": config("REDIS_CACHE_TIMEOUT", cast=int, default=300),  # M-7: was hardcoded 5000 (83 min)
        "OPTIONS": {
            "client_class": "django_redis.client.DefaultClient",
        },
    }
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_LEVEL = config("DJANGO_LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": (
                '{"time": "%(asctime)s", "level": "%(levelname)s", '
                '"name": "%(name)s", "message": "%(message)s", '
                '"module": "%(module)s", "line": %(lineno)d}'
            ),
        },
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": config("DJANGO_DB_LOG_LEVEL", default="WARNING"),
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Reservation system
# ---------------------------------------------------------------------------

# Duration (minutes) for a soft stock reservation before auto-expiry.
# Celery Beat task re-runs every 5 min to batch-expire stale reservations.
RESERVATION_TIMEOUT_MINUTES: int = config(
    "RESERVATION_TIMEOUT_MINUTES",
    cast=int,
    default=21600,  # 15 days (> 2 weeks)
)

# ---------------------------------------------------------------------------
# Celery Beat periodic tasks
# ---------------------------------------------------------------------------
# Guarded import: celery may not be installed in all environments (e.g. CI).
# Django settings must remain importable without Celery.
try:
    from celery.schedules import crontab  # noqa: E402

    CELERY_BEAT_SCHEDULE = {
        "expire-stale-reservations": {
            "task": "reservations.expire_stale",
            "schedule": crontab(minute="*/5"),
            "options": {"expires": 240},  # drop task if not consumed within 4 min
        },
        "distribute-confirm-bonuses": {
            "task": "bonuses.distribute_and_confirm",
            # Bonus retries are handled by the task itself; this is a safety net
            # to periodically re-try any PENDING bonuses in case the Celery task
            # did not execute (broker outage, etc.).
            # NOTE: only dispatched via Order.deliver endpoint in normal flow.
            "schedule": crontab(hour="*/1"),  # every hour — safety net
            "enabled": False,  # disabled by default; enable via env if needed
        },
    }
except ImportError:
    # Celery not installed — CELERY_BEAT_SCHEDULE stays undefined (harmless).
    pass
