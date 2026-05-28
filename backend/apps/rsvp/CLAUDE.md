# apps/rsvp — RSVP & Attendance Context

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C RSVP & Attendance).
> Источники: `ARCHITECTURE.md` § RSVP & Attendance services + endpoints + RLS policies; PDF V1.3 sec 20.4 (`merge_guest_on_signup`); PDF V1.3 sec 20.5 (RLS guest_visible_to_owner).

## Context

RSVP & Attendance — критичный wedge BC (JTBD-2 per-event RSVP-подтверждение, главный UX-differentiator vs Luma/Meetup). Owns: `EventParticipant` (signed-in RSVP), `GuestRSVP` (anonymous RSVP), `WaitlistEntry`. Statuses: `applied`, `confirmed`, `waitlist`, `declined`, `checked_in`, `no_show`.

## Entities (verbatim из `docs/ARCHITECTURE.md` § RSVP)

| Entity | Description | RLS? | Key fields |
|---|---|---|---|
| `EventParticipant` | RSVP залогиненного User | ✓ | `id UUIDv7 PK`, `event_id`, `user_id`, `status`, `applied_at`, `confirmed_at`, `checked_in_at`, `merged_from_guest_id` (nullable, audit) |
| `GuestRSVP` | RSVP без аккаунта | ✓ | `id`, `event_id`, `channel ∈ {email, telegram_handle, phone}`, `value` (encrypted), `value_hash` (HMAC), `display_name`, `status`, `merged_into_user_id` (nullable) |
| `WaitlistEntry` | Очередь когда `capacity` достигнут | ✓ | `event_id`, `user_id_or_guest_id`, `position`, `created_at` |

## Service signatures (verbatim из Level C)

```python
def rsvp_signed_in(*, user_id: UUID, event_id: UUID, note: str | None) -> ParticipantDTO: ...

def rsvp_as_guest(*, event_id: UUID, contact_channel: str, contact_value: str,
                  display_name: str, request_meta: RequestMeta) -> GuestRSVPDTO:
    """
    Creates GuestRSVP in 'pending' if channel='email' (sends verify mail);
    immediate 'going' if channel='telegram_handle'.
    Enforces UNIQUE (event_id, channel, value_hash).
    """

def merge_guest_on_signup(*, user_id: UUID, contact_channel: str, contact_value: str) -> int:
    """
    Called from identity_auth.signup_with_telegram_oidc / verify_magic_link
    AFTER the contact channel is confirmed (verify NOT before).
    """
```

## Conventions

- **Per-instance RSVP** — каждый Event в Series требует **отдельного** `EventParticipant` подтверждения. Никаких «auto-confirm всей series». Это главный UX-differentiator (PDF V1.1).
- **Guest channel verification** — `GuestRSVP(channel='email')` стартует в `pending` пока user не verify через magic-link (skill `auth-flow`). `channel='telegram_handle'` immediately `going` (Telegram сам подтверждает handle).
- **Encrypted PII lookup** — `GuestRSVP.value` шифруется через `apps.core.crypto.EncryptedField` (ADR-014 revised — PyCA Fernet); exact-match через `value_hash` HMAC-SHA256(`PII_HMAC_SECRET`, normalized_value). Phone — normalize до `+E164` ДО hash.
- **UNIQUE constraint** — `(event_id, channel, value_hash)` для guest; `(event_id, user_id)` для participant.
- **Merge invariant (PDF V1.3 sec 20.4)** — `merge_guest_on_signup` ТОЛЬКО после verify контакт-канала. Без verify = impersonation risk.
- **Idempotent merge** — `EventParticipant.objects.get_or_create()` + повторный вызов возвращает 0 merged.
- **Capacity gate** — service-level check ДО `EventParticipant.create()`; при overflow → `WaitlistEntry`; promotion из waitlist при cancel — atomic transaction + ordered by `position ASC`.
- **Owner visibility** — организатор Event видит всех своих participants + guests; participant видит только свои записи. RLS via `participant_visibility` policy.

## RLS policies (verbatim из Level C)

```sql
-- EventParticipant: participant видит свои; organizer видит все по своему event
CREATE POLICY participant_visibility ON rsvp_event_participant FOR SELECT
USING (
    user_id = (select current_setting('app.current_user_id'))::uuid
    OR event_id IN (
        SELECT id FROM events_event
        WHERE owner_id = (select current_setting('app.current_user_id'))::uuid
    )
);

-- GuestRSVP: видим только organizer-у соответствующего event-а
CREATE POLICY guest_visible_to_owner ON rsvp_guest_rsvp FOR SELECT
USING (event_id IN (SELECT id FROM events_event WHERE owner_id = ...));
```

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `ParticipantDTO`, `GuestRSVPDTO`, `RSVPStatus` enum, `merge_guest_on_signup` (callable contract).
- **Consumes:** `apps.identity_auth.contracts` (`UserContract` для signup-merge), `apps.events.contracts` (`EventDTO` для capacity / owner check), `apps.contacts_sharing.contracts` (для bilateral channel resolve после check-in).
- **Emits via Outbox (ADR-016):** `RSVPCreated`, `RSVPConfirmed`, `GuestRSVPCreated`, `GuestRSVPMerged`, `ParticipantCheckedIn`, `ParticipantNoShow`.
- **Subscribes:** `EventCancelled(event_id)` → mark all participants `declined`; `EventCompleted(event_id)` → trigger Ratings windows (via Outbox в Ratings BC).

## Common pitfalls

- **НЕ merge без verify** — kto угодно мог guest-RSVP-нуться с чужим email; merge ТОЛЬКО после verify (NN #6 magic-link POST).
- **НЕ `.filter(value=...)`** напрямую — value зашифрован (ADR-014); используй `value_hash` для exact lookup.
- **НЕ забывать phone normalization** — `+7 (495) 123-45-67` и `+74951234567` должны hash-нуться одинаково. Normalize до `+E164` ДО HMAC.
- **НЕ забывать idempotency** в merge — `get_or_create` + повторный вызов = 0 (для retry safety при partial commit).
- **НЕ возвращать `GuestRSVP.value` plain** в API responses — только masked (`***@example.com`).
- **НЕ публиковать `GuestRSVPMerged`** если ничего не merged — noise в outbox.
- **НЕ забывать `merged_from_guest_id`** на `EventParticipant` при merge — audit trail для compliance.
- **НЕ забывать audit log** если merge через `act_admin` BYPASSRLS — write в `audit_log_pii_access` с `purpose='rsvp_merge_on_signup'`.
- **НЕ использовать UUIDv7 для guest_rsvp.value_hash** — это HMAC, не UUID.
- **НЕ забывать capacity check** ДО create participant — иначе race overflow.
- **НЕ забывать waitlist promotion** на `EventParticipant.delete` (cancel) — atomic в той же транзакции.

## Skills relevant to this BC

- `guest-rsvp-merge` — полный workflow `merge_guest_on_signup`.
- `outbox-event` — для RSVPConfirmed / ParticipantCheckedIn cross-context events.
- `write-rls-policy` — RLS policies (participant_visibility + guest_visible_to_owner).
- `create-migration` — schema changes (expand-contract; добавление status, fields).
- `auth-flow` — для signup-side вызова merge_guest_on_signup.
