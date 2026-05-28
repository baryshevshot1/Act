"""Smoke tests для apps.core.crypto — ADR-014 revised.

Не требует БД — Fernet round-trip полностью в-памяти. Покрывает:
- EncryptedField round-trip (encrypt → decrypt = identity)
- Different tokens at every encrypt (Fernet random IV)
- Empty string passthrough (НЕ encrypted — для compat с nullable TextField)
- generate_key() — valid Fernet key shape
- MultiFernet rotation — old token still decryptable after key prepend
"""

from __future__ import annotations

from cryptography.fernet import Fernet, MultiFernet
from django.test import override_settings

from apps.core.crypto import EncryptedField, generate_key, get_keyring


def test_round_trip_preserves_plaintext() -> None:
    """encrypt(decrypt(value)) == value для типичных PII strings."""
    field = EncryptedField()
    for plaintext in [
        "user@example.com",
        "+79161234567",
        "Иван Петров",  # Cyrillic
        "user+tag@домен.рф",  # IDN
        "x" * 1000,  # long string
    ]:
        token = field.get_db_prep_save(plaintext, connection=None)
        roundtripped = field.from_db_value(token, expression=None, connection=None)
        assert roundtripped == plaintext, f"round-trip failed для {plaintext!r}"


def test_empty_string_not_encrypted() -> None:
    """Empty string и None проходят насквозь — для compat с nullable TextField default=''."""
    field = EncryptedField()
    assert field.get_db_prep_save("", connection=None) == ""
    assert field.get_db_prep_save(None, connection=None) is None
    assert field.from_db_value("", expression=None, connection=None) == ""
    assert field.from_db_value(None, expression=None, connection=None) is None


def test_different_tokens_at_every_encrypt() -> None:
    """Fernet включает random IV — два encrypt одного plaintext дают разные tokens.

    Защита от deterministic-encryption inference (rainbow tables по encrypted PII).
    Поэтому exact-match lookup невозможен через encrypted поле — только через HMAC hash.
    """
    field = EncryptedField()
    t1 = field.get_db_prep_save("same value", connection=None)
    t2 = field.get_db_prep_save("same value", connection=None)
    assert t1 != t2, "Fernet tokens должны различаться (random IV)"


def test_generate_key_produces_valid_fernet_key() -> None:
    """generate_key() — drop-in для PII_ENCRYPTION_KEY env var."""
    key = generate_key()
    assert isinstance(key, str)
    # Smoke test — key реально используется для encrypt/decrypt.
    fernet = Fernet(key.encode())
    token = fernet.encrypt(b"smoke")
    assert fernet.decrypt(token) == b"smoke"


def test_multifernet_rotation_old_token_still_decryptable() -> None:
    """После prepend нового ключа старые tokens всё ещё decrypt'ятся.

    Это invariant rotation strategy — без него ротация требует full backfill
    перед удалением старого ключа.
    """
    old_key = Fernet.generate_key()
    new_key = Fernet.generate_key()

    # Token зашифрован старым ключом.
    old_token = Fernet(old_key).encrypt(b"historical data")

    # Keyring с newest-first ordering.
    keyring = MultiFernet([Fernet(new_key), Fernet(old_key)])

    # Старый token читается.
    assert keyring.decrypt(old_token) == b"historical data"

    # Новые writes используют новейший ключ.
    new_token = keyring.encrypt(b"fresh data")
    # Старый Fernet НЕ может расшифровать новый token (другой ключ).
    assert Fernet(new_key).decrypt(new_token) == b"fresh data"


def test_get_keyring_raises_without_config() -> None:
    """Fail-fast если ни PII_ENCRYPTION_KEY ни PII_ENCRYPTION_KEYRING не заданы."""
    # `get_keyring` lru-cached — clear перед override.
    get_keyring.cache_clear()
    with override_settings(PII_ENCRYPTION_KEY="", PII_ENCRYPTION_KEYRING=""):
        try:
            get_keyring()
        except Exception as exc:
            assert "PII encryption requires" in str(exc)
        else:
            raise AssertionError("Expected ImproperlyConfigured when keys missing")
    get_keyring.cache_clear()


def test_to_python_decrypts_fernet_token_strings() -> None:
    """to_python() распознаёт Fernet token (gAAAAA... prefix) и расшифровывает.

    Used при form/serialization deserialization paths.
    """
    field = EncryptedField()
    token = field.get_db_prep_save("hello", connection=None)
    assert token is not None and token.startswith("gAAAAA")
    assert field.to_python(token) == "hello"
    # Non-token strings проходят насквозь.
    assert field.to_python("plain text") == "plain text"
