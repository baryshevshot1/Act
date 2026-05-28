"""RSVP service layer.

[F: backend/apps/rsvp/CLAUDE.md «Service signatures» — verbatim]
[F: docs/ARCHITECTURE.md § RSVP & Attendance]
[F: PDF V1.3 sec 20.4 — merge_guest_on_signup invariants]

W6 sprint реализует:
    - rsvp_signed_in / rsvp_as_guest (capacity gate + atomic waitlist promotion)
    - merge_guest_on_signup (вызывается из identity_auth после verify контакт-канала)
    - check_in / mark_no_show (organizer actions)
    - cancel_rsvp (с auto-promotion top waitlist)

Phase 1.4 — только signatures + invariant docstrings.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from apps.identity_auth.contracts import RequestMeta

    from .contracts import ContactChannelContract, GuestRSVPDTO, ParticipantDTO


# ---------------------------------------------------------------------------
# Signed-in RSVP
# ---------------------------------------------------------------------------
def rsvp_signed_in(
    *,
    user_id: UUID,
    event_id: UUID,
    note: str | None = None,
) -> "ParticipantDTO":
    """Create EventParticipant.

    Pre-conditions:
        - event.status in {published, full} (FSM)
        - user not already participating (UNIQUE constraint)
    Side effects (atomic):
        - capacity check: если >= capacity → waitlist (status=waitlisted)
                          иначе → applied (organizer-review) ИЛИ confirmed
                          (если moderation_required=False)
        - Outbox: RSVPCreated (RSVPConfirmed дополнительно если auto-confirm)
    """
    raise NotImplementedError("W6 sprint")


def rsvp_as_guest(
    *,
    event_id: UUID,
    contact_channel: "ContactChannelContract",
    contact_value: str,
    display_name: str,
    request_meta: "RequestMeta",
) -> "GuestRSVPDTO":
    """Create GuestRSVP.

    Behavior:
        - channel=email     → status='pending'; шлём verify mail с magic-link
        - channel=telegram_handle → status='going' immediate (Telegram сам валидирует)
        - channel=phone     → status='pending'; OTP через Telegram Gateway/SMS.ru

    UNIQUE (event_id, channel, value_hash) — повторный guest-RSVP тем же email
    на тот же event → idempotent (возвращаем существующий).
    Outbox: GuestRSVPCreated.
    """
    raise NotImplementedError("W6 sprint")


# ---------------------------------------------------------------------------
# Guest merge — ONLY called from identity_auth AFTER contact verify
# ---------------------------------------------------------------------------
def merge_guest_on_signup(
    *,
    user_id: UUID,
    contact_channel: "ContactChannelContract",
    contact_value: str,
) -> int:
    """Merge все pending GuestRSVP, совпадающие по (channel, value), в EventParticipant.

    [F: PDF V1.3 sec 20.4 + rsvp/CLAUDE.md «Merge invariant»]

    CRITICAL INVARIANT: вызывается ТОЛЬКО после verify контакт-канала
    (через magic-link POST или Telegram OIDC callback). Без verify =
    impersonation risk (кто-то RSVP-ался от чужого email — при сlaim
    через signup это даст ему accept).

    Idempotency:
        - find GuestRSVP WHERE channel + hash(value) match AND merged_into_user_id IS NULL
        - для каждого: get_or_create(EventParticipant) с merged_from_guest_id=guest.id
        - GuestRSVP.merged_into_user_id = user_id
        - повторный вызов на тех же данных = 0 merged (filter уже отсёк merged)

    Side effects:
        - Outbox: GuestRSVPMerged per merged guest (для analytics + notifications)
        - Outbox: НЕ emit'ить если 0 merged (избегаем noise)
        - Audit: если вызвано через act_admin BYPASSRLS → write в audit_log_pii_access

    Returns: number of merged guests.
    """
    raise NotImplementedError("W1 sprint (auth-side trigger) + W6 sprint (rsvp impl)")


# ---------------------------------------------------------------------------
# Organizer actions
# ---------------------------------------------------------------------------
def confirm_rsvp(*, event_id: UUID, organizer_user_id: UUID, participant_id: UUID) -> "ParticipantDTO":
    """Organizer confirms an applied RSVP. Outbox: RSVPConfirmed."""
    raise NotImplementedError("W6 sprint")


def cancel_rsvp(*, event_id: UUID, user_id: UUID) -> None:
    """User cancels their own RSVP. Auto-promote top waitlist (atomic)."""
    raise NotImplementedError("W6 sprint")


def check_in(*, event_id: UUID, organizer_user_id: UUID, participant_id: UUID) -> None:
    """Organizer check-in. Outbox: ParticipantCheckedIn → contributes к NSM (WAU)."""
    raise NotImplementedError("W6 sprint")


def mark_no_show(*, event_id: UUID, organizer_user_id: UUID, participant_id: UUID) -> None:
    """Organizer marks no-show post-event. Outbox: ParticipantNoShow."""
    raise NotImplementedError("W6 sprint")


# ---------------------------------------------------------------------------
# Read-side
# ---------------------------------------------------------------------------
def list_participants(
    *,
    event_id: UUID,
    requester_user_id: UUID,
) -> list["ParticipantDTO"]:
    """RLS обеспечивает visibility:
    - organizer видит всех (via participant_visibility policy)
    - participant видит себя + organizer-confirmed peers (зависит от Event settings)
    """
    raise NotImplementedError("W6 sprint")
