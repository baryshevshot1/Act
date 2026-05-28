# apps/contacts_sharing — Contacts Sharing Context (Bilateral Consent)

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C Contacts Sharing).
> Источники: `ARCHITECTURE.md` § Contacts Sharing (Level C готов) + ADR-014 (PII encryption) + 152-ФЗ ст. 9 ред. 156-ФЗ от 24.06.2025 (отдельный документ согласия).

## Context

Contacts Sharing — bilateral consent-based раскрытие каналов связи **между participants одного Event**. Owns: `UserContactChannel` (каналы пользователя), `ContactShare` (grants раскрытия). Главный UX: user может share Telegram/phone/email с другим участником **только при взаимности** (обе стороны grant-нули sharing для того же event). Не дублирует `ConsentRecord` из identity_auth — переиспользует с `purpose='contact_sharing'`.

## Entities (verbatim из `docs/ARCHITECTURE.md` § Contacts Sharing)

| Entity | Description | RLS? | Encrypted? |
|---|---|---|---|
| `UserContactChannel` | Канал связи пользователя | ✓ | `channel_value` (ADR-014) + `channel_value_hash` (HMAC для lookup) |
| `ContactShare` | Bilateral grant раскрытия на event | ✓ | — (только references) |

### Schema highlights

```sql
CREATE TABLE contacts_sharing_channel (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    channel_type VARCHAR(32) NOT NULL,
    -- 'telegram_handle' | 'phone' | 'email' | 'instagram' | 'custom_url'
    channel_value TEXT NOT NULL,        -- ENCRYPT_AT_REST (apps.core.crypto.EncryptedField)
    channel_value_hash VARCHAR(64) NOT NULL,  -- HMAC-SHA256(PII_HMAC_SECRET, value)
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (user_id, channel_type, channel_value_hash)
);

CREATE TABLE contacts_sharing_share (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    from_user_id UUID NOT NULL,
    to_user_id UUID NOT NULL,
    event_id UUID NOT NULL,
    channel_id UUID NOT NULL REFERENCES contacts_sharing_channel(id),
    consent_record_id UUID NOT NULL REFERENCES identity_auth_consent(id),
    -- 152-ФЗ ст. 9 ред. 156-ФЗ: явная ссылка на отдельный документ согласия
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ NULL,
    UNIQUE (from_user_id, to_user_id, event_id, channel_id),
    CHECK (from_user_id <> to_user_id)
);
```

## Conventions

- **Bilateral invariant** — `to_user_id` видит `channel_value` **только если** есть взаимный grant (`from = to_user_id`, `to = from_user_id`, same `event_id`, оба `revoked_at IS NULL`). Enforced на RLS-уровне (recipient policy).
- **Time-gating** — RLS подтверждает «грант существует и доступен взаимной стороне». Гейтинг по времени (показывать `channel_value` только в день Event / после `starts_at`) реализуется в **service-layer `resolve_shared_channel`**, не в RLS. Это разделение упрощает RLS expressions.
- **PII encryption (ADR-014 revised)** — `channel_value` шифруется через `apps.core.crypto.EncryptedField` (PyCA Fernet + MultiFernet keyring) + Yandex Lockbox master key. НЕ через `pgcrypto` (ADR-014 reject reason: key в plain в БД).
- **Exact-match lookup** — через `channel_value_hash` HMAC; нельзя `.filter(channel_value=)` напрямую.
- **Consent reference** — каждый `ContactShare` ссылается на `identity_auth_consent` row с `purpose='contact_sharing'` (NN #2 ст. 9 ред. 156-ФЗ).
- **UUIDv7 PKs** — share grants — write-heavy (каждый event triggers многих shares).
- **Revoke = soft-delete** — `revoked_at IS NOT NULL`, не DELETE. Для compliance audit и user UI «Мои отзывы grants».
- **No cascade сейчас** — `from_user_id DELETE` каскадирует `UserContactChannel` (ON DELETE CASCADE); `ContactShare` тоже cascade. Хочешь сохранять — переключи на `ON DELETE SET NULL`.

## RLS policies (verbatim из Level C)

```sql
-- Channels: user видит ТОЛЬКО свои
CREATE POLICY contacts_sharing_channel_owner ON contacts_sharing_channel
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);

-- Donor sees ВСЕ свои grants (UI «Мои общие контакты», включая revoked)
CREATE POLICY contacts_share_donor_select ON contacts_sharing_share FOR SELECT
USING (from_user_id = (select current_setting('app.current_user_id'))::uuid);

-- Recipient sees активные grants ТОЛЬКО при взаимности
CREATE POLICY contacts_share_recipient_select ON contacts_sharing_share FOR SELECT
USING (
    to_user_id = (select current_setting('app.current_user_id'))::uuid
    AND revoked_at IS NULL
    AND EXISTS (
        SELECT 1 FROM contacts_sharing_share rev
        WHERE rev.from_user_id = (select current_setting('app.current_user_id'))::uuid
          AND rev.to_user_id = contacts_sharing_share.from_user_id
          AND rev.event_id = contacts_sharing_share.event_id
          AND rev.revoked_at IS NULL
    )
);
```

Partial index `contacts_share_reverse_idx (from_user_id, to_user_id, event_id) WHERE revoked_at IS NULL` — обязателен под EXISTS-subquery.

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `ContactChannelDTO` (без `channel_value` raw — только masked), `ContactShareDTO`, `ContactChannelType` enum, `resolve_shared_channel(from_user_id, to_user_id, event_id) -> str | None`.
- **Consumes:** `apps.identity_auth.contracts` (`UserContract`, `ConsentContract`), `apps.events.contracts` (для event_id validation).
- **Emits via Outbox:** `ContactShareGranted`, `ContactShareRevoked`, `ChannelAdded`.
- **Subscribes:** `UserBanned(user_id)` → revoke all shares from/to user (compliance + safety).

## Common pitfalls

- **НЕ возвращать `channel_value` plain** в API — только masked (`@username` для telegram, `+7XXX***45-67` для phone, `***@example.com` для email).
- **НЕ использовать `pgcrypto`** для encryption (ADR-014 reject) — key в plain в БД; visible через `pg_stat_activity` для Yandex admin.
- **НЕ забывать `consent_record_id`** при create share — без него compliance audit fail (152-ФЗ ст. 9 ред. 156-ФЗ).
- **НЕ забывать `channel_value_hash`** при `add_contact_channel` — без него `merge_guest_on_signup` (skill `guest-rsvp-merge`) не сможет find user by phone/email.
- **НЕ нормализовать phone после hash** — нормализуй ДО (`+E164`).
- **НЕ time-gating в RLS** — оставь в service-layer `resolve_shared_channel`. RLS = «exists and accessible»; service = «когда показать».
- **НЕ забывать `audit_log_pii_access`** при любом чтении `channel_value` админом / модератором / service-ролью (Wave 3).
- **НЕ забывать про unique constraint** — `(user_id, channel_type, channel_value_hash)` позволяет несколько каналов одного типа (личный + рабочий phone), но не дубликаты.
- **НЕ забывать revoke на user delete** — cascading через FK работает, но `ContactShareRevoked` event тоже должен публиковаться.

## Skills relevant to this BC

- `write-rls-policy` — RLS на channels + shares (особенно recipient bilateral check).
- `outbox-event` — публикация ContactShareGranted / Revoked.
- `create-migration` — schema changes; encrypted columns требуют отдельной миграции для backfill `channel_value_hash`.
- `guest-rsvp-merge` — использует `channel_value_hash` для find user by phone/email.

## Notes

`UserContactChannel.channel_type='custom_url'` — discord / VK / в будущем — без encryption (публичные ссылки) [Г]; но Phase 1 = все encrypted единообразно, оптимизация при появлении проблемы.
