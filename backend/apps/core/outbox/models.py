"""Transactional Outbox table.

[F: docs/ARCHITECTURE.md «Outbox (cross-cutting infrastructure)» строки 589-713]
[F: ADR-016]

RLS: НЕ применяется — infrastructure-таблица. Доступ только через act_app
service-роль. user-attributable данные в payload должны быть encrypted.

PK — UUIDv7 (write-heavy таблица, time-ordered insert). На Phase 1.4 используем
UUIDv4 placeholder; pg_uuidv7 extension придёт в Phase 1.4.bis (см. ADR-006).
"""
from __future__ import annotations

import uuid

from django.core.validators import MinValueValidator
from django.db import models


class OutboxEvent(models.Model):
    """Cross-context событие, ждущее доставки subscribers через Procrastinate."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        # TODO Phase 1.4.bis: switch default to uuidv7() via pg_uuidv7 extension.
        editable=False,
    )
    event_type = models.CharField(
        max_length=128,
        help_text="'RSVPCreated' | 'EventPublished' | 'ContactShareGranted' | ...",
    )
    aggregate_type = models.CharField(
        max_length=64,
        help_text="'Event' | 'User' | 'Group' | 'Series' | 'Notification'",
    )
    aggregate_id = models.UUIDField()
    payload = models.JSONField(
        help_text="Денормализованный snapshot — consumers не должны JOIN-ить.",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(
        null=True, blank=True,
        help_text="NULL = pending; NOT NULL = доставлено всем subscribers.",
    )
    error_count = models.IntegerField(
        default=0, validators=[MinValueValidator(0)],
        help_text="При >= 10 — alert в Sentry, manual review (poison message).",
    )
    last_error = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "outbox_event"
        indexes = [
            # Hot path — worker poll only pending events (~5s intervals).
            # Partial index добавим в 1.4.bis миграции:
            #   CREATE INDEX outbox_event_pending_idx
            #     ON outbox_event (created_at) WHERE published_at IS NULL;
            models.Index(fields=["created_at"], name="outbox_created_idx"),
            models.Index(fields=["published_at"], name="outbox_published_idx"),
            models.Index(
                fields=["aggregate_type", "aggregate_id"],
                name="outbox_aggregate_idx",
            ),
        ]
        verbose_name = "Outbox event"
        verbose_name_plural = "Outbox events"
