# Act — Entity-Relationship Diagram (ERD)

> Mermaid ERD для 16 bounded contexts. Полный domain-model snapshot для Phase 1 Bootstrap.
> Источники: `docs/ARCHITECTURE.md` § Основные сущности + 6 готовых Level C (identity_auth, events, rsvp, contacts_sharing, recommendations, localization) + Wave 3 (audit_log_pii_access, outbox).
> Дата: 2026-05-27.

## 1. Bounded Context overview (cross-context dependencies)

```mermaid
flowchart TB
    subgraph "Cross-cutting"
        OUTBOX[(outbox_event)]
        AUDIT[(audit_log_pii_access)]
    end
    
    subgraph "Identity layer"
        IA[identity_auth]
        UP[user_profile]
        VER[verification]
    end
    
    subgraph "Domain layer"
        GR[groups]
        EV[events]
        RE[recurrence_engine]
        RS[rsvp]
        CS[contacts_sharing]
        RT[ratings]
    end
    
    subgraph "Service layer"
        DS[discovery]
        RC[recommendations]
        NT[notifications]
        MOD[moderation]
    end
    
    subgraph "Support"
        LOC[localization]
        AN[analytics]
        AC[admin_console]
    end
    
    IA -.UserContract.-> UP
    IA -.UserContract.-> VER
    IA -.UserContract.-> EV
    IA -.UserContract.-> RS
    EV -.EventDTO.-> RS
    EV -.EventDTO.-> DS
    EV -.EventDTO.-> RC
    GR -.GroupDTO.-> EV
    RE -.SeriesDTO.-> EV
    RS -.ParticipantDTO.-> RT
    RT -.RatingDTO.-> RC
    DS -.score_events_for_user.-> RC
    LOC -.LocaleDTO.-> EV
    LOC -.CityDTO.-> EV
    LOC -.CountryDTO.-> EV
    
    EV ==EventPublished==> OUTBOX
    RS ==RSVPConfirmed==> OUTBOX
    RT ==RatingPosted==> OUTBOX
    OUTBOX ==NotificationDelivered==> NT
    OUTBOX ==InvalidateCache==> RC
    
    style OUTBOX fill:#f9f
    style AUDIT fill:#fcf
```

**Легенда:**
- `-.DTO.->` — synchronous cross-context import через `contracts.py`.
- `==Event==>` — async cross-context через `outbox_event` (ADR-016, никаких Django signals).

## 2. Identity & Auth (Level C готов)

```mermaid
erDiagram
    USER ||--o{ SESSION : "has many"
    USER ||--o{ MAGIC_LINK_TOKEN : "requests"
    USER ||--o{ OAUTH_IDENTITY : "links to"
    USER ||--o{ PASSKEY_CREDENTIAL : "registers"
    USER ||--o{ CONSENT_RECORD : "grants"
    USER ||--o{ AUTH_EVENT : "produces"
    OAUTH_PROVIDER ||--o{ OAUTH_IDENTITY : "supplies"
    
    USER {
        uuid id PK "UUIDv7"
        text primary_email "encrypted+hashed"
        text phone_e164 "encrypted+hashed"
        text telegram_id "unique nullable"
        varchar locale FK
        varchar country_code
        uuid city_id FK
        varchar status "active|banned"
        timestamptz created_at
    }
    SESSION {
        uuid id PK
        uuid user_id FK
        bytea device_fingerprint
        timestamptz expires_at
    }
    MAGIC_LINK_TOKEN {
        uuid id PK "UUIDv4 — NOT v7"
        varchar email_hash "HMAC-SHA256"
        varchar token_hash "256-bit CSPRNG"
        timestamptz expires_at "15 min TTL"
        inet ip_address
    }
    CONSENT_RECORD {
        uuid id PK
        uuid user_id FK
        varchar purpose "core_processing|marketing|contact_sharing|cross_border_transfer|cookies_*"
        varchar consent_text_hash
        timestamptz granted_at
        timestamptz withdrawn_at
        inet ip_address
    }
    AUTH_EVENT {
        uuid id PK
        uuid user_id FK
        varchar event_type "login|logout|signup|password_change"
        timestamptz occurred_at
        varchar ip_hash
    }
```

## 3. Events + Recurrence (Level C готов)

```mermaid
erDiagram
    EVENT_SERIES ||--o{ EVENT : "generates"
    EVENT_SERIES ||--o{ EX_DATE : "excludes"
    EVENT_SERIES ||--o{ RECURRENCE_OVERRIDE : "modifies"
    EVENT ||--|| EVENT_COVER_IMAGE : "has 0..1"
    USER ||--o{ EVENT : "organizes"
    GROUP ||--o{ EVENT : "hosts (optional)"
    CITY ||--o{ EVENT : "located in"
    
    EVENT_SERIES {
        uuid id PK "UUIDv7"
        uuid organizer_user_id FK
        text rrule "RFC 5545"
        timestamptz dtstart
        timestamptz until "nullable"
        jsonb template_event_data
        timestamptz next_generation_at
    }
    EVENT {
        uuid id PK "UUIDv7"
        uuid organizer_user_id FK
        uuid series_id FK "nullable"
        timestamptz recurrence_id "matching key for override"
        uuid group_id FK "nullable"
        text title "default locale"
        timestamptz starts_at
        timestamptz ends_at
        int capacity
        varchar status "draft|published|full|cancelled|completed"
        boolean is_paid
        numeric price "nullable"
        varchar currency "nullable"
    }
    EX_DATE {
        uuid series_id FK
        timestamptz excluded_date
    }
    RECURRENCE_OVERRIDE {
        uuid id PK
        uuid series_id FK
        timestamptz recurrence_id
        varchar range "THISONLY|THISANDFUTURE"
        jsonb override_fields
    }
```

## 4. RSVP & Attendance (Level C готов)

```mermaid
erDiagram
    EVENT ||--o{ EVENT_PARTICIPANT : "tracks"
    EVENT ||--o{ GUEST_RSVP : "tracks"
    EVENT ||--o{ WAITLIST_ENTRY : "queues"
    USER ||--o{ EVENT_PARTICIPANT : "creates"
    GUEST_RSVP }o--|| EVENT_PARTICIPANT : "merges to (after signup)"
    
    EVENT_PARTICIPANT {
        uuid id PK "UUIDv7"
        uuid event_id FK
        uuid user_id FK
        varchar status "applied|confirmed|waitlist|declined|checked_in|no_show"
        timestamptz applied_at
        timestamptz confirmed_at
        timestamptz checked_in_at
        uuid merged_from_guest_id "nullable, audit"
    }
    GUEST_RSVP {
        uuid id PK "UUIDv7"
        uuid event_id FK
        varchar channel "email|telegram_handle|phone"
        text value "encrypted (django-cryptography)"
        varchar value_hash "HMAC for lookup"
        text display_name
        varchar status
        uuid merged_into_user_id "nullable"
    }
    WAITLIST_ENTRY {
        uuid event_id FK
        uuid user_or_guest_id
        int position
        timestamptz created_at
    }
```

## 5. Contacts Sharing + Ratings + Groups

```mermaid
erDiagram
    USER ||--o{ USER_CONTACT_CHANNEL : "owns"
    USER_CONTACT_CHANNEL ||--o{ CONTACT_SHARE : "shared via"
    USER ||--o{ CONTACT_SHARE : "donates (from_user_id)"
    USER ||--o{ CONTACT_SHARE : "receives (to_user_id)"
    EVENT ||--o{ CONTACT_SHARE : "scoped to"
    CONSENT_RECORD ||--o{ CONTACT_SHARE : "audits"
    
    EVENT ||--o{ RATING : "subject"
    USER ||--o{ RATING : "rater"
    USER ||--o{ RATING : "ratee"
    USER ||--o{ REPUTATION_SCORE : "has"
    
    USER ||--o{ GROUP : "owns"
    GROUP ||--o{ GROUP_MEMBERSHIP : "has"
    USER ||--o{ GROUP_MEMBERSHIP : "joins"
    GROUP ||--o{ GROUP_RULE : "enforces"
    
    USER_CONTACT_CHANNEL {
        uuid id PK
        uuid user_id FK
        varchar channel_type "telegram_handle|phone|email|instagram|custom_url"
        text channel_value "ENCRYPT_AT_REST"
        varchar channel_value_hash "HMAC for lookup"
    }
    CONTACT_SHARE {
        uuid id PK
        uuid from_user_id FK
        uuid to_user_id FK
        uuid event_id FK
        uuid channel_id FK
        uuid consent_record_id FK "152-ФЗ ст. 9 ред. 156-ФЗ"
        timestamptz granted_at
        timestamptz revoked_at "nullable, soft-delete"
    }
    RATING {
        uuid id PK
        uuid event_id FK
        uuid rater_user_id FK
        uuid ratee_user_id FK
        smallint score "1-5"
        text comment
        varchar visibility "hidden_until_reciprocal|visible"
        timestamptz created_at
    }
    REPUTATION_SCORE {
        uuid user_id FK
        varchar scope "as_organizer|as_participant"
        numeric score
        int sample_size
        timestamptz last_recomputed_at
    }
```

## 6. Cross-cutting infrastructure (Outbox + Audit)

```mermaid
erDiagram
    OUTBOX_EVENT {
        uuid id PK "UUIDv7"
        varchar event_type "EventPublished|RSVPConfirmed|..."
        varchar aggregate_type "Event|User|Group"
        uuid aggregate_id
        jsonb payload "denormalized snapshot"
        timestamptz created_at
        timestamptz published_at "NULL = pending"
        int error_count "alert at >= 10"
        text last_error
    }
    AUDIT_LOG_PII_ACCESS {
        uuid id PK "UUIDv7"
        uuid actor_user_id FK
        varchar actor_role "self|admin|moderator|service"
        uuid accessed_user_id FK
        varchar accessed_field "phone|email|telegram_id|verification_doc"
        varchar purpose "human-readable"
        varchar ip_hash "SHA-256(ip + daily salt)"
        uuid request_id "Sentry/LGTM correlation"
        timestamptz accessed_at
    }
```

## 7. Localization справочники

```mermaid
erDiagram
    LOCALE ||--o| LOCALE : "fallback chain"
    COUNTRY ||--o{ CITY : "has"
    COUNTRY ||--o{ USER : "primary"
    CITY ||--o{ USER : "primary"
    CITY ||--o{ EVENT : "located"
    
    LOCALE {
        varchar code PK "ru-RU|en-US"
        varchar icu_language_tag "BCP 47"
        varchar fallback_locale_code FK
        boolean is_rtl
        boolean is_active
    }
    COUNTRY {
        uuid id PK
        varchar iso_code "ISO 3166-1 alpha-2"
        jsonb localized_names "expression index per-locale"
        varchar default_locale_code FK
    }
    CITY {
        uuid id PK
        uuid country_id FK
        jsonb localized_names
        varchar iana_timezone "Europe/Moscow"
        numeric latitude
        numeric longitude
    }
```

## Notes

- **Mermaid rendering**: GitHub README/wiki, VS Code preview, `mermaid-cli` для статической генерации SVG.
- **Cardinality notation**: `||--o{` = 1:N, `||--||` = 1:1, `||--o|` = 1:0..1, `}o--||` = N:1.
- **Type hints**: ORM-mapped types (uuid, varchar, jsonb, timestamptz, inet); фактические Django field types — в `apps/<ctx>/models.py` (Phase 1).
- **Encryption notes**: `encrypted` columns используют `django-cryptography` + Yandex Lockbox (ADR-014). Lookup через `_hash` HMAC columns.
- **10 missing BCs** (user_profile, verification details, groups full schema, ratings windows, discovery indexes, notifications FSM, moderation, analytics, admin_console, recurrence_engine standalone — если будет решение разделить с events post-Pilot) — Level C добавится в Iteration 9; ERD расширится.

## Cross-refs

- Полная schema каждой таблицы → `docs/ARCHITECTURE.md` соответствующий Level C.
- RLS policies для каждой user-attributed таблицы → skill `.claude/skills/write-rls-policy/`.
- Per-context patterns → `backend/apps/<ctx>/CLAUDE.md`.
