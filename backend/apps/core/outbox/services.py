"""Outbox service layer — единственный API для emit'а cross-context событий.

[F: docs/ARCHITECTURE.md «Service-layer паттерн» строки 628-673]
[F: ADR-016]

Использование:

    from apps.core.outbox.services import publish_event

    def create_event(*, organizer_user_id, ...) -> EventDTO:
        with transaction.atomic():
            event = Event.objects.create(...)
            publish_event(
                event_type='EventPublished',
                aggregate_type='Event',
                aggregate_id=event.id,
                payload={'organizer_id': str(organizer_user_id), ...},
            )
        return EventDTO.from_orm(event)

Гарантия at-least-once: consumer ОБЯЗАН быть идемпотентен по `event.id`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from .models import OutboxEvent

if TYPE_CHECKING:
    pass


def publish_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict[str, Any],
) -> OutboxEvent:
    """Записать событие в outbox_event внутри текущей транзакции.

    Caller ОБЯЗАН вызывать внутри `with transaction.atomic():` — если транзакция
    откатывается, outbox запись тоже откатывается (atomic delivery promise).
    Если вызвать вне транзакции — Django auto-commit-ит, что нарушает atomic
    guarantee между state change и event emission.
    """
    return OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
