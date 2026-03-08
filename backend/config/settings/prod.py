from decouple import config

from .base import *                    

DEBUG = False

ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", cast=lambda v: [s.strip() for s in v.split(",") if s.strip()])

DATABASES["default"]["OPTIONS"]["sslmode"] = "require"                                     

                                                                             
                  
                                                                             

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", cast=bool, default=True)

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False                                                     

SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", cast=int, default=31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", cast=bool, default=True)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", cast=bool, default=True)

SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

                                                                             
                                                                                  
                                                                             

_csrf_raw = config("CSRF_TRUSTED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = [s.strip() for s in _csrf_raw.split(",") if s.strip()]

                                                                             
                                            
                                                                             

CORS_ALLOW_ALL_ORIGINS = False
_cors_raw = config("CORS_ALLOWED_ORIGINS", default="")
CORS_ALLOWED_ORIGINS = [s.strip() for s in _cors_raw.split(",") if s.strip()]

                                                                             
                
                                                                             

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"                                            

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"                                            

                                                                             
       
                                                                             

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=True)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@grass-mlm.com")

                                                                             
                   
                                                                             

LOGGING["handlers"]["console"]["formatter"] = "json"                                     
LOGGING["root"]["level"] = config("DJANGO_LOG_LEVEL", default="INFO")                                     
LOGGING["loggers"]["django.request"]["level"] = "WARNING"                                     
LOGGING["loggers"]["django.db.backends"]["level"] = config("DJANGO_DB_LOG_LEVEL", default="ERROR")                                     

                                                                             
                             
                                                                             

CELERY_TIMEZONE = TIME_ZONE                                            
CELERY_ENABLE_UTC = True
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_WORKER_MAX_TASKS_PER_CHILD = config("CELERY_WORKER_MAX_TASKS_PER_CHILD", cast=int, default=1000)
CELERY_WORKER_CONCURRENCY = config("CELERY_WORKER_CONCURRENCY", cast=int, default=4)