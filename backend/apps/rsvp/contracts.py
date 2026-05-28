"""RSVP public DTOs.

[F: backend/apps/rsvp/CLAUDE.md «Exposes»]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class RSVPStatusContract(StrEnum):
    APPLIED = "applied"
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    DECLINED = "declined"
    CHECKED_IN = "checked_in"
    NO_SHOW = "no_show"


class GuestStatusContract(StrEnum):
    PENDING = "pending"
    GOING = "going"
    DECLINED = "declined"


class ContactChannelContract(StrEnum):
    EMAIL = "email"
    TELEGRAM_HANDLE = "telegram_handle"
    PHONE = "phone"


@dataclass(frozen=True, slots=True)
class ParticipantDTO:
    id: UUID
    event_id: UUID
    user_id: UUID
    status: RSVPStatusContract
    applied_at: datetime
    confirmed_at: datetime | None
    checked_in_at: datetime | None


@dataclass(frozen=True, slots=True)
class GuestRSVPDTO:
    """Response для guest RSVP — `contact_value` НИКОГДА не возвращается plain.

    Caller получает masked view (например, `j***@example.com`).
    """

    id: UUID
    event_id: UUID
    contact_channel: ContactChannelContract
    contact_value_masked: str  # e.g. "j***@example.com"
    display_name: str
    status: GuestStatusContract
    created_at: datetime
    merged_into_user_id: UUID | None
