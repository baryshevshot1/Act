"""Base Django settings — общие для dev/test/prod.

[F: CLAUDE.md «Стек (frozen V1.2)» строки 47-69 + «NON-NEGOTIABLE» строки 130-141]
[F: docs/ARCHITECTURE.md § Backend, § Database, § Identity & Auth]

Layered pattern:
    base.py  →  dev.py / test.py / prod.py
Each child overrides DEBUG, DATABASES, ALLOWED_HOSTS, etc. но НЕ INSTALLED_APPS
или MIDDLEWARE без чёткой причины.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# backend/act/settings/base.py → backend/

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    # Dev-fallback; production обязательно задаёт через env (см. prod.py validate).
    "django-insecure-dev-only-replace-via-env-secrets.token_urlsafe(50)",
)
DEBUG = False
ALLOWED_HOSTS: list[str] = []

# CSRF / cookies — secure defaults (overridden in dev.py).
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"  # [F: identity_auth/CLAUDE.md «Conventions»]
SESSION_COOKIE_SECURE = True  # overridden False в dev.py
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True  # overridden False в dev.py
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Argon2id default — самый сильный hasher Django 5.2.
# [F: identity_auth/CLAUDE.md «Password hashing: argon2id»]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # fallback
]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",  # ArrayField, JSONField, FTS — целевой backend PG 17
]

THIRD_PARTY_APPS = [
    "allauth",
    "allauth.account",
    "allauth.socialaccount",  # Telegram / VK ID / Yandex ID adapters — wired в W1
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    # core должен быть первым — содержит RLS middleware + outbox для остальных BC.
    "apps.core",
    # 16 bounded contexts (alphabetical, как в .importlinter).
    "apps.admin_console",
    "apps.analytics",
    "apps.contacts_sharing",
    "apps.discovery",
    "apps.events",
    "apps.groups",
    "apps.identity_auth",
    "apps.localization",
    "apps.moderation",
    "apps.notifications",
    "apps.ratings",
    "apps.recommendations",
    "apps.recurrence_engine",
    "apps.rsvp",
    "apps.user_profile",
    "apps.verification",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Custom auth user model — ОБЯЗАТЕЛЬНО до первой миграции.
# [F: identity_auth/CLAUDE.md «Entities» — User имеет UUIDv7 PK + encrypted PII fields]
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "identity_auth.User"

# django-allauth — Telegram OIDC primary, magic-link fallback (NN #6: POST only).
# Реальный TelegramAdapter — W1 sprint, ~100 строк, отдельный PR.
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# ---------------------------------------------------------------------------
# Middleware — ORDER MATTERS.
# RLSContextMiddleware ДОЛЖЕН быть после AuthenticationMiddleware
# (нужен request.user.id) и обернуть весь handler в transaction.atomic()
# (см. ADR-006 + NON-NEGOTIABLE #11).
# CSP — после SecurityMiddleware, чтобы заголовки склеились корректно.
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # allauth account middleware
    "allauth.account.middleware.AccountMiddleware",
    # Act-specific:
    "apps.core.rls.middleware.RLSContextMiddleware",
    "apps.core.middleware.csp.CSPMiddleware",
]

ROOT_URLCONF = "act.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "act.wsgi.application"
ASGI_APPLICATION = "act.asgi.application"


# ---------------------------------------------------------------------------
# Database — overridden в dev.py / test.py / prod.py
# Production использует ТРИ alias-а:
#   default     → act_app (без BYPASSRLS, подчиняется RLS)
#   admin       → act_admin (с BYPASSRLS, для Django Admin) — RLS Operational Constraint #4
#   migrations  → DATABASE_URL_DIRECT (минуя PgBouncer) — RLS Operational Constraint #6
# ---------------------------------------------------------------------------
def _parse_db_url(url: str) -> dict[str, object]:
    """Минимальный парсер DATABASE_URL без dj-database-url (не в pyproject.toml).

    Поддерживает только `postgres://user:pass@host:port/dbname` и `sqlite:///path`.
    """
    parsed = urlparse(url)
    if parsed.scheme.startswith("sqlite"):
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": parsed.path.lstrip("/") or ":memory:",
        }
    if parsed.scheme.startswith(("postgres", "postgresql")):
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/"),
            "USER": parsed.username or "",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or ""),
        }
    raise ValueError(f"Unsupported DATABASE_URL scheme: {parsed.scheme!r}")


DATABASE_URL = os.environ.get("DATABASE_URL", "")
DATABASES: dict[str, dict[str, object]] = {}
if DATABASE_URL:
    DATABASES["default"] = _parse_db_url(DATABASE_URL)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Internationalization — RU default; EN — фоллбэк для wedge-расширения.
# [F: CLAUDE.md «Конвенции кода» + docs/ARCHITECTURE.md § Localization]
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Russian"),
    ("en", "English"),
]
TIME_ZONE = os.environ.get("TIME_ZONE", "Europe/Moscow")
USE_I18N = True
USE_TZ = True  # TIMESTAMPTZ в БД, UTC внутри
LOCALE_PATHS = [BASE_DIR / "locale"]

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# PII Encryption — django-cryptography + Yandex Lockbox в prod (ADR-014).
# Dev: ephemeral key из env; production обязан валидировать наличие ключа.
# ---------------------------------------------------------------------------
PII_HMAC_SECRET = os.environ.get(
    "PII_HMAC_SECRET",
    "dev-only-replace-via-env-secrets.token_urlsafe(64)-not-for-production",
)
YANDEX_LOCKBOX_KEY_ID = os.environ.get("YANDEX_LOCKBOX_KEY_ID", "")

# ---------------------------------------------------------------------------
# Email — UniSender или SendPulse в prod; в dev — console backend.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "no-reply@act.app")

# ---------------------------------------------------------------------------
# CORS — Next.js frontend локально на 3000.
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# OpenAPI / DRF — для typegen в Next.js (W1+).
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Act API",
    "DESCRIPTION": "Host-first платформа для совместных мероприятий (modular monolith).",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ---------------------------------------------------------------------------
# Sentry — placeholder; реальный init в prod.py при наличии SENTRY_DSN.
# ---------------------------------------------------------------------------
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
