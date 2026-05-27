# apps/events — Events + Recurrence Engine Context

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C Events context, включая Recurrence).
> Источники: `ARCHITECTURE.md` § Events context (Level C готов) + PDF V1.1 Recurrence Engine UX + RFC 5545.

## Context

Events — **core BC** wedge MVP (JTBD-2 «тренеры регулярных групп»). Owns: `Event`, `EventSeries`, `RecurrenceRule` (RFC 5545), `EXDate`, `RecurrenceOverride`, `EventCoverImage`. Recurrence Engine — sub-module внутри `apps/recurrence_engine/` (раздельный stub, исторически отдельный, но логически часть Events Level C). Statuses: `draft`, `published`, `full`, `cancelled`, `completed`.

## Entities (verbatim из `docs/ARCHITECTURE.md` § Events context)

| Entity | Description | RLS? | Key fields |
|---|---|---|---|
| `Event` | Один экземпляр встречи | ✓ | `id UUIDv7 PK`, `owner_id`, `series_id` (nullable FK), `recurrence_id TIMESTAMPTZ` (для override-match), `group_id` (nullable), `title`, `starts_at TIMESTAMPTZ`, `ends_at`, `city_id`, `status`, `capacity`, `format_tags[]`, `moderation_required`, `is_paid`, `price`, `currency` |
| `EventSeries` | Родитель recurring | ✓ | `id`, `organizer_user_id`, `rrule TEXT` (RFC 5545), `dtstart`, `until` (опц.), `template_event_data JSONB` |
| `EXDate` | Дата-исключение из серии | ✓ | `series_id`, `excluded_date TIMESTAMPTZ` |
| `RecurrenceOverride` | Изменение конкретного instance | ✓ | `series_id`, `recurrence_id`, `range ∈ {THISONLY, THISANDFUTURE}`, `override_fields JSONB` |
| `EventCoverImage` | Cover для OG-card | — (read-public) | `event_id`, `storage_key`, `width`, `height` |

## RFC 5545 essentials (verbatim из Level C)

- `RRULE` — правило (`FREQ=WEEKLY;BYDAY=TU,TH`).
- `EXDATE` — исключения (отдельная таблица, не inline в rrule).
- `RECURRENCE-ID` — id конкретного экземпляра при override.
- `RANGE=THISANDFUTURE` — изменение всех будущих instances → splittail серии (новая `EventSeries` от cutoff).

Полный workflow в skill `.claude/skills/recurrence-rrule/`.

## Conventions

- **RFC 5545 verbatim** — НЕ изобретать собственный синтаксис; ломает interop с iCalendar / Google / Apple Calendar (важно для V2 calendar sync).
- **Generation horizon** — Recurrence Engine генерирует ровно **21 день вперёд** через Procrastinate periodic-task (daily); старые instances удаляются после `EventCompleted` через retention (Wave 3 Data Retention Policies).
- **Idempotent generation** — `Event.objects.update_or_create(series_id, recurrence_id)` — критично; иначе ретраи task создают duplicates.
- **`btree_gist` extension** — exclusion constraint для overlap-проверки instances одной series.
- **`TIMESTAMPTZ`** для всех datetime; конвертация в локаль — в сервисах через `iana_timezone` из `localization_city` либо на фронте.
- **Owner-only writes** — только `organizer_user_id` может create/edit/cancel свой Event/Series. RLS обеспечивает (через skill `.claude/skills/write-rls-policy/`).
- **UUIDv7 PKs** [F: `CLAUDE.md` строка 104] — Events write-heavy; UUIDv7 для производительности (time-ordered insert).
- **Status transitions** — explicit FSM в `services.py`: `draft → published → (full | completed | cancelled)`. Без skip states.
- **`recurrence_id` vs `id`** — `recurrence_id` = оригинальный DTSTART (matching key для override); `id` = UUID конкретного Event. НЕ путать.

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `EventDTO`, `EventSeriesDTO`, `EventCardDTO` (для shareable cards с OG metadata), `EventStatus` enum.
- **Consumes:** `apps.identity_auth.contracts` (`UserContract` для owner validation), `apps.localization.contracts` (locale-aware fields, city resolution), `apps.groups.contracts` (опциональная привязка к Group).
- **Emits via Outbox (ADR-016):** `EventPublished`, `EventCancelled`, `EventCompleted`, `SeriesCreated`, `EventGeneratedFromSeries`, `EventOverridden`.
- **Subscribes (через `subscribers.py`):** `GroupArchived(group_id)` → soft-cancel future events в этой группе.

## Common pitfalls

- **НЕ inline `EXDATE` в RRULE field** — отдельная таблица `events_exdate` для audit + query-friendly.
- **НЕ генерировать instances > horizon** — periodic-task держит ровно 21 день; иначе table растёт linearly с временем.
- **НЕ обновлять `Event.starts_at` для override** без записи в `RecurrenceOverride` — теряется audit-trail.
- **НЕ использовать `prefetch_related` за пределами `services.py`** — размывает границы (NN convention).
- **НЕ exposing internal series matching logic** — `recurrence_id` нужен только в Event aggregate, не в публичном `EventDTO`.
- **НЕ забывать RLS** на `events_event`, `events_event_series`, `events_exdate`, `events_recurrence_override`. Owner-based policy через skill `write-rls-policy`.
- **НЕ публиковать `EventPublished`** через Django signal — только через Outbox (ADR-016, skill `outbox-event`).
- **НЕ забывать про i18n** — `Event.title` в основной таблице на default locale организатора; переводы — в `events_event_translation` (skill `add-translation`).
- **НЕ забывать `EventCompleted` triggering Ratings** — это outbox subscriber в `ratings`; не вызывать ratings.services напрямую.

## Каскады удаления

- `EventSeries DELETE` → cascade на `Event` (все instances) через `ON DELETE CASCADE`; cascade на `EXDate`, `RecurrenceOverride`.
- `Event DELETE` → cascade на `EventParticipant`, `GuestRSVP` (через FK в RSVP context).
- Soft-delete предпочтителен через `status='cancelled'`; hard `DELETE` только для admin spam cleanup.

## Skills relevant to this BC

- `recurrence-rrule` — создание Series, override, EXDATE, generation.
- `outbox-event` — публикация cross-context events.
- `write-rls-policy` — RLS на новых таблицах.
- `create-migration` — schema changes (expand-contract).
- `add-translation` — для `events_event_translation` user content.
