---
name: guest-rsvp-merge
description: Merges anonymous GuestRSVP records into authenticated EventParticipant when the guest signs up. Use when implementing signup flow in identity_auth, when user says "merge guest", "claim RSVP", "guest signup conversion", "GuestRSVP", or when handling Telegram OIDC / magic-link verification that needs to convert prior guest RSVPs. Pattern from PDF V1.3 sec 20.4.
allowed-tools: [Read, Write, Edit]
---

# Merge GuestRSVP into EventParticipant on Signup

> **RSVP & Attendance context** (Level C готов) [F: `docs/ARCHITECTURE.md` § RSVP & Attendance services + endpoints]. Anonymous guests RSVP-ятся через email / Telegram-handle / phone (`GuestRSVP`); при signup той же контакт-связки они должны автоматически конвертироваться в `EventParticipant` без потери RSVP-истории. Source: PDF V1.3 секция 20.4.

## When to use

- Реализация signup-flow в `identity_auth.services` (Telegram OIDC, magic-link verify, phone OTP confirm).
- Любой verification flow, который подтверждает контакт-канал (email / phone / telegram_handle) и должен retro-active claim существующие guest RSVPs.
- Тесты конверсии guest → participant.

## When NOT to use

- Обратный flow (delete user → restore guest) — это backward-compatibility hack, не нужен.
- Merge через UI «вручную claim» — guest сначала должен signup-нуться, потом merge автоматический.
- Если контакт-канал не подтверждён (email не verified) — merge ОПАСЕН (impersonation): kто угодно с тем же email мог RSVP-нуться раньше. **Merge только после verify.**

## Signature (verbatim из Level C)

```python
# apps/rsvp/services.py
def merge_guest_on_signup(*, user_id: UUID, contact_channel: str, contact_value: str) -> int:
    """
    Called from identity_auth.signup_with_telegram_oidc / verify_magic_link
    AFTER the contact channel is confirmed.

    Finds all GuestRSVP where (channel, value) match and merged_into_user_id IS NULL.
    For each: create EventParticipant(merged_from_guest_id), set GuestRSVP.merged_into_user_id.

    Returns number of merged.
    Idempotent: повторный вызов не создаёт duplicates.
    """
```

## Шаги

### 1. Вызов из identity_auth signup-flow

```python
# apps/identity_auth/services.py
from apps.rsvp.contracts import merge_guest_on_signup  # cross-context only через contracts

def signup_with_telegram_oidc(*, telegram_user_id: int, locale: str, ...) -> UserDTO:
    with transaction.atomic():
        user = User.objects.create(...)
        publish_event('UserRegistered', aggregate_id=user.id, payload={...})
        # Telegram OIDC → telegram_handle verified by Telegram itself
        merged_count = merge_guest_on_signup(
            user_id=user.id,
            contact_channel='telegram_handle',
            contact_value=user.telegram_username,
        )
        # Также merge по email, если у пользователя есть verified email
        if user.primary_email and user.primary_email_verified_at:
            merge_guest_on_signup(
                user_id=user.id,
                contact_channel='email',
                contact_value=user.primary_email,
            )
        return UserDTO.from_orm(user)
```

### 2. Implementation в rsvp.services

```python
# apps/rsvp/services.py
from uuid import UUID
from django.db import transaction
from apps.rsvp.models import GuestRSVP, EventParticipant
from apps.core.outbox.services import publish_event

def merge_guest_on_signup(*, user_id: UUID, contact_channel: str, contact_value: str) -> int:
    merged_count = 0
    with transaction.atomic():
        guests = GuestRSVP.objects.select_for_update().filter(
            channel=contact_channel,
            value=contact_value,  # encrypted lookup — используй hash column
            merged_into_user_id__isnull=True,
        )
        for guest in guests:
            # Idempotent: если participant уже есть, skip
            participant, created = EventParticipant.objects.get_or_create(
                event_id=guest.event_id,
                user_id=user_id,
                defaults={
                    'status': guest.status,
                    'merged_from_guest_id': guest.id,
                    'applied_at': guest.created_at,
                },
            )
            guest.merged_into_user_id = user_id
            guest.save(update_fields=['merged_into_user_id'])
            if created:
                merged_count += 1
                publish_event(
                    event_type='GuestRSVPMerged',
                    aggregate_type='EventParticipant',
                    aggregate_id=participant.id,
                    payload={
                        'user_id': str(user_id),
                        'event_id': str(guest.event_id),
                        'merged_from_guest_id': str(guest.id),
                    },
                )
    return merged_count
```

### 3. Encrypted lookup pattern (PII)

`GuestRSVP.value` хранит phone/email в `EncryptedValue` (ADR-014, `django-cryptography`). Прямой `.filter(value=...)` НЕ работает — нужен hashed lookup column:

```python
# models.py
class GuestRSVP(models.Model):
    channel = models.CharField(...)
    value = EncryptedTextField()  # actual encrypted PII
    value_hash = models.CharField(max_length=64, db_index=True)  # HMAC-SHA256
    # ...

# services.py: при создании
guest.value_hash = hmac_sha256(PII_HMAC_SECRET, contact_value.lower())

# при merge:
guests = GuestRSVP.objects.filter(
    channel=contact_channel,
    value_hash=hmac_sha256(PII_HMAC_SECRET, contact_value.lower()),
    merged_into_user_id__isnull=True,
)
```

## RLS interactions

- `rsvp_guest_rsvp` имеет policy `guest_visible_to_owner` (организатор event-а видит свои guest RSVPs).
- Service-call `merge_guest_on_signup` запускается из `identity_auth` flow → нужно временно `SET LOCAL app.current_user_id = <new user_id>` ИЛИ запускать через `act_admin` BYPASSRLS role (но тогда **обязателен audit log** — см. `audit_log_pii_access`).
- Recommended pattern: использовать `act_app` role + `SET LOCAL` на нового user (он imminently становится owner записи).

## Pitfalls

- **НЕ merge-ить до verify контакт-канала** — kто угодно мог guest-RSVP-нуться с чужим email. Merge ТОЛЬКО после magic-link verify / Telegram OIDC (Telegram сам подтверждает handle).
- **НЕ забывать idempotency** — если user уже EventParticipant (повторный signup, edge case): `get_or_create` не создаст duplicate, но `merged_count` не инкрементируется.
- **НЕ декодировать `value` raw** для compare — используй `value_hash` (HMAC) для exact-match lookup.
- **НЕ забывать про phone normalization** — `+7 (495) 123-45-67` и `+74951234567` должны hash-нуться одинаково. Normalize до `+E164` ДО hash.
- **НЕ публиковать `GuestRSVPMerged` событие если ничего не merged** — выше `if created:` важен (избежать noise в outbox).
- **НЕ забывать audit log** если merge через `act_admin` BYPASSRLS — write в `audit_log_pii_access` с `purpose='rsvp_merge_on_signup'`.

## Cross-context эффекты

- `GuestRSVPMerged` через Outbox → notifications subscriber может отправить welcome-letter с claim-confirmation; analytics subscribes для conversion-metrics tracking.
- Используй skill `.claude/skills/outbox-event/`.

## После реализации

1. Тест: создать `GuestRSVP(email='x@y.com')` → создать user с verified email `x@y.com` → проверить что `EventParticipant` создан + `GuestRSVP.merged_into_user_id` set.
2. Тест idempotency: вызвать `merge_guest_on_signup` дважды → second call возвращает 0.
3. Тест RLS: после merge, user видит свой `EventParticipant`, не видит `GuestRSVP` напрямую.
4. `lint-imports` — `apps.identity_auth` импортирует `apps.rsvp.contracts`, не `apps.rsvp.services`.
5. Записать в `docs/CHANGELOG.md` § Unreleased → Added.
