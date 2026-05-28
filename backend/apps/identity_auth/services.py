"""Service layer — единственное место, где разрешён ORM-доступ для identity_auth.

[F: CLAUDE.md «Конвенции кода: ORM ТОЛЬКО в services.py»]
[F: backend/apps/identity_auth/CLAUDE.md «Conventions»]

Все signatures соответствуют 7 приоритетам аутентификации
(см. CLAUDE.md). Реальная реализация — в W1 sprint (Identity & Auth full).
Phase 1.4 — только signatures + `raise NotImplementedError` для compile-time
проверки правильности cross-context импортов через import-linter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from .contracts import (
        ConsentContract,
        ConsentPurposeContract,
        MagicLinkContract,
        RequestMeta,
        UserContract,
    )


# ---------------------------------------------------------------------------
# Signup / login
# ---------------------------------------------------------------------------
def signup_with_telegram_oidc(
    *,
    telegram_id: str,
    locale: str,
    request_meta: RequestMeta,
    consent_cross_border_transfer: bool,
) -> UserContract:
    """Создаёт User через Telegram Login Widget callback.

    NOTE: имя функции содержит «oidc» по историческим причинам — Telegram
    использует HMAC-SHA256, а не OAuth/OIDC. Реальная обработка делегируется
    нативному `allauth.socialaccount.providers.telegram` (research R2). W1
    sprint может переименовать функцию.

    PRE-condition: `consent_cross_border_transfer=True` — без него Telegram API
    нельзя вызывать (NN #9 + ADR-013). Caller должен показать explicit-checkbox
    «использовать Telegram-каналы» и записать `ConsentRecord(purpose=
    cross_border_transfer)` в той же транзакции.

    POST-conditions (in single transaction):
        - User(telegram_id) created
        - ConsentRecord(core_processing, cross_border_transfer) created
        - AuthEvent(signup) appended
        - Outbox: UserRegistered emitted
        - merge_guest_on_signup called for matching GuestRSVPs (via outbox sub)
    """
    raise NotImplementedError("W1 sprint — Identity & Auth full implementation")


def request_magic_link(
    *,
    email: str,
    request_meta: RequestMeta,
) -> MagicLinkContract:
    """Генерирует MagicLinkToken, отправляет email через UniSender/SendPulse.

    Rate limit: 3/min/IP + 10/hour/email (см. ARCHITECTURE.md Rate Limiting).
    Token: 256-bit CSPRNG (secrets.token_urlsafe(32)); хранится только HMAC hash.
    """
    raise NotImplementedError("W1 sprint")


def verify_magic_link(
    *,
    raw_token: str,
    request_meta: RequestMeta,
) -> UserContract:
    """Verify magic-link и логинит пользователя.

    NON-NEGOTIABLE #6: вызывается ТОЛЬКО на POST после явного клика.
    GET-handler страницы показывает кнопку «Подтвердить вход» —
    клик → POST с CSRF-token → этот service.

    Атомарно:
        - find MagicLinkToken by HMAC hash; verify not expired, not used
        - mark used_at
        - create Session
        - AuthEvent(login_ok)
        - merge_guest_on_signup для всех matching GuestRSVPs (через outbox)
    """
    raise NotImplementedError("W1 sprint — POST only (NN #6)")


def find_user_by_email(*, email: str) -> UserContract | None:
    """Exact-match lookup через HMAC hash; НЕ filter(email=)."""
    raise NotImplementedError("W1 sprint")


def find_user_by_phone(*, phone_e164: str) -> UserContract | None:
    """Phone normalize до +E164 ДО HMAC — иначе hash не совпадёт."""
    raise NotImplementedError("W1 sprint")


def find_user_by_telegram_id(*, telegram_id: str) -> UserContract | None:
    """Telegram ID — публичный handle, plain lookup OK."""
    raise NotImplementedError("W1 sprint")


# ---------------------------------------------------------------------------
# Consent — 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025
# ---------------------------------------------------------------------------
def grant_consent(
    *,
    user_id: UUID,
    purpose: ConsentPurposeContract,
    consent_text_hash: str,
    ip_address: str,
    user_agent: str,
) -> ConsentContract:
    """Записать согласие.

    Отдельный документ согласия (NN #2). `consent_text_hash` фиксирует версию.
    Если новая версия документа — нужно новое согласие (старая запись остаётся
    для audit, новая создаётся с другим hash).

    Outbox: ConsentGranted event для analytics retention monitoring.
    """
    raise NotImplementedError("W1 sprint")


def withdraw_consent(
    *,
    user_id: UUID,
    purpose: ConsentPurposeContract,
    ip_address: str,
) -> None:
    """Отзыв согласия (ст. 14 152-ФЗ — право на удаление).

    Side effects:
        - ConsentRecord.withdrawn_at = now()
        - Если purpose='cross_border_transfer' → суspend все Telegram channels
        - AuthEvent(consent_withdrawn)
        - Outbox: ConsentWithdrawn → notifications BC suppress future Telegram sends
    """
    raise NotImplementedError("W1 sprint")


def has_consent(*, user_id: UUID, purpose: ConsentPurposeContract) -> bool:
    """Проверка активного согласия (granted_at is not null, withdrawn_at is null).

    ВАЖНО: вызывается ПЕРЕД любым cross-border data flow
    (Telegram API, ESP в зарубежной юрисдикции etc).
    """
    raise NotImplementedError("W1 sprint")
