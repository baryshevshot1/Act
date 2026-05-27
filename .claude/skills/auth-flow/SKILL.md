---
name: auth-flow
description: Implements authentication flows for Act — Telegram OIDC (primary), magic-link email (fallback), VK ID / Yandex ID (secondary), phone OTP. Use when adding signup/login routes, when user says "add auth", "magic link", "Telegram OIDC", "OAuth", "passkey", or when implementing identity_auth services. NEVER login on GET (NN #6); NEVER call Telegram API without cross-border consent (NN #9).
allowed-tools: [Read, Write, Edit]
---

# Auth Flow (Telegram OIDC primary + magic-link fallback + OTP)

> **identity_auth context** (Level C готов) [F: `docs/ARCHITECTURE.md` § Identity & Auth + `backend/apps/identity_auth/CLAUDE.md`]. 7 приоритетов аутентификации из PDF V1.1 раздел 3.5. Соблюдать **NON-NEGOTIABLE #6** (magic links POST), **#7** (PII encryption), **#9** (cross-border consent для Telegram).

## When to use

- Новая страница signup / login / magic-link verify.
- Новый OAuth provider (VK ID secondary, Yandex ID secondary).
- Phone OTP flow через Telegram Gateway / SMS.ru.
- Adding passkey/WebAuthn endpoint (только через `django-otp-webauthn`).
- Implementing `signup_with_*` service в `apps/identity_auth/services.py`.

## When NOT to use

- Session management — это middleware, не отдельный flow (см. `apps/core/middleware/session.py`).
- Authorization (kто может что) — это RLS (skill `write-rls-policy`) + service-layer guards, не auth.
- Импорт `User` model в другой BC — запрещено (`.importlinter` CONTRACT 1); используй `apps.identity_auth.contracts.UserContract`.

## 7 приоритетов аутентификации [F: PDF V1.1 раздел 3.5]

| # | Provider | Implementation | Consent required |
|---|---|---|---|
| 1 | **Telegram OIDC** (primary) | `django-allauth` + custom adapter (~100 lines) | `cross_border_transfer` (NN #9, ADR-013) |
| 2 | **VK ID** secondary | `id.vk.com/about/business`, ИП-доступно | `core_processing` |
| 3 | **Yandex ID** secondary | `oauth.yandex.ru`, виджет «Мгновенный вход» | `core_processing` |
| 4 | **Apple Sign-In** | требует foreign юр.лицо | DEFERRED Phase 6+ |
| 5 | **Google Sign-In** | Google Cloud Billing не принимает РФ-карты | DEFERRED |
| 6 | **Email magic link** (fallback) | 256-bit CSPRNG, 15 min TTL, **POST after click** | `core_processing` |
| 7 | **Phone OTP** | Telegram Gateway primary; SMS.ru fallback | `cross_border_transfer` для Telegram Gateway |

## Pattern 1. Magic-link (POST after explicit click)

> **NN #6** [F: `CLAUDE.md` строка 134]: НЕ логинить на GET. Link-preview боты (Telegram WebpageBot, Microsoft SafeLinks) сожгут token. Sources: [F: supertokens.com/blog/magiclinks], [F: etodd.io/2026/03/22/magic-link-pitfalls].

```python
# apps/identity_auth/services.py
import secrets
from datetime import timedelta
from django.utils.timezone import now

def request_magic_link(*, email: str, request_meta: RequestMeta) -> None:
    """Sends magic-link email. Public endpoint, rate-limited."""
    token = secrets.token_urlsafe(32)  # ~256 bits CSPRNG — NN UUID rules
    token_hash = hmac_sha256(MAGIC_LINK_HMAC_SECRET, token)
    with transaction.atomic():
        MagicLinkToken.objects.create(
            email_hash=hmac_sha256(PII_HMAC_SECRET, email.lower()),
            token_hash=token_hash,
            expires_at=now() + timedelta(minutes=15),
            ip_address=request_meta.ip_address,
            user_agent_hash=hmac_sha256(PII_HMAC_SECRET, request_meta.user_agent),
        )
    # Email — НЕ через Telegram (NN #9); через UniSender/SendPulse
    send_magic_link_email(to=email, verify_url=f'https://act.app/auth/verify?t={token}')
```

### Frontend `app/[locale]/auth/verify/page.tsx` (Next.js 16 Server Component)

```tsx
// GET handler — рендерит form с CSRF token + кнопкой «Войти»; НЕ логинит.
export default async function VerifyPage({ searchParams }: { searchParams: { t: string } }) {
  return (
    <form action="/api/auth/verify" method="POST">
      <input type="hidden" name="csrf_token" value={await getCsrfToken()} />
      <input type="hidden" name="t" value={searchParams.t} />
      <button type="submit">Войти как этот пользователь</button>
    </form>
  );
}
```

### POST `/api/auth/verify` (Django view)

```python
# apps/identity_auth/views.py
@require_POST
@csrf_protect
def verify_magic_link(request):
    token = request.POST.get('t')
    user, session = services.verify_magic_link(
        token=token,
        request_meta=RequestMeta.from_request(request),
    )
    login(request, user)
    return redirect(f'/{user.locale}/feed')
```

## Pattern 2. Telegram OIDC (with consent gate)

```python
# apps/identity_auth/services.py
def signup_with_telegram_oidc(*, telegram_data: TelegramOAuthData,
                              consent: ConsentInput) -> UserDTO:
    """
    consent.cross_border_transfer MUST be True (Telegram = ОАЭ; NN #9, ADR-013).
    """
    if not consent.cross_border_transfer:
        raise ConsentRequiredError(purpose='cross_border_transfer')
    if not consent.core_processing:
        raise ConsentRequiredError(purpose='core_processing')

    with transaction.atomic():
        user = User.objects.create(
            telegram_id=telegram_data.user_id,
            telegram_username=telegram_data.username,
            primary_email=None,  # Telegram OIDC не даёт email
        )
        # Записываем consent records в той же транзакции
        ConsentRecord.objects.create(
            user_id=user.id, purpose='core_processing',
            consent_text_hash=hash_consent_doc('core_processing'),
            granted_at=now(), ip_address=consent.ip_address,
        )
        ConsentRecord.objects.create(
            user_id=user.id, purpose='cross_border_transfer',
            consent_text_hash=hash_consent_doc('cross_border_transfer'),
            granted_at=now(), ip_address=consent.ip_address,
        )
        publish_event('UserRegistered', aggregate_id=user.id, payload={...})
        # Retroactive merge guest RSVPs (skill: guest-rsvp-merge)
        merge_guest_on_signup(user_id=user.id, contact_channel='telegram_handle',
                              contact_value=telegram_data.username)
        return UserDTO.from_orm(user)
```

## Pattern 3. Phone OTP с fallback (ADR-013)

```python
def request_phone_otp(*, phone_e164: str, consent: ConsentInput) -> None:
    code = f'{secrets.randbelow(10**6):06d}'  # CSPRNG 6 digits
    # ... save hashed code ...
    if consent.cross_border_transfer:
        send_via_telegram_gateway(phone_e164, code)  # $0.01/code
    else:
        send_via_sms_ru(phone_e164, code)  # domestic fallback
```

## Pitfalls

- **НЕ логинить на GET** (NN #6) — link-preview боты выжигают token.
- **НЕ вызывать Telegram API без consent** (NN #9) — fallback на SMS.ru / email через UniSender (ADR-013).
- **НЕ хранить magic-link plaintext** — только `token_hash` (HMAC-SHA256). Compare через constant-time `hmac.compare_digest`.
- **НЕ логировать** password / token / `magic_link_value` даже в DEBUG.
- **НЕ использовать `User.objects.filter(email=)`** напрямую без `.first()` или `get_or_none` — enumeration timing-attack.
- **НЕ возвращать `User` instance** за пределы BC — только `UserContract` DTO без sensitive полей.
- **НЕ забывать rate limit:** 3 попытки за 15 мин / IP; 10 / час / email; lockout после 5 неудач [F: PDF V1.1 раздел 3.3].
- **НЕ использовать UUIDv7 для tokens** — predictability риск; только UUIDv4 / `secrets.token_urlsafe()` [F: `CLAUDE.md` строка 104].
- **НЕ забывать AuthEvent record** на каждый login/signup/logout — append-only для `audit_log_pii_access`.

## Cross-context эффекты

- `UserRegistered` / `UserBanned` / `ConsentGranted` / `ConsentWithdrawn` через Outbox (ADR-016).
- При signup — call `merge_guest_on_signup` (skill `.claude/skills/guest-rsvp-merge/`).
- Все RLS-таблицы в identity_auth — через skill `.claude/skills/write-rls-policy/`.

## После реализации

1. Тест magic-link: GET `/auth/verify?t=X` рендерит form (HTTP 200) **без login**; POST с тем же token — logs in user.
2. Тест rate limit: 4-я попытка за 15 мин → HTTP 429.
3. Тест consent gate Telegram: signup без `cross_border_transfer` → `ConsentRequiredError`.
4. Тест fallback OTP: user без `cross_border_transfer` consent → SMS.ru вместо Telegram Gateway.
5. `lint-imports` CONTRACT 1 (identity_auth не импортирует другие BC напрямую).
6. AuthEvent написан для каждого attempted login.
