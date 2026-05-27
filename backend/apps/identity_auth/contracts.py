"""Public DTOs — cross-context API.

[F: backend/apps/identity_auth/CLAUDE.md «Cross-context dependencies»]
[F: import-linter CONTRACT 1 + others — все other BC видят identity_auth
ТОЛЬКО через contracts.*]

dataclasses используем потому что pydantic не в pyproject.toml — добавление
требует ADR update. dataclasses покрывают DTO use case (immutable, typed,
JSON-serializable через `asdict`).

ВАЖНО: ни одно поле здесь НЕ должно содержать plain PII.
Допустимо: id, hash, status, telegram_id (публичный), locale, country_code.
Запрещено: primary_email_encrypted, phone_e164_encrypted, password.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class UserStatusContract(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    BANNED = "banned"
    DELETED = "deleted"


class ConsentPurposeContract(str, Enum):
    CORE_PROCESSING = "core_processing"
    MARKETING = "marketing"
    CONTACT_SHARING = "contact_sharing"
    CROSS_BORDER_TRANSFER = "cross_border_transfer"
    COOKIES_ESSENTIAL = "cookies_essential"
    COOKIES_ANALYTICS = "cookies_analytics"
    COOKIES_MARKETING = "cookies_marketing"


@dataclass(frozen=True, slots=True)
class UserContract:
    """Public user representation — no PII, only identifiers."""

    id: UUID
    primary_email_hash: str         # HMAC, не plain
    telegram_id: str | None
    locale: str
    country_code: str
    city_id: UUID | None
    status: UserStatusContract
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SessionContract:
    id: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ConsentContract:
    id: UUID
    user_id: UUID
    purpose: ConsentPurposeContract
    granted_at: datetime
    withdrawn_at: datetime | None


@dataclass(frozen=True, slots=True)
class RequestMeta:
    """Метаданные запроса для audit / rate-limit / anti-fraud."""

    ip_address: str
    user_agent: str
    locale: str = "ru"
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MagicLinkContract:
    """Result контракт для request_magic_link — НЕ содержит raw token."""

    id: UUID
    user_id: UUID
    email_hash_target: str
    expires_at: datetime
