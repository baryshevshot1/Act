# apps/identity_auth — Security-Critical Context

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C Identity & Auth).
> Источники: `ARCHITECTURE.md` (Level C готов) + PDF V1.3 секции 20.1-20.2.

## Context

Identity & Auth — **root BC**. Owns: `User`, `Session`, `MagicLinkToken`, `OAuthProvider`, `OAuthIdentity`, `PasskeyCredential`, `ConsentRecord`, `AuthEvent`. Все security-critical operations и compliance touchpoints проходят через этот контекст. Никаких импортов из других `apps.*` (см. `.importlinter` CONTRACT 1).

## Entities (7 verbatim из PDF V1.3 секция 20.1 + `AuthEvent` — Wave 1+ дополнение для `audit_log_pii_access`)

| Entity | Description | RLS? | Encrypted fields |
|---|---|---|---|
| `User` | `id UUIDv7 PK`, `primary_email` (encrypted + hashed), `phone_e164` (encrypted + hashed), `telegram_id` (unique nullable), `locale`, `country_code`, `city_id`, `status` | ✓ | email, phone |
| `Session` | server-side sessions с device fingerprinting | ✓ | — |
| `MagicLinkToken` | 256-bit CSPRNG, 15 min TTL, one-time use, IP / UA binding | ✓ | `token_hash` |
| `OAuthProvider` | справочник: `telegram`, `vk`, `yandex` | — (справочник) | — |
| `OAuthIdentity` | связь User ↔ provider_uid | ✓ | `provider_uid` |
| `PasskeyCredential` | через `django-otp-webauthn` [F: github.com/Stormbase/django-otp-webauthn] | ✓ | — |
| `ConsentRecord` | id, user_id, purpose, `consent_text_hash`, `granted_at`, `withdrawn_at`, `ip_address`. Purposes: `core_processing`, `marketing`, `contact_sharing`, `cross_border_transfer`, `cookies_essential`, `cookies_analytics`, `cookies_marketing` | ✓ | — |
| `AuthEvent` | append-only audit log; для `audit_log_pii_access` trigger | ✓ | `ip_address` (hashed) |

## 7 приоритетов аутентификации (PDF `Leto_project_p1.pdf` раздел 3.5)

1. **Telegram Login Widget primary** — нативный provider `allauth.socialaccount.providers.telegram` (без кастомного adapter — research R2 confirmed). HMAC-SHA256 callback (не OAuth/OIDC). Требует ст. 12 consent (см. NON-NEGOTIABLE #9). Mini App `initData` flow — отложен до Phase 5+.
2. **VK ID secondary** — `id.vk.com/about/business`, ИП-доступно. access_token 60 мин, refresh 180 дней.
3. **Yandex ID secondary** — `oauth.yandex.ru`, ИП через email. Виджет «Мгновенный вход».
4. **Apple Sign-In** — только EN-сегмент. Требует зарубежного юр.лица. `[?]` deferred до Phase 6+.
5. **Google Sign-In** — `[?]` deferred (Google Cloud Billing не принимает РФ-карты).
6. **Email magic link** — fallback universal. 256-bit CSPRNG, 15 мин TTL, one-time, IP / UA binding. **POST после явного клика** (NON-NEGOTIABLE #6).
7. **Phone OTP** — Telegram Gateway primary ($0.01 / code), SMS.ru fallback. Только с ст. 12 consent.

## Conventions

- **Consent — отдельный документ** (NON-NEGOTIABLE #2: 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025). НЕ вложенный чекбокс «согласен с правилами»; каждый purpose из `ConsentRecord` — отдельная запись с `consent_text_hash`.
- **RLS policies** — все RLS-таблицы создаются через skill `.claude/skills/write-rls-policy/` (FORCE + RESTRICTIVE `default_deny` + `SET LOCAL app.current_user_id`, NON-NEGOTIABLE #11).
- **Password hashing:** `argon2id` (default Django 5.2). НИКОГДА bcrypt, plain SHA, MD5.
- **Email / phone normalization** ДО save: lowercase emails; `+7` для RU phones.
- **ВСЕ writes к User** → `AuthEvent` записать в одной транзакции (Outbox subscriber, ADR-016).
- **Session token:** 256 bits, secure cookie, `SameSite=Strict`, `HttpOnly`, `Secure`.
- **Magic link rate limit:** 3 попытки за 15 мин / IP; 10 / час / email; lockout после 5 неудач (PDF V1.1 раздел 3.3).
- **PasskeyCredential:** только через `django-otp-webauthn` API — не писать кастомных WebAuthn endpoint'ов.

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `UserContract`, `SessionContract`, `ConsentContract`, `TenantContract` (= self-reference).
- **Consumes:** ничего (root BC, никаких импортов из других `apps.*`).
- **Emits via Outbox** (ADR-016): `UserRegistered`, `UserBanned`, `ConsentGranted`, `ConsentWithdrawn`.

## Common pitfalls (security-critical)

- **НЕ возвращать `User` instance** за пределы BC — только `UserContract` DTO (без sensitive полей).
- **НЕ логировать** password / token / `magic_link_value` даже в DEBUG. Все логи проходят через `apps.core.logging.redact_pii`.
- **НЕ использовать** `User.objects.filter(email=)` без `.first()` или `get_or_none` — race на enumeration timing-attack.
- **НЕ логинить пользователя на GET** — link-preview боты (Telegram WebpageBot, Microsoft SafeLinks) сожгут magic-link token. Логин ТОЛЬКО на POST после явного клика (NON-NEGOTIABLE #6).
- **НЕ забывать `ConsentRecord(purpose='cross_border_transfer')`** перед любым вызовом Telegram Bot API / Telegram Gateway (NON-NEGOTIABLE #9, ADR-013).
- **НЕ забывать audit log** для admin-операций (impersonation, manual ban, manual verification) — все mutations через `act_admin` BYPASSRLS-роль ОБЯЗАТЕЛЬНО логируются в `audit_log_pii_access` [F: `CLAUDE.md` строка 124].
