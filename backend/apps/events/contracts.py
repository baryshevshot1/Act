"""Events public DTOs.

[F: backend/apps/events/CLAUDE.md «Exposes»]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID


class EventStatusContract(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    FULL = "full"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class EventDTO:
    """Read-model для Discovery / RSVP / Notifications.

    Сериализуется в JSON для API; consumers НЕ дёргают ORM напрямую.
    """

    id: UUID
    owner_id: UUID
    series_id: UUID | None
    title: dict[str, str]                # i18n {"ru": "...", "en": "..."}
    description: dict[str, str]
    country_code: str
    city_id: UUID | None
    location_text: str
    starts_at: datetime
    ends_at: datetime
    capacity: int | None
    status: EventStatusContract
    format_tags: list[str] = field(default_factory=list)
    moderation_required: bool = False
    is_paid: bool = False
    price_kopecks: int | None = None
    currency: str = "RUB"


@dataclass(frozen=True, slots=True)
class EventSeriesDTO:
    id: UUID
    organizer_user_id: UUID
    rrule: str
    dtstart: datetime
    until: datetime | None
    status: str


@dataclass(frozen=True, slots=True)
class EventCardDTO:
    """Минимальный DTO для shareable cards (OG metadata + cover).

    Используется в Discovery feed и в email/Telegram preview.
    """

    id: UUID
    title: dict[str, str]
    starts_at: datetime
    city_id: UUID | None
    cover_storage_key: str | None
    short_slug: str          # для /e/{slug} public route
