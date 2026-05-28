"""ASGI entry-point — reserved для async views (Django 5.2 async-capable).

На MVP — sync WSGI через gunicorn (см. wsgi.py). ASGI оставлен на случай
async-handlers для outbox webhook intake в Phase 4+.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "act.settings.prod")

application = get_asgi_application()
