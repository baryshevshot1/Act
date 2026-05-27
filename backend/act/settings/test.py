"""Test settings — pytest-django.

[F: pyproject.toml `[tool.pytest.ini_options]` DJANGO_SETTINGS_MODULE = "act.settings.test"]

Использует in-memory SQLite для большинства тестов. RLS-тесты (marker=rls)
требуют живой PG (override через `--reuse-db` + DATABASE_URL_TEST).
"""
from __future__ import annotations

from .base import *  # noqa: F401,F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost"]

# In-memory SQLite для unit-тестов (быстро).
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
