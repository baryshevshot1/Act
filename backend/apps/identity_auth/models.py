"""Identity & Auth — root BC.

[F: backend/apps/identity_auth/CLAUDE.md «Entities» — 7 моделей]
[F: docs/ARCHITECTURE.md «Identity & Auth» строки 858-961]
[F: ADR-014 — PII encryption via django-cryptography + Yandex Lockbox]

7 моделей:
    User              — корневая, AUTH_USER_MODEL; email/phone encrypted + HMAC hash
    Session           — server-side с device fingerprinting
    MagicLinkToken    — 256-bit CSPRNG, 15 min TTL, IP/UA binding (NN #6: POST only)
    OAuthProvider     — справочник (telegram/vk/yandex)
    OAuthIdentity     — связь User ↔ provider_uid (encrypted)
    PasskeyCredential — placeholder; реальная схема приходит с django-otp-webauthn в W1
    ConsentRecord     — 152-ФЗ ст. 9 в ред. 156-ФЗ; 7 purposes — каждый отдельная запись
    AuthEvent         — append-only audit log; trigger для audit_log_pii_access

RLS: ВСЕ user-attributed модели имеют RLS policies (User, Session, MagicLinkToken,
OAuthIdentity, PasskeyCredential, ConsentRecord, AuthEvent). FORCE + RESTRICTIVE
default_deny — обязательно. SQL policies живут в Phase 1.4.bis миграции
(см. .claude/skills/write-rls-policy/SKILL.md).
"""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserStatus(models.TextChoices):
    PENDING = "pending", "Pending verification"
    ACTIVE = "active", "Active"
    BANNED = "banned", "Banned"
    DELETED = "deleted", "Soft-deleted"


class UserManager(BaseUserManager["User"]):
    """Custom manager — email/phone normalization + signup invariants.

    Реальная бизнес-логика signup живёт в `services.py`. Этот manager —
    минимум для совместимости с `AUTH_USER_MODEL` requirements (createsuperuser).
    """

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: object) -> "User":
        if not email:
            raise ValueError("Email обязателен для регистрации.")
        normalized = self.normalize_email(email).lower()
        user = self.model(primary_email_hash=normalized, **extra)
        # На Phase 1.4 password storage остаётся placeholder — реальный flow
        # passwordless (magic link / Telegram OIDC). Поддерживаем для admin createsuperuser.
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra: object) -> "User":
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("status", UserStatus.ACTIVE)
        return self.create_user(email=email, password=password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Базовая identity сущность.

    PII поля (email, phone) ХРАНЯТСЯ encrypted; exact-match lookup через
    HMAC hash. На Phase 1.4 поля помечены как CharField; реальное шифрование
    через django-cryptography подключается в W1 (требует ключа в Lockbox).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        # TODO Phase 1.4.bis: pg_uuidv7 default; UUIDv4 — write-perf compromise.
        editable=False,
    )

    # Email — encrypted at rest, exact-match via HMAC hash.
    # [F: identity_auth/CLAUDE.md «Conventions: Email / phone normalization ДО save»]
    primary_email_encrypted = models.TextField(
        blank=True, default="",
        help_text="ENCRYPT_AT_REST (django-cryptography в W1). НЕ filter — используй hash.",
    )
    primary_email_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="HMAC-SHA256(PII_HMAC_SECRET, lowercase(email)) — для exact lookup.",
    )

    # Phone — same pattern. Nullable: signup may be Telegram-only без phone.
    phone_e164_encrypted = models.TextField(blank=True, default="")
    phone_e164_hash = models.CharField(
        max_length=64, null=True, blank=True, db_index=True, unique=True,
        help_text="HMAC-SHA256(PII_HMAC_SECRET, +E164 normalized phone).",
    )

    # Telegram — unique (если задано); plain — это публичный handle.
    telegram_id = models.CharField(
        max_length=64, null=True, blank=True, unique=True,
        help_text="Telegram user_id (numeric); НЕ username (мог измениться).",
    )

    # Локаль/география (FK на localization придёт в Iteration 9).
    locale = models.CharField(max_length=8, default="ru")
    country_code = models.CharField(max_length=2, default="RU")
    city_id = models.UUIDField(null=True, blank=True)

    # Status FSM.
    status = models.CharField(
        max_length=16, choices=UserStatus.choices, default=UserStatus.PENDING,
    )

    # Django admin / permissions framework — нужны для createsuperuser.
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "primary_email_hash"        # email_hash используется для login через allauth
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "identity_auth_user"
        indexes = [
            models.Index(fields=["telegram_id"], name="user_telegram_id_idx"),
            models.Index(fields=["status"], name="user_status_idx"),
        ]
        verbose_name = "User"
        verbose_name_plural = "Users"


# ---------------------------------------------------------------------------
# Session — server-side с device fingerprinting (RLS owner-only)
# ---------------------------------------------------------------------------
class Session(models.Model):
    """Server-side session с device fingerprinting.

    Django default sessions framework НЕ используем — нужен RLS owner-isolation
    + device tracking + sliding expiry per identity_auth/CLAUDE.md.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity_auth.User", on_delete=models.CASCADE, related_name="sessions",
    )
    session_token_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="HMAC-SHA256(secret, raw_token); raw — в cookie, hash — в БД.",
    )
    device_fingerprint = models.CharField(max_length=128, blank=True, default="")
    ip_address_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent = models.CharField(max_length=512, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "identity_auth_session"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="session_user_exp_idx"),
        ]
        # RLS: session_owner policy (USING user_id = current_user_id) — Phase 1.4.bis.


# ---------------------------------------------------------------------------
# MagicLinkToken — passwordless email auth (NN #6: POST only)
# ---------------------------------------------------------------------------
class MagicLinkToken(models.Model):
    """One-time, 15-min TTL, IP/UA binding.

    NON-NEGOTIABLE #6: НЕ логинить на GET. Link-preview боты (Telegram WebpageBot,
    Microsoft SafeLinks) сожгут token. Auth flow: GET показывает кнопку
    «Подтвердить вход», клик → POST → verify_magic_link → session.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="HMAC-SHA256(secret, raw_token). Raw — никогда в БД (NN #6).",
    )
    user = models.ForeignKey(
        "identity_auth.User", on_delete=models.CASCADE, related_name="magic_links",
    )
    email_hash_target = models.CharField(
        max_length=64, db_index=True,
        help_text="Защита от подмены user_id: при verify cравниваем с user.email_hash.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address_hash = models.CharField(max_length=64, blank=True, default="")
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        db_table = "identity_auth_magic_link_token"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="magiclink_user_exp_idx"),
        ]


# ---------------------------------------------------------------------------
# OAuth — Telegram primary, VK/Yandex secondary
# ---------------------------------------------------------------------------
class OAuthProvider(models.Model):
    """Справочник провайдеров — не RLS (lookup table)."""

    TELEGRAM = "telegram"
    VK = "vk"
    YANDEX = "yandex"

    name = models.CharField(max_length=32, primary_key=True)
    display_name = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "identity_auth_oauth_provider"


class OAuthIdentity(models.Model):
    """Связь User ↔ provider_uid.

    `provider_uid_encrypted` + `provider_uid_hash` — same pattern что email/phone.
    UNIQUE (provider, provider_uid_hash) — нельзя двум User-ам иметь
    тот же Telegram ID.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity_auth.User", on_delete=models.CASCADE, related_name="oauth_identities",
    )
    provider = models.ForeignKey(
        "identity_auth.OAuthProvider", on_delete=models.PROTECT,
    )
    provider_uid_encrypted = models.TextField()
    provider_uid_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_auth_oauth_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_uid_hash"],
                name="oauth_identity_provider_uid_uniq",
            ),
        ]


# ---------------------------------------------------------------------------
# PasskeyCredential — placeholder.
# Реальная схема придёт с django-otp-webauthn в W1 (миграции пакета).
# Здесь только маркер — чтобы RLS migration в Phase 1.4.bis знала, что
# таблица будет существовать. См. github.com/Stormbase/django-otp-webauthn.
# ---------------------------------------------------------------------------
class PasskeyCredential(models.Model):
    """Placeholder; в W1 заменяется на django-otp-webauthn provided model."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity_auth.User", on_delete=models.CASCADE, related_name="passkeys",
    )
    # Реальные WebAuthn поля (credential_id, public_key, sign_count, transports)
    # приходят с django-otp-webauthn — не дублируем здесь.
    placeholder_marker = models.CharField(
        max_length=8, default="W1",
        help_text="Удаляется при switch на django-otp-webauthn в W1.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_auth_passkey_credential"


# ---------------------------------------------------------------------------
# ConsentRecord — 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025
# ---------------------------------------------------------------------------
class ConsentPurpose(models.TextChoices):
    """7 purposes — каждый отдельная запись (NON-NEGOTIABLE #2 + #9).

    [F: CLAUDE.md «Глоссарий» — ConsentRecord]
    """

    CORE_PROCESSING = "core_processing", "Core processing (152-ФЗ ст. 9)"
    MARKETING = "marketing", "Marketing communications"
    CONTACT_SHARING = "contact_sharing", "Bilateral contact sharing"
    CROSS_BORDER_TRANSFER = "cross_border_transfer", "ТППД (Telegram FZ-LLC, ст. 12)"
    COOKIES_ESSENTIAL = "cookies_essential", "Essential cookies (always granted)"
    COOKIES_ANALYTICS = "cookies_analytics", "Analytics cookies (PostHog)"
    COOKIES_MARKETING = "cookies_marketing", "Marketing cookies (retargeting)"


class ConsentRecord(models.Model):
    """Отдельный документ согласия — НЕ вложенный чекбокс.

    [F: CLAUDE.md NN #2: 152-ФЗ ст. 9 в ред. 156-ФЗ; NN #9: ст. 12 ТППД]
    `consent_text_hash` фиксирует версию документа на момент granting —
    при изменении текста требуется новое согласие.
    `ip_address` хранится PLAIN (не hash) — РКН требует читаемый IP для аудита.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity_auth.User", on_delete=models.CASCADE, related_name="consents",
    )
    purpose = models.CharField(max_length=32, choices=ConsentPurpose.choices)
    consent_text_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 текста документа на момент granting (audit-trail).",
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(
        help_text="PLAIN, не hash — РКН требует читаемый IP для аудита.",
    )
    user_agent = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        db_table = "identity_auth_consent"
        indexes = [
            models.Index(fields=["user", "purpose"], name="consent_user_purpose_idx"),
            models.Index(fields=["purpose", "granted_at"], name="consent_purpose_at_idx"),
        ]


# ---------------------------------------------------------------------------
# AuthEvent — append-only audit log; trigger для audit_log_pii_access
# ---------------------------------------------------------------------------
class AuthEventType(models.TextChoices):
    LOGIN_OK = "login_ok", "Login succeeded"
    LOGIN_FAIL = "login_fail", "Login failed"
    SIGNUP = "signup", "Signup completed"
    LOGOUT = "logout", "Logout"
    PASSWORD_RESET = "password_reset", "Password reset requested"
    CONSENT_GRANTED = "consent_granted", "Consent granted"
    CONSENT_WITHDRAWN = "consent_withdrawn", "Consent withdrawn"
    BAN_APPLIED = "ban_applied", "User banned (admin action)"
    PII_ACCESS = "pii_access", "PII field read by admin/service"


class AuthEvent(models.Model):
    """Append-only audit log (writes only; UPDATE/DELETE — alarm).

    Cross-references audit_log_pii_access (отдельная таблица в Wave 3) для
    full compliance trail; здесь — minimal authz/authn events для security
    monitoring + Sentry alerts (login spikes etc).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(
        "identity_auth.User", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="auth_events",
        help_text="NULL для anonymous events (failed login без существующего user).",
    )
    event_type = models.CharField(max_length=32, choices=AuthEventType.choices)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address_hash = models.CharField(
        max_length=64, blank=True, default="",
        help_text="SHA-256(IP + daily salt) — не plain IP (минимизация).",
    )
    user_agent_hash = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "identity_auth_auth_event"
        indexes = [
            models.Index(
                fields=["actor_user", "created_at"],
                name="authevent_actor_at_idx",
            ),
            models.Index(
                fields=["event_type", "created_at"],
                name="authevent_type_at_idx",
            ),
        ]
