"""
ASGI config for Grassback.
"""
import os

from django.core.asgi import get_asgi_application

# C-4: was pointing to 'grass_mlm.settings' (old project name — does not exist).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_asgi_application()
