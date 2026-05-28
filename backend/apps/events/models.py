"""Events + Recurrence (core wedge BC).

[F: backend/apps/events/CLAUDE.md «Entities»]
[F: docs/ARCHITECTURE.md § Events context + RFC 5545]

Сущности (skeleton-уровень):
    Event              — экземпляр встречи (одна дата); UUIDv7 PK; status FSM
    EventSeries        — родитель recurring; RFC 5545 RRULE
    EXDate             — отдельная таблица исключений (НЕ inline в RRULE)
    RecurrenceOverride — изменение конкретного instance
    EventCoverImage    — cover для OG-card (read-public, без RLS)

RLS:
    Event, EventSeries, EXDate, RecurrenceOverride — owner-only writes,
    public read для published. policy создаётся в Phase 1.4.bis миграции.
    EventCoverImage — public (без RLS).
"""

from __future__ import annotations

import uuid

from django.contrib.postgres.fields import ArrayField
from django.db import models


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PUBLISHED = "published", "Published"
    FULL = "full", "Full (capacity reached)"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class EventSeriesStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    ARCHIVED = "archived", "Archived"


# ---------------------------------------------------------------------------
# EventSeries — родитель recurring (RFC 5545)
# ---------------------------------------------------------------------------
class EventSeries(models.Model):
    """Recurring series (RRULE / EXDATE / RECURRENCE-ID per RFC 5545).

    Generation Engine (apps.recurrence_engine) ежедневно создаёт ровно 21 день
    вперёд Event instances через Procrastinate periodic-task. Idempotent через
    `update_or_create(series_id, recurrence_id)`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer_user = models.ForeignKey(
        "identity_auth.User",  # string reference — НЕ direct import (NN cross-context)
        on_delete=models.CASCADE,
        related_name="organized_series",
    )
    # Group FK — апдейтится после groups BC получит Level C (Iteration 9).
    group_id = models.UUIDField(null=True, blank=True)

    # Шаблон Event на основе которого генерируются instances.
    # Включает title/description/capacity/location/format_tags etc.
    template_event_data = models.JSONField(
        default=dict,
        help_text="Snapshot Event-полей; instance наследует, override через RecurrenceOverride.",
    )

    # RFC 5545 RRULE — verbatim строка ("FREQ=WEEKLY;BYDAY=TU,TH").
    # НЕ изобретать собственный синтаксис (важно для V2 calendar sync).
    rrule = models.CharField(max_length=512)
    dtstart = models.DateTimeField()
    until = models.DateTimeField(null=True, blank=True)

    # Когда последний раз generation-task создавал instances.
    next_generation_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=16,
        choices=EventSeriesStatus.choices,
        default=EventSeriesStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events_event_series"
        indexes = [
            models.Index(
                fields=["organizer_user", "status"],
                name="series_organizer_status_idx",
            ),
            models.Index(
                fields=["next_generation_at"],
                name="series_next_gen_idx",
            ),
        ]


# ---------------------------------------------------------------------------
# Event — экземпляр встречи
# ---------------------------------------------------------------------------
class Event(models.Model):
    """Один экземпляр встречи (одна дата).

    Standalone OR generated from EventSeries (через recurrence_engine).
    UUIDv7 PK — write-heavy table (instance generation создаёт 21/день/series).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "identity_auth.User",  # NN cross-context: string FK
        on_delete=models.CASCADE,
        related_name="owned_events",
    )
    series = models.ForeignKey(
        "events.EventSeries",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="instances",
        help_text="NULL для standalone Event; FK на series при generation.",
    )
    # Matching key для RecurrenceOverride: оригинальный DTSTART instance.
    # Отдельно от `starts_at` потому что override может менять starts_at,
    # но recurrence_id остаётся matching key.
    recurrence_id = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Original DTSTART (RFC 5545 RECURRENCE-ID); matching key для overrides.",
    )
    group_id = models.UUIDField(null=True, blank=True)

    # i18n title/description — JSONB {"ru": "...", "en": "..."}.
    title = models.JSONField(
        default=dict,
        help_text='{"ru": "Йога утром", "en": "Morning yoga"}',
    )
    description = models.JSONField(default=dict, blank=True)

    # Geo / location.
    country_code = models.CharField(max_length=2, default="RU")
    city_id = models.UUIDField(null=True, blank=True)
    location_text = models.CharField(max_length=512, blank=True, default="")

    # Time — TIMESTAMPTZ, UTC.
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()

    # Capacity / status.
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="NULL = unlimited; otherwise WaitlistEntry при overflow.",
    )
    status = models.CharField(
        max_length=16,
        choices=EventStatus.choices,
        default=EventStatus.DRAFT,
    )

    # Формат и теги. ArrayField требует PG — на dev SQLite используется как
    # generic-list (Django принимает, но миграция в SQLite сломается; реальный
    # путь — PG в docker-compose).
    format_tags = ArrayField(
        models.CharField(max_length=32),
        default=list,
        blank=True,
        help_text="['online', 'in_person', 'hybrid', 'series', 'paid', ...]",
    )

    # Moderation / pricing.
    moderation_required = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    price_kopecks = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="ЮKassa ИП-only path (NN #3). NULL для free events.",
    )
    currency = models.CharField(max_length=3, default="RUB")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "events_event"
        indexes = [
            models.Index(fields=["owner", "status"], name="event_owner_status_idx"),
            models.Index(
                fields=["starts_at", "status"],
                name="event_starts_status_idx",
            ),
            models.Index(
                fields=["city_id", "starts_at"],
                name="event_city_starts_idx",
            ),
            models.Index(
                fields=["series", "recurrence_id"],
                name="event_series_recur_idx",
            ),
        ]
        constraints = [
            # Защита от дубликатов instance при retries generation-task.
            models.UniqueConstraint(
                fields=["series", "recurrence_id"],
                condition=models.Q(series__isnull=False),
                name="event_series_recur_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="event_ends_after_starts",
            ),
        ]


# ---------------------------------------------------------------------------
# EXDate — отдельная таблица исключений (НЕ inline в RRULE)
# ---------------------------------------------------------------------------
class EXDate(models.Model):
    """Дата-исключение из series (RFC 5545 EXDATE).

    [F: events/CLAUDE.md «НЕ inline EXDATE в RRULE field»]
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(
        "events.EventSeries",
        on_delete=models.CASCADE,
        related_name="exdates",
    )
    excluded_date = models.DateTimeField()
    reason = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events_exdate"
        constraints = [
            models.UniqueConstraint(
                fields=["series", "excluded_date"],
                name="exdate_series_date_uniq",
            ),
        ]


# ---------------------------------------------------------------------------
# RecurrenceOverride — изменение конкретного instance
# ---------------------------------------------------------------------------
class OverrideRange(models.TextChoices):
    THIS_ONLY = "this_only", "Только этот instance"
    THIS_AND_FUTURE = "this_and_future", "Этот и все будущие (split series)"


class RecurrenceOverride(models.Model):
    """RFC 5545 RECURRENCE-ID override.

    Если range='this_and_future' — generation-task создаёт новую EventSeries
    от cutoff date с применённым override (splittail pattern).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    series = models.ForeignKey(
        "events.EventSeries",
        on_delete=models.CASCADE,
        related_name="overrides",
    )
    recurrence_id = models.DateTimeField(
        help_text="Matching key — оригинальный DTSTART overrided instance.",
    )
    range_kind = models.CharField(
        max_length=16,
        choices=OverrideRange.choices,
        default=OverrideRange.THIS_ONLY,
    )
    override_fields = models.JSONField(
        default=dict,
        help_text="Только изменённые поля Event: {'starts_at': ..., 'title': ...}.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events_recurrence_override"
        constraints = [
            models.UniqueConstraint(
                fields=["series", "recurrence_id"],
                name="override_series_recur_uniq",
            ),
        ]


# ---------------------------------------------------------------------------
# EventCoverImage — read-public (без RLS)
# ---------------------------------------------------------------------------
class EventCoverImage(models.Model):
    """Cover для OG-card (V1.1 critical UX path: share-link → preview)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.OneToOneField(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="cover_image",
    )
    storage_key = models.CharField(
        max_length=512,
        help_text="Yandex Object Storage S3 key.",
    )
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    alt_text = models.JSONField(
        default=dict,
        blank=True,
        help_text='i18n: {"ru": "...", "en": "..."} for accessibility.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "events_cover_image"
