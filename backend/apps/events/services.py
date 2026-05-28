"""Events service layer.

[F: backend/apps/events/CLAUDE.md «Conventions» — explicit FSM, owner-only writes]
[F: docs/ARCHITECTURE.md § Events context]

W3 sprint реализует:
    - create_event / update_event / publish_event / cancel_event
    - create_series / pause_series / archive_series
    - apply_override / apply_exdate
    - generation-task helpers (вызываются из apps.recurrence_engine)

Phase 1.4 — только signatures для valid import-linter checks.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .contracts import EventDTO, EventSeriesDTO


# ---------------------------------------------------------------------------
# Standalone Event lifecycle
# ---------------------------------------------------------------------------
def create_event(
    *,
    owner_id: UUID,
    title: dict[str, str],
    starts_at: datetime,
    ends_at: datetime,
    city_id: UUID | None = None,
    capacity: int | None = None,
    format_tags: list[str] | None = None,
    is_paid: bool = False,
    price_kopecks: int | None = None,
) -> "EventDTO":
    """Create draft Event (owner only).

    Outbox: НЕ emit'ит EventPublished для draft.
    """
    raise NotImplementedError("W3 sprint — Events CRUD")


def publish_event(*, event_id: UUID, owner_id: UUID) -> "EventDTO":
    """FSM: draft → published. Emit EventPublished через outbox.

    Pre-conditions: event.owner_id == owner_id (RLS enforce); status == draft.
    """
    raise NotImplementedError("W3 sprint")


def cancel_event(*, event_id: UUID, owner_id: UUID, reason: str) -> "EventDTO":
    """FSM: published/full → cancelled.

    Outbox: EventCancelled → rsvp BC marks all participants 'declined' +
    notifications BC шлёт cancellation messages.
    """
    raise NotImplementedError("W3 sprint")


def complete_event(*, event_id: UUID) -> "EventDTO":
    """FSM: published/full → completed (вызывается scheduled job по ends_at).

    Outbox: EventCompleted → ratings BC создаёт rating windows для участников.
    """
    raise NotImplementedError("W3 sprint")


# ---------------------------------------------------------------------------
# Series lifecycle (RFC 5545)
# ---------------------------------------------------------------------------
def create_series(
    *,
    organizer_user_id: UUID,
    rrule: str,
    dtstart: datetime,
    template_event_data: dict[str, object],
    until: datetime | None = None,
) -> "EventSeriesDTO":
    """Create series; первый generation-batch создаётся отдельной task'ой."""
    raise NotImplementedError("W5 sprint — Series + Recurrence Engine")


def apply_exdate(*, series_id: UUID, owner_id: UUID, excluded_date: datetime) -> None:
    """Добавить EXDATE; existing matching Event помечается cancelled."""
    raise NotImplementedError("W5 sprint")


def apply_override(
    *,
    series_id: UUID,
    owner_id: UUID,
    recurrence_id: datetime,
    override_fields: dict[str, object],
    range_kind: str = "this_only",
) -> None:
    """RECURRENCE-ID override. Если range='this_and_future' — split series."""
    raise NotImplementedError("W5 sprint")


# ---------------------------------------------------------------------------
# Read-side (используется Discovery + RSVP + Notifications)
# ---------------------------------------------------------------------------
def get_event(*, event_id: UUID) -> "EventDTO | None":
    raise NotImplementedError("W3 sprint")


def list_events_for_discovery(
    *,
    city_id: UUID | None,
    from_date: datetime,
    to_date: datetime,
    format_tags: list[str] | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list["EventDTO"]:
    """Discovery feed query.

    select_related / prefetch_related — ТОЛЬКО здесь (NN convention).
    """
    raise NotImplementedError("W3 sprint")
