"""Fernet keyring management.

[F: ADR-014 — Field-level PII encryption]
[F: docs/research/phase-1-prep-findings-2026-05-28.md R6]

Threat model:
- Yandex admin / DBA dump compromise → master key в Lockbox (RU jurisdiction
  per ст. 18 152-ФЗ), не в БД и не в plain env.
- Application compromise → in-memory ключ (process memory) — accepted risk.
- Backup misconfiguration → encrypted-at-rest data в dump бесполезен без ключа.

Key rotation (ADR-014 1 год):
- `MultiFernet([Fernet(k_new), Fernet(k_old)])` — новые writes используют k_new,
  reads пробуют k_new затем k_old. Старые tokens остаются валидны.
- Re-encrypt backfill task (Procrastinate periodic) переписывает старые tokens
  на новый ключ → через rotation period k_old можно удалить.

Production:
- `PII_ENCRYPTION_KEYRING` — JSON list base64-encoded Fernet keys (newest first).
  Загружается из Yandex Lockbox на startup (apps/core/lockbox.py — W1 sprint).
- Dev / test:
- `PII_ENCRYPTION_KEY` — single key из env (deterministic across runs).
- Если ничего не задано — fail-fast при первом use (НЕ при import — иначе
  manage.py команды без crypto падают).
"""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def generate_key() -> str:
    """Generate a new Fernet key (URL-safe base64, 32 bytes random).

    CLI: python -c "from apps.core.crypto import generate_key; print(generate_key())"
    """
    return Fernet.generate_key().decode("ascii")


@lru_cache(maxsize=1)
def get_keyring() -> MultiFernet:
    """Lazy load Fernet keyring из settings.

    Cached на process lifetime — keys не ротируются in-flight. Restart pod
    после rotation.

    Order of resolution:
        1. `PII_ENCRYPTION_KEYRING` (list) — newest-first; supports rotation.
        2. `PII_ENCRYPTION_KEY` (str) — single key fallback (dev/test).
        3. Raise `ImproperlyConfigured`.
    """
    keyring_setting = getattr(settings, "PII_ENCRYPTION_KEYRING", None)
    single_key_setting = getattr(settings, "PII_ENCRYPTION_KEY", None)

    if keyring_setting:
        if isinstance(keyring_setting, str):
            keys = [k.strip() for k in keyring_setting.split(",") if k.strip()]
        else:
            keys = list(keyring_setting)
        if not keys:
            raise ImproperlyConfigured("PII_ENCRYPTION_KEYRING is empty.")
        return MultiFernet([Fernet(k.encode() if isinstance(k, str) else k) for k in keys])

    if single_key_setting:
        return MultiFernet([Fernet(single_key_setting.encode())])

    raise ImproperlyConfigured(
        "PII encryption requires PII_ENCRYPTION_KEY (single, dev/test) или "
        "PII_ENCRYPTION_KEYRING (list, production via Yandex Lockbox). "
        "Generate dev key: "
        "python -c 'from apps.core.crypto import generate_key; print(generate_key())'."
    )
