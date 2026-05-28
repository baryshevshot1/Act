"""Development settings — local dev на машине фаундера / Codespace.

Fallback на SQLite если DATABASE_URL не задан — позволяет `manage.py check`
работать без живого PG. Реальный dev-flow требует `docker-compose up postgres`.
"""

from __future__ import annotations

from .base import *
from .base import BASE_DIR, DATABASES

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Не блокировать локальные HTTP-запросы.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# SQLite fallback — только для `manage.py check` без PG.
# Любые миграции / runtime — через docker-compose PG.
if not DATABASES:
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "dev.sqlite3",
    }

INTERNAL_IPS = ["127.0.0.1"]
