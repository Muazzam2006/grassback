# Expose the Celery app so that `celery -A config worker` resolves correctly
# and Django management commands that use Celery can import the app.
from .celery import app as celery_app

__all__ = ("celery_app",)
