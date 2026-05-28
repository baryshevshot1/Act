"""RSVP & Attendance — критичный wedge BC (JTBD-2 per-event confirmation).

[F: backend/apps/rsvp/CLAUDE.md «Entities»]
[F: docs/ARCHITECTURE.md § RSVP & Attendance]
[F: PDF V1.3 sec 20.4 (merge_guest_on_signup), sec 20.5 (RLS policies)]

Сущности:
    EventParticipant — RSVP залогиненного User
    GuestRSVP        — RSVP без аккаунта; сливается через merge_guest_on_signup
    WaitlistEntry    — очередь при capacity overflow; atomic promotion при cancel

RLS:
    EventParticipant — participant видит свои; organizer видит все по своему event
    GuestRSVP        — visible только organizer-у соответствующего event
    WaitlistEntry    — same pattern что EventParticipant
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.core.crypto import EncryptedField


class RSVPStatus(models.TextChoices):
    APPLIED = "applied", "Applied (pending organizer review)"
    CONFIRMED = "confirmed", "Confirmed"
    WAITLISTED = "waitlisted", "Waitlisted"
    DECLINED = "declined", "Declined"
    CHECKED_IN = "checked_in", "Checked in"
    NO_SHOW = "no_show", "No show"


class GuestStatus(models.TextChoices):
    PENDING = "pending", "Pending (email verify required)"
    GOING = "going", "Going"
    DECLINED = "declined", "Declined"


class ContactChannel(models.TextChoices):
    EMAIL = "email", "Email"
    TELEGRAM_HANDLE = "telegram_handle", "Telegram handle"
    PHONE = "phone", "Phone"


# ---------------------------------------------------------------------------
# EventParticipant — signed-in RSVP
# ---------------------------------------------------------------------------
class EventParticipant(models.Model):
    """RSVP залогиненного User.

    UNIQUE (event_id, user_id) — один user не может RSVP-нуться дважды на event.
    Per-instance RSVP: для recurring series каждый Event требует отдельного
    confirmation (PDF V1.1 UX differentiator).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "events.Event",  # string ref (NN cross-context)
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        "identity_auth.User",  # string ref
        on_delete=models.CASCADE,
        related_name="rsvps",
    )
    status = models.CharField(
        max_length=16,
        choices=RSVPStatus.choices,
        default=RSVPStatus.APPLIED,
    )

    # Note для organizer (опционально, ~280 chars).
    note = models.CharField(max_length=280, blank=True, default="")

    applied_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    # Audit-trail: если этот participant был создан через merge_guest_on_signup,
    # храним original GuestRSVP.id для compliance + UX («ваш guest RSVP подтверждён»).
    merged_from_guest_id = models.UUIDField(null=True, blank=True)

    class Meta:
        db_table = "rsvp_event_participant"
        constraints = [
            models.UniqueConstraint(
                fields=["event", "user"],
                name="participant_event_user_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"], name="participant_user_status_idx"),
            models.Index(fields=["event", "status"], name="participant_event_status_idx"),
        ]


# ---------------------------------------------------------------------------
# GuestRSVP — anonymous RSVP (email / Telegram / phone)
# ---------------------------------------------------------------------------
class GuestRSVP(models.Model):
    """RSVP без аккаунта; сливается при signup через merge_guest_on_signup.

    [F: rsvp/CLAUDE.md «Conventions: Encrypted PII lookup»]

    `contact_value_encrypted` — ENCRYPT_AT_REST через apps.core.crypto.EncryptedField
    (ADR-014 revised).
    `contact_value_hash` — HMAC-SHA256(PII_HMAC_SECRET, normalized_value)
    для exact lookup при merge.

    UNIQUE (event_id, channel, contact_value_hash) — нельзя guest-RSVP
    одним и тем же email дважды.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="guest_rsvps",
    )
    contact_channel = models.CharField(max_length=16, choices=ContactChannel.choices)
    contact_value_encrypted = EncryptedField(
        help_text="ENCRYPT_AT_REST. НЕ filter — используй hash.",
    )
    contact_value_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="HMAC-SHA256(secret, normalized). Phone — +E164 ДО hash.",
    )
    display_name = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(
        max_length=16,
        choices=GuestStatus.choices,
        default=GuestStatus.PENDING,
        help_text="'pending' для email до verify; 'going' immediate для telegram_handle.",
    )

    # Pointer на User после merge — для audit + idempotency повторных merge.
    merged_into_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Set by merge_guest_on_signup; non-null → этот guest уже claimed.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set при email verify (через magic-link).",
    )

    class Meta:
        db_table = "rsvp_guest_rsvp"
        constraints = [
            models.UniqueConstraint(
                fields=["event", "contact_channel", "contact_value_hash"],
                name="guest_event_channel_value_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["contact_channel", "contact_value_hash"],
                name="guest_channel_hash_idx",
                # Используется merge_guest_on_signup для O(log n) lookup
                # по всем pending guest-RSVP при signup.
            ),
            models.Index(fields=["event", "status"], name="guest_event_status_idx"),
        ]


# ---------------------------------------------------------------------------
# WaitlistEntry — очередь при capacity overflow
# ---------------------------------------------------------------------------
class WaitlistEntry(models.Model):
    """FIFO очередь при достижении Event.capacity.

    `position` обновляется atomically при removal (sequential renumber) —
    реальная impl в W6 через `transaction.atomic() + select_for_update()`.
    Promotion: при cancel участника → top waitlist confirms automatically
    (PDF V1.1 UX — «места освободились»).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.CASCADE,
        related_name="waitlist",
    )
    user = models.ForeignKey(
        "identity_auth.User",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
        help_text="NULL для guest waitlist (см. guest_rsvp_id).",
    )
    guest_rsvp = models.ForeignKey(
        "rsvp.GuestRSVP",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="waitlist_entries",
    )
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rsvp_waitlist_entry"
        constraints = [
            # Один из (user, guest_rsvp) должен быть задан, но не оба.
            models.CheckConstraint(
                condition=(
                    models.Q(user__isnull=False, guest_rsvp__isnull=True)
                    | models.Q(user__isnull=True, guest_rsvp__isnull=False)
                ),
                name="waitlist_user_xor_guest",
            ),
            models.UniqueConstraint(
                fields=["event", "user"],
                condition=models.Q(user__isnull=False),
                name="waitlist_event_user_uniq",
            ),
            models.UniqueConstraint(
                fields=["event", "guest_rsvp"],
                condition=models.Q(guest_rsvp__isnull=False),
                name="waitlist_event_guest_uniq",
            ),
            models.UniqueConstraint(
                fields=["event", "position"],
                name="waitlist_event_position_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["event", "position"], name="waitlist_event_pos_idx"),
        ]
