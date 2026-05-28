# apps.core.crypto — Field-level PII encryption (ADR-014).
#
# Замена `django-cryptography-django5` (stale, last 2024-06; не support Django 5.2)
# на minimal-deps custom field built on PyCA `cryptography`.
# Decision: ADR-014 revised 2026-05-28 (research finding R6).
#
# Public API:
#   from apps.core.crypto import EncryptedField, get_keyring, generate_key
#
# Использование в models:
#   from apps.core.crypto import EncryptedField
#
#   class User(models.Model):
#       primary_email_encrypted = EncryptedField(blank=True, default="")
#
# Key management (production): master Fernet key из Yandex Lockbox через
# `settings.PII_ENCRYPTION_KEY` (one key) или `settings.PII_ENCRYPTION_KEYRING`
# (list для MultiFernet rotation). Подробнее — apps/core/crypto/keys.py.
from .fields import EncryptedField
from .keys import generate_key, get_keyring

__all__ = ["EncryptedField", "generate_key", "get_keyring"]
