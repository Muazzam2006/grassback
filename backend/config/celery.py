"""
Celery application instance for Grassback.

This module must be imported in config/__init__.py so that Celery is
initialised before Django's app registry, enabling @shared_task decorators
to resolve correctly in all LOCAL_APPS.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("grassback")

# Read Celery configuration from Django settings; all keys must be prefixed
# with CELERY_ (e.g. CELERY_BROKER_URL).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all INSTALLED_APPS (looks for tasks.py in each app).
app.autodiscover_tasks()
