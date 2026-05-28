"""Test settings — pytest-django.

[F: pyproject.toml `[tool.pytest.ini_options]` DJANGO_SETTINGS_MODULE = "act.settings.test"]

Behavior:
- Если задано `DATABASE_URL_TEST` (CI с реальным PG17) — используется он.
- Иначе fallback на in-memory SQLite (быстрый local dev unit-run).

RLS-тесты (marker=rls) и smoke tests против реального PG17 требуют живой PG —
запускаются через `DATABASE_URL_TEST=postgres://... pytest`.
"""

from __future__ import annotations

import os

from .base import *
from .base import _parse_db_url

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# Database: реальный PG если env задан (CI), иначе in-memory SQLite (local).
_test_db_url = os.environ.get("DATABASE_URL_TEST", "")
if _test_db_url:
    DATABASES = {"default": _parse_db_url(_test_db_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }

# Email — locmem backend, проверка writes через mail.outbox.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Отключить argon2id в тестах для скорости.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Cookies без secure-флага для http://testserver.
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
