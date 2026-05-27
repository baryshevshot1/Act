---
name: outbox-event
description: Emits a cross-context event via the Transactional Outbox table (ADR-016). Use when one bounded context needs to notify another about a state change (EventPublished, RSVPConfirmed, NotificationDelivered, RatingPosted, EventCompleted), when user says "publish event", "emit event", "trigger downstream", "send to notifications". NEVER use Django signals for cross-context.
allowed-tools: [Read, Write, Edit]
---

# Emit Cross-Context Event via Transactional Outbox

> **ADR-016** [F: `ARCHITECTURE.md`]: Cross-context коммуникация ТОЛЬКО через `outbox_event` таблицу.
> Django signals — для intra-context concerns внутри одного `apps.<ctx>/`.

## When to use

- Mutation в одном BC должен триггерить side-effect в другом BC.
- Примеры: `EventPublished` → Notifications enqueues invitations; `RSVPConfirmed` → Notifications + Analytics; `EventCompleted` → Ratings создаёт evaluation windows.
- Cross-context dependency не симметричен (publisher не знает subscribers).

## When NOT to use

- Intra-context validation внутри одного BC — используй Django signals (`pre_save` / `post_save`) внутри `apps/<ctx>/signals.py`.
- Synchronous read запросы между BC — используй `apps.<ctx>.contracts` импорт (DTOs).
- Тяжёлые batch jobs (> 1k events one-shot) — отдельный Procrastinate task, не Outbox.

## Шаги

### 1. Эмиссия события в той же транзакции, что и mutation

В `apps/<ctx>/services.py`:

```python
# apps/events/services.py
from uuid import UUID
from django.db import transaction
from apps.core.outbox.services import publish_event
from apps.events.contracts import EventDTO
from apps.events.models import Event


def publish_event_to_audience(*, organizer_user_id: UUID, event_data: dict) -> EventDTO:
    with transaction.atomic():
        event = Event.objects.create(
            owner_id=organizer_user_id,
            **event_data,
            status='published',
        )

        # Outbox event в той же транзакции — at-least-once delivery (ADR-016).
        publish_event(
            event_type='EventPublished',
            aggregate_type='Event',
            aggregate_id=event.id,
            payload={
                'organizer_id': str(organizer_user_id),
                'city_id': str(event.city_id),
                'group_id': str(event.group_id) if event.group_id else None,
                'starts_at': event.starts_at.isoformat(),
            },
        )

        return EventDTO.from_orm(event)
```

### 2. Подписка subscriber в другом BC

В `apps/<other_bc>/subscribers.py`:

```python
# apps/notifications/subscribers.py
from uuid import UUID
from apps.core.outbox.dispatcher import subscribe
from apps.notifications.models import NotificationDelivery


@subscribe('EventPublished')
def notify_group_members(payload: dict, *, event_id: UUID) -> None:
    """
    At-least-once: consumer-side идемпотентность через event_id (ADR-016 dedupe key).
    """
    if NotificationDelivery.objects.filter(correlation_id=event_id).exists():
        return  # already processed

    # ... enqueue notifications через Procrastinate ...
```

### 3. Тест outbox emission

```python
import pytest
from apps.events import services as events_services
from apps.core.outbox.models import OutboxEvent


@pytest.mark.outbox
def test_event_publish_emits_outbox(db, user_factory):
    user = user_factory()
    event_dto = events_services.publish_event_to_audience(
        organizer_user_id=user.id,
        event_data={'title': 'Test', 'starts_at': '2026-06-01T18:00:00Z', 'city_id': city_id},
    )

    assert OutboxEvent.objects.filter(
        event_type='EventPublished',
        aggregate_id=event_dto.id,
    ).exists()
```

## Verbatim — event_type naming convention

- Формат: `<EntityAction>` в PascalCase (соответствует ADR-016 примеру).
- Примеры: `EventPublished`, `EventCancelled`, `RSVPCreated`, `RSVPConfirmed`, `GuestRSVPMerged`, `EventCompleted`, `RatingPosted`, `UserBanned`, `ConsentWithdrawn`.

## Idempotency rules (consumer-side, ADR-016)

- ВСЕГДА проверяй `event_id` в dedupe table перед обработкой.
- Если subscriber пишет в БД — wrap в `transaction.atomic()` с `select_for_update()` на dedupe row.
- Если subscriber вызывает внешний API (Telegram, UniSender) — храни provider response с `external_id` для retry-safety.

## Procrastinate periodic poll (cron */5s)

> Уже реализован в `apps/core/outbox/tasks.py` (см. ADR-016 verbatim в `ARCHITECTURE.md`).
> При ошибке подписчика `error_count` инкрементируется; при ≥ 10 — alert и ручное расследование.

## Pitfalls

- **НЕ использовать Django signals** для cross-context — отвергнуто в ADR-016 (loss риск при падении subscriber после commit основной транзакции).
- **НЕ забывать `transaction.atomic()`** — без неё нет гарантии что mutation и outbox commit'ятся вместе.
- **НЕ полагаться на порядок** доставки — Outbox даёт at-least-once, но НЕ ordered (если нужен порядок per aggregate, добавить `sequence_number` partition по `aggregate_id` — см. ADR-016 trigger пересмотра).
- **НЕ передавать большие payloads** (> 10 KB) — outbox table должна оставаться lean; используй `aggregate_id` для re-fetch consumer-side.
- **НЕ помещать сырые PII в payload** — `outbox_event.payload` доступен service-role; PII (телефон, email) шифруются на уровне source-таблицы (ADR-014), в payload идут только ссылки (`user_id`, `event_id`).
- **НЕ забывать retention** — outbox events удаляются через 30 дней (Wave 3 Data Retention Policies).
- **НЕ инициировать вторичную трансграничную передачу без consent** [F: NON-NEGOTIABLE #9] — если subscriber вызывает Telegram Bot API, обязательна проверка `ConsentRecord(purpose='cross_border_transfer')`. Иначе — fallback на SMS / email через UniSender (ADR-013).
