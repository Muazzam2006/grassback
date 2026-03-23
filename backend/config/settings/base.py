import os
from datetime import timedelta
from pathlib import Path

from decouple import Csv, config
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

                                                                            
os.environ.setdefault("PGCLIENTENCODING", "UTF8")

BASE_DIR = Path(__file__).resolve().parent.parent.parent


SECRET_KEY = config("DJANGO_SECRET_KEY")

DEBUG = config("DJANGO_DEBUG", cast=bool, default=False)

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=Csv())

AUTH_USER_MODEL = "users.User"

TIME_ZONE = "Asia/Dushanbe"
LANGUAGE_CODE = "ru"
USE_I18N = True
USE_TZ = True


DJANGO_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_cotton",
    "mptt",                                                                                         
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "unfold.contrib.forms",
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
    "apps.slider",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

UNFOLD = {
    "SITE_TITLE": "Панель управления Grass MLM",
    "SITE_HEADER": "Админ-панель Grass MLM",
    "SITE_SYMBOL": "inventory_2",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Обзор"),
                "items": [
                    {
                        "title": _("Панель управления"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Продажи"),
                "separator": True,
                "items": [
                    {
                        "title": _("Заказы"),
                        "icon": "shopping_cart",
                        "link": reverse_lazy("admin:orders_order_changelist"),
                    },
                ],
            },
            {
                "title": _("Каталог"),
                "separator": True,
                "items": [
                    {
                        "title": _("Товары"),
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:products_product_changelist"),
                    },
                    {
                        "title": _("Категории"),
                        "icon": "category",
                        "link": reverse_lazy("admin:products_productcategory_changelist"),
                    },
                    {
                        "title": _("Бренды"),
                        "icon": "branding_watermark",
                        "link": reverse_lazy("admin:products_brand_changelist"),
                    },
                    {
                        "title": _("Параметры"),
                        "icon": "tune",
                        "link": reverse_lazy("admin:products_productattribute_changelist"),
                    },
                ],
            },
            {
                "title": _("Контент"),
                "separator": True,
                "items": [
                    {
                        "title": _("Слайдер"),
                        "icon": "view_carousel",
                        "link": reverse_lazy("admin:slider_slideritem_changelist"),
                    },
                ],
            },
            {
                "title": _("Финансы"),
                "separator": True,
                "items": [
                    {
                        "title": _("Начисления бонусов"),
                        "icon": "savings",
                        "link": reverse_lazy("admin:bonuses_bonus_changelist"),
                    },
                    {
                        "title": _("Правила начисления"),
                        "icon": "rule",
                        "link": reverse_lazy("admin:bonuses_mlmrule_changelist"),
                    },
                    {
                        "title": _("Пороги карьерных статусов"),
                        "icon": "workspace_premium",
                        "link": reverse_lazy("admin:mlm_statusthreshold_changelist"),
                    },
                ],
            },
            {
                "title": _("Уведомления"),
                "separator": True,
                "items": [
                    {
                        "title": _("Уведомления"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:notifications_notification_changelist"),
                    },
                ],
            },
            {
                "title": _("Пользователи"),
                "separator": True,
                "items": [
                    {
                        "title": _("Клиенты"),
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                    },
                ],
            },
        ],
    },
    "STYLES": [
        "admin_theme/css/unfold-sidebar-hierarchy.css",
        "css/output.css",
        "admin_theme/css/shadcn-admin-bridge.css",
    ],
    "COLORS": {
        "primary": {
            "50": "oklch(98.2% 0.018 155)",
            "100": "oklch(95.3% 0.05 155)",
            "200": "oklch(90.5% 0.095 155)",
            "300": "oklch(84.0% 0.15 155)",
            "400": "oklch(74.0% 0.19 155)",
            "500": "oklch(65.0% 0.18 155)",
            "600": "oklch(56.0% 0.16 155)",
            "700": "oklch(47.0% 0.13 155)",
            "800": "oklch(39.0% 0.105 155)",
            "900": "oklch(32.0% 0.085 155)",
            "950": "oklch(23.0% 0.06 155)",
        },
    },
}


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",                                                                    
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
                                                                                       
            "sslmode": config("DB_SSLMODE", default="prefer"),
                                                                   
            "client_encoding": "UTF8",
        },
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

ADMIN_FRONTEND_STATIC_DIR = BASE_DIR.parent / "admin_frontend" / "static"
STATICFILES_DIRS = [
    ADMIN_FRONTEND_STATIC_DIR,
] if ADMIN_FRONTEND_STATIC_DIR.exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
    "SIGNING_KEY": config("JWT_SIGNING_KEY"),                                                      
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
}

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

SMS_LOGIN = config("SMS_LOGIN", default="")
SMS_HASH = config("SMS_HASH", default="")
SMS_SENDER = config("SMS_SENDER", default="")
SMS_SERVER = config("SMS_SERVER", default="https://api.osonsms.com/sendsms_v1.php")
SMS_TIMEOUT_SEC = config("SMS_TIMEOUT_SEC", cast=float, default=10.0)

OTP_CODE_TTL_MINUTES = config("OTP_CODE_TTL_MINUTES", cast=int, default=5)
OTP_MAX_ATTEMPTS = config("OTP_MAX_ATTEMPTS", cast=int, default=5)
OTP_VERIFIED_TTL_MINUTES = config("OTP_VERIFIED_TTL_MINUTES", cast=int, default=30)

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default="redis://redis:6379/1")
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_TIME_LIMIT = config("CELERY_TASK_TIME_LIMIT", cast=int, default=300)
CELERY_TASK_SOFT_TIME_LIMIT = config("CELERY_TASK_SOFT_TIME_LIMIT", cast=int, default=240)
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": config("REDIS_CACHE_URL", default="redis://redis:6379/2"),
        "TIMEOUT": config("REDIS_CACHE_TIMEOUT", cast=int, default=300),                                    
        "OPTIONS": {
            "client_class": "django_redis.client.DefaultClient",
        },
    }
}

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

RESERVATION_TIMEOUT_MINUTES: int = config(
    "RESERVATION_TIMEOUT_MINUTES",
    cast=int,
    default=21600,                       
)

try:
    from celery.schedules import crontab              

    CELERY_BEAT_SCHEDULE = {
        "expire-stale-reservations": {
            "task": "reservations.expire_stale",
            "schedule": crontab(minute="*/5"),
            "options": {"expires": 240},                                          
        },
        "distribute-confirm-bonuses": {
            "task": "bonuses.distribute_and_confirm",
                                                                                
                                                                                
                                                    
                                                                              
            "schedule": crontab(hour="*/1"),                           
            "enabled": False,                                                 
        },
    }
except ImportError:
    pass
