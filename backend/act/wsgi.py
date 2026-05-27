"""WSGI entry-point — gunicorn в production (Coolify spawns workers).

[F: docs/ARCHITECTURE.md «Hosting: Yandex Cloud Compute + Coolify»]
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "act.settings.prod")

application = get_wsgi_application()
