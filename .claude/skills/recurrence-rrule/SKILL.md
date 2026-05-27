---
name: recurrence-rrule
description: Creates an EventSeries with RFC 5545 RRULE/EXDATE/RECURRENCE-ID for the Events context. Use when a Series owner needs «event repeats weekly Tue+Thu», when user says "add recurrence", "create series", "weekly event", "RRULE", "override one occurrence", or when working with apps/events recurrence_engine. NEVER invent custom recurrence syntax — RFC 5545 verbatim.
allowed-tools: [Read, Write, Edit]
---

# RFC 5545 Recurrence (RRULE / EXDATE / RECURRENCE-ID)

> **Events context** (Level C готов) [F: `docs/ARCHITECTURE.md` § Events context]. `EventSeries` owns RRULE; Recurrence Engine генерирует `Event`-instances ежедневно на 21 день вперёд через Procrastinate periodic-task. **RFC 5545 verbatim** — НЕ изобретать собственный синтаксис.

## When to use

- Создание `EventSeries` с правилом повторения (`FREQ=WEEKLY;BYDAY=TU,TH` и т.п.).
- Override на конкретный instance: «эта неделя — другая локация» → `RecurrenceOverride` с `RECURRENCE-ID`.
- Исключение даты из серии (отпуск / каникулы) → `EXDATE`.
- Background-task генерации экземпляров (apps.recurrence_engine).
- THIS-AND-FUTURE-семантика (`RANGE=THISANDFUTURE`) — изменение всех будущих с конкретной даты.

## When NOT to use

- Single Event без серии — просто `Event(starts_at, ends_at)`, без `series_id`.
- Group без расписания — `Group` создаётся без `schedule_series_id`.
- Изменение **прошлого** instance — RFC 5545 рассматривает прошлые экземпляры как immutable; для исправления данных писать audit + manual UPDATE через `act_admin` роль.

## Сущности (verbatim из `docs/ARCHITECTURE.md` Level C Events)

| Сущность | Назначение |
|---|---|
| `EventSeries` | Родитель recurring; владеет `rrule TEXT NOT NULL` (формат RFC 5545), `dtstart TIMESTAMPTZ`, `until` (опц.), `organizer_user_id`, `template_event_data JSONB` |
| `Event` | Конкретный instance с `series_id FK` + `recurrence_id TIMESTAMPTZ` (= оригинальный DTSTART для override-match) |
| `EXDate` | Список дат-исключений: `series_id`, `excluded_date TIMESTAMPTZ` |
| `RecurrenceOverride` | Изменение конкретного instance: `series_id`, `recurrence_id`, `range ∈ {THISONLY, THISANDFUTURE}`, `override_fields JSONB` |

## Шаги для типичных операций

### 1. Создать серию

```python
# apps/events/services.py
from datetime import datetime
from uuid import UUID
from django.db import transaction
from apps.core.outbox.services import publish_event
from apps.events.models import EventSeries

def create_series(*, organizer_user_id: UUID, dtstart: datetime, rrule: str,
                  template: dict, until: datetime | None = None) -> EventSeries:
    """
    rrule example: 'FREQ=WEEKLY;BYDAY=TU,TH;INTERVAL=1'
    """
    with transaction.atomic():
        series = EventSeries.objects.create(
            organizer_user_id=organizer_user_id,
            dtstart=dtstart,
            rrule=rrule,
            until=until,
            template_event_data=template,
        )
        publish_event(
            event_type='SeriesCreated',
            aggregate_type='EventSeries',
            aggregate_id=series.id,
            payload={'organizer_id': str(organizer_user_id), 'rrule': rrule},
        )
        return series
```

### 2. Сгенерировать instances (Procrastinate periodic-task, daily +21 days ahead)

```python
# apps/recurrence_engine/tasks.py
from datetime import timedelta
from django.utils.timezone import now
from dateutil.rrule import rrulestr  # python-dateutil >=2.9
from apps.events.models import EventSeries, Event, EXDate

def generate_upcoming_instances(series_id):
    series = EventSeries.objects.select_for_update().get(id=series_id)
    horizon = now() + timedelta(days=21)
    rule = rrulestr(f"DTSTART:{series.dtstart:%Y%m%dT%H%M%SZ}\nRRULE:{series.rrule}")
    excluded = set(EXDate.objects.filter(series_id=series_id).values_list('excluded_date', flat=True))
    for occurrence_dt in rule.between(series.dtstart, horizon, inc=True):
        if occurrence_dt in excluded:
            continue
        Event.objects.update_or_create(
            series_id=series_id,
            recurrence_id=occurrence_dt,
            defaults={**series.template_event_data, 'starts_at': occurrence_dt},
        )
```

### 3. Override на один instance (RFC 5545 RECURRENCE-ID + RANGE=THISONLY)

```python
def override_single_instance(*, series_id: UUID, recurrence_id: datetime,
                             overrides: dict) -> Event:
    with transaction.atomic():
        event = Event.objects.select_for_update().get(
            series_id=series_id, recurrence_id=recurrence_id,
        )
        for field, value in overrides.items():
            setattr(event, field, value)
        event.save()
        # RecurrenceOverride хранит audit; restoreable
        RecurrenceOverride.objects.create(
            series_id=series_id, recurrence_id=recurrence_id,
            range='THISONLY', override_fields=overrides,
        )
        return event
```

### 4. THIS-AND-FUTURE (RFC 5545 RANGE=THISANDFUTURE)

При изменении всех будущих с конкретной даты — **разделить серию**: создать новую `EventSeries(dtstart=cutoff_date, ...)` + закрыть старую через `until=cutoff_date - 1 day`. Это упрощает RLS и поиск, и точно соответствует RFC 5545 implementation guidelines от Apple/Google Calendar.

## Verbatim RRULE examples

- Еженедельно вторник + четверг 19:00: `FREQ=WEEKLY;BYDAY=TU,TH`
- Каждое первое воскресенье месяца: `FREQ=MONTHLY;BYDAY=1SU`
- Каждые 2 недели: `FREQ=WEEKLY;INTERVAL=2`
- 10 повторений: `FREQ=WEEKLY;COUNT=10`
- До конкретной даты: `FREQ=WEEKLY;UNTIL=20260901T000000Z`

[F: RFC 5545 § 3.3.10 «Recurrence Rule»]

## Pitfalls

- **НЕ изобретать собственный синтаксис** — RFC 5545 verbatim. Любой свой DSL ломает interop с iCalendar / Google Calendar / Apple Calendar (важно для V2 calendar sync).
- **НЕ хранить generated instances больше horizon** — periodic-task держит ровно 21 день вперёд; старые удаляются после `EventCompleted` через retention rule (Wave 3 Data Retention Policies).
- **НЕ забывать idempotency** — `update_or_create(series_id, recurrence_id)` критичен; иначе при ретраях task создаёт дубликаты.
- **НЕ использовать naive datetime** — все datetimes в `TIMESTAMPTZ` UTC; конвертация в локальное время — в сервисах или фронте через `iana_timezone` из `localization_city`.
- **НЕ забывать exclusion constraint** через `btree_gist` (ADR-006) — overlap-проверка двух instances в одной series через GiST.
- **НЕ путать `recurrence_id` с `id`** — `recurrence_id` = оригинальный DTSTART (matching key для override); `id` = UUID конкретного Event.

## Cross-context эффекты

- `SeriesCreated` / `EventGeneratedFromSeries` / `EventOverridden` через Outbox (ADR-016) → notifications subscribes для уведомления `SeriesParticipant`s. Используй skill `.claude/skills/outbox-event/`.
- RLS на `events_event` и `events_event_series` — owner-only writes; через skill `.claude/skills/write-rls-policy/`.

## После реализации

1. Тест: создать серию `FREQ=WEEKLY;BYDAY=MO`, прогнать `generate_upcoming_instances`, убедиться что 3 instances создались (21 days / 7).
2. Тест override: применить `override_single_instance`, проверить что только один Event изменился, остальные intact.
3. Тест EXDATE: добавить `EXDate`, прогнать generation, убедиться что excluded дата пропущена.
4. `lint-imports` (CONTRACT 6 events) — не сломали ли cross-context boundaries.
5. Записать в `docs/CHANGELOG.md` § Unreleased → Added, если расширили схему.
