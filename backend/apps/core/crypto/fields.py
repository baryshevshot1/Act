"""EncryptedField — transparent Fernet encryption для Django models.

[F: ADR-014 — Field-level PII encryption (revised 2026-05-28)]
[F: docs/research/phase-1-prep-findings-2026-05-28.md R6]

Использование:
    from apps.core.crypto import EncryptedField

    class User(models.Model):
        primary_email_encrypted = EncryptedField(blank=True, default="")
        # exact-match lookup — отдельный hash field (HMAC-SHA256)
        primary_email_hash = models.CharField(max_length=64, db_index=True)

Storage:
- Encrypted TEXT в БД (Fernet token: URL-safe base64, ~150 байт на короткую строку).
- Plaintext в Python-side при .save() / .refresh_from_db() / queryset iteration.
- ВАЖНО: НЕЛЬЗЯ `.filter(field_encrypted='value')` — token меняется каждый encrypt
  (Fernet включает random IV). Только exact-match через separate `_hash` field.

Pitfalls:
- НЕ использовать как PK / unique constraint target — каждый INSERT даёт новый token.
- НЕ JSON-сериализовать без masking — `model_to_dict()` вернёт plaintext.
- При migration на новый ключ rotation — backfill task (Procrastinate) переписывает
  старые tokens; HMAC hash остаётся прежним.
"""

from __future__ import annotations

from typing import Any

from cryptography.fernet import InvalidToken
from django.db import models

from .keys import get_keyring


class EncryptedField(models.TextField):
    """Transparent Fernet encryption (PyCA cryptography).

    Inherits TextField — schema-wise это просто TEXT column. Encryption/decryption
    хуки навешаны на get_db_prep_save / from_db_value.

    Empty / NULL values НЕ шифруются — это позволяет nullable fields без
    «encrypted-empty» blob, и упрощает migration с TextField placeholder
    (existing empty rows остаются совместимыми).
    """

    description = "Transparently encrypted text field (Fernet AES-128-CBC + HMAC-SHA256)"

    def get_db_prep_save(self, value: Any, connection: Any) -> str | None:
        """Plaintext → Fernet token перед записью в БД."""
        if value is None or value == "":
            return value
        if not isinstance(value, str):
            value = str(value)
        return get_keyring().encrypt(value.encode("utf-8")).decode("ascii")

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> str | None:
        """Fernet token → plaintext при чтении из БД."""
        if value is None or value == "":
            return value
        try:
            return get_keyring().decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken:
            # Migration window: rows могут содержать plaintext (TextField → EncryptedField swap).
            # Возвращаем сырой value — backfill task должен encrypt'нуть его в production.
            # В W1 sprint после full data migration — поднять InvalidToken как fatal.
            return value

    def to_python(self, value: Any) -> str | None:
        """Form / deserialization. Decrypt если Fernet token, иначе passthrough."""
        if value is None:
            return value
        if not isinstance(value, str):
            return str(value)
        if value == "":
            return value
        # Heuristic: Fernet tokens начинаются с "gAAAAA" (version byte 0x80 + timestamp prefix).
        if value.startswith("gAAAAA"):
            try:
                return get_keyring().decrypt(value.encode("ascii")).decode("utf-8")
            except InvalidToken:
                pass
        return value
