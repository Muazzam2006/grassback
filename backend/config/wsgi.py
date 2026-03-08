"""
WSGI config for Grassback.
"""
import os

from django.core.wsgi import get_wsgi_application

# C-4: was pointing to 'grass_mlm.settings' (old project name — does not exist).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

application = get_wsgi_application()
