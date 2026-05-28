"""Production settings — Yandex Cloud Compute + Coolify (ADR-004).

[F: CLAUDE.md NON-NEGOTIABLE #11 — миграции через прямой PG]
[F: ARCHITECTURE.md «RLS Operational Constraints» #4 — act_admin BYPASSRLS role]

Три database alias:
    default     → act_app (RLS под policies)
    admin       → act_admin (BYPASSRLS, для Django Admin)
    migrations  → DATABASE_URL_DIRECT (минуя PgBouncer; CREATE INDEX CONCURRENTLY)

Coolify pre-deploy hook:
    PG_BOUNCER_HOST="" python manage.py migrate --database=migrations --noinput
"""

from __future__ import annotations

import os
import sys

from .base import *
from .base import _parse_db_url

DEBUG = False
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == [""]:
    raise RuntimeError("ALLOWED_HOSTS must be set in production (comma-separated).")

# HTTPS-only — terminate на Coolify reverse proxy + HSTS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31_536_000  # 1 год
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True

# ---------------------------------------------------------------------------
# Database aliases — three roles
# ---------------------------------------------------------------------------
_required_db_urls = {
    "default": os.environ.get("DATABASE_URL"),
    "admin": os.environ.get("DATABASE_URL_ADMIN"),
    "migrations": os.environ.get("DATABASE_URL_DIRECT"),
}
_missing = [k for k, v in _required_db_urls.items() if not v]
if _missing:
    raise RuntimeError(
        f"Missing required DATABASE_URL env vars for prod: {_missing}. See .env.example."
    )

DATABASES = {alias: _parse_db_url(url) for alias, url in _required_db_urls.items()}

# ---------------------------------------------------------------------------
# PII encryption — fail-fast if key not set.
# ---------------------------------------------------------------------------
if not os.environ.get("PII_HMAC_SECRET"):
    raise RuntimeError(
        "PII_HMAC_SECRET must be set in production (see .env.example: secrets.token_urlsafe(64))."
    )
if not os.environ.get("YANDEX_LOCKBOX_KEY_ID"):
    # Warning, не error — на Phase 1.1+ Lockbox ещё не готов.
    print(
        "WARN: YANDEX_LOCKBOX_KEY_ID не задан — PII encryption fallback на local key.",
        file=sys.stderr,
    )

# ---------------------------------------------------------------------------
# Sentry init (если DSN задан).
# ---------------------------------------------------------------------------
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False,  # NEVER send PII (NON-NEGOTIABLE #7)
        environment="production",
    )
