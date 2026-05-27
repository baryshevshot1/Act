# Промт: Phase 1.4 — Django skeleton (3 BC + RLS middleware)

> **Назначение.** Первая итерация **реального кода** в репозитории Act. Создать минимальный Django 5.2 LTS skeleton с layered settings, 3 BC stubs (identity_auth / events / rsvp), RLS middleware на FORCE + default_deny patterns, CSP middleware, базовый django-allauth wiring и healthz endpoint. Это **scaffold для Phase 1.4.bis** (PG extensions migration через прямой PG) и **Pilot Этап 0** (core flow signup → create event → RSVP).
>
> **Когда запускать.** Новая Claude Code сессия от свежего `main` (PR #3 audit-fixes уже merged). Founder создаёт сессию из web UI → она автоматически создаёт ветку `claude/<random-name>` от main и в конце пушит PR.
>
> **Кто запускает.** Соло-фаундер Андрей. Модель: **Claude Opus 4.7** (Fast mode опционально). Полный run — 6–8 часов AI-работы (ожидать stream tool calls, не торопить).
>
> **Что НЕ делает.** Не запускает живые миграции (это Phase 1.4.bis, требует PG). Не пишет Next.js (Phase 1.5). Не настраивает GitHub Actions (Phase 1.6). Не ставит Procrastinate worker (Phase 1.7). Не делает реальную интеграцию Telegram OIDC adapter (это W1 спринт MVP — слишком большой scope). Не трогает `pyproject.toml` зависимости (frozen V1.2 — менять только через ADR-update). Не создаёт live Yandex Cloud ресурсы (Phase 1.1, founder-bound).

-----

## 1. Роль

Ты — **principal Django engineer + RLS specialist + modular monolith architect** с четырьмя профилями:

1. **Convention-first.** Каждое решение сверяется с `CLAUDE.md` (frozen V1.2 стек + 11 NON-NEGOTIABLE) и `docs/ARCHITECTURE.md` (Level C для 3 целевых BC). Никаких «придумаю своё».
2. **RLS-discipline.** Каждая user-attributed таблица получает: `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy. Никаких exceptions — нарушение = security incident. Используй skill `write-rls-policy` через Skill tool, не пиши policy руками.
3. **Module boundary respect.** Cross-context импорты ТОЛЬКО через `apps.<ctx>.contracts` (Data Transfer Objects). Прямых импортов между `apps.identity_auth ↔ apps.events ↔ apps.rsvp` быть не должно. Enforcement через существующий `backend/.importlinter` (18 контрактов уже написаны).
4. **Minimal scope.** Skeleton ≠ implementation. Models с полями + indexes + RLS. Services с signatures + 1-2 строки docstring + `raise NotImplementedError`. Никакой реальной auth-логики (это W1 MVP), никакого Telegram OIDC adapter (~100 строк отдельный PR), никаких реальных endpoints (urls.py только healthz).

Ты не предлагаешь альтернативы стеку («может FastAPI?», «может Redis для cache?»). Стек frozen V1.2 — все альтернативы рассмотрены и отвергнуты в ADR-002/005/006/007. Если задача кажется требующей альтернативы — это знак прочитать соответствующий ADR ещё раз.

-----

## 2. Обязательное чтение перед началом

Self-contained brief: новая сессия не имеет контекста прошлых разговоров. Прочитай в указанном порядке:

### 2.1. Root context (mandatory, ~5 минут)

1. `/home/user/Act/CLAUDE.md` — frozen стек, 11 NON-NEGOTIABLE, конвенции, глоссарий. **Особое внимание:** NN #3 (ЮKassa only), NN #6 (magic link POST), NN #7 (PII encryption), NN #11 (RLS + PgBouncer), «Что Claude НЕ должен делать».
2. `/home/user/Act/README.md` — структура репо + Phase 0 → Phase 1 roadmap.

### 2.2. Architecture (mandatory секции, ~15 минут)

В `/home/user/Act/docs/ARCHITECTURE.md` прочитай **выборочно**:

| Секция | Строки (приблизительно) | Зачем |
|---|---|---|
| § 16 bounded contexts | 52–71 | Список 16 BC + cross-context принципы |
| § Стек (Уровень B) — Backend / ORM / Module boundary enforcement | 293–321 | Django 5.2 LTS обоснование + import-linter |
| § Compliance: 152-ФЗ / OWASP / Rate Limiting / Data Retention | 482–567 | Compliance-чек-лист |
| § Level C → UUID Strategy | 572–587 | UUIDv7 для PK write-heavy, UUIDv4/CSPRNG для tokens |
| § Level C → Outbox (cross-cutting infrastructure) | 589–713 | Outbox-таблица + service-pattern + Procrastinate task |
| § Level C → RLS Operational Constraints | 715–857 | **7 операционных правил RLS — критично** |
| § Level C → Identity & Auth | 858–961 | 7 таблиц + RLS policies + Cookie consent + PII Audit Log |
| § Level C → Events (включая Recurrence) | 963–971 | Сущности (skeleton-уровень достаточен) |
| § Level C → RSVP & Attendance | 973–1027 | services signatures + RLS policies |
| § Bootstrap → Phase 1 | 1687–1700 | **Точный scope Phase 1.4 — единственный источник истины** |

Можно пропустить: § Pilot Этап 0, § ADR-008–016 detail (только если нужно за конкретным решением), § Источники.

### 2.3. Per-context CLAUDE.md (mandatory, ~10 минут)

3 BC, на которые Phase 1.4 фокусируется:

1. `/home/user/Act/backend/apps/identity_auth/CLAUDE.md` — security-critical context, 7 entities + 7 приоритетов аутентификации.
2. `/home/user/Act/backend/apps/events/CLAUDE.md` — Events + Recurrence Engine context, RFC 5545.
3. `/home/user/Act/backend/apps/rsvp/CLAUDE.md` — RSVP & Attendance, guest-merge invariants.

Эти файлы автоматически load-ятся Claude Code при работе с файлами в соответствующих директориях, но прочитать их **явно перед началом** — обязательно, чтобы спланировать модели сразу правильно.

### 2.4. Existing scaffolding (mandatory, ~5 минут)

Файлы которые **уже существуют и НЕ переписывать**:

```bash
ls /home/user/Act/backend/                     # pyproject.toml, .importlinter, Dockerfile.dev, README.md, act/, apps/, scripts/, tests/
ls /home/user/Act/backend/apps/                # 16 BC dirs + core, все только __init__.py
cat /home/user/Act/backend/pyproject.toml      # Зависимости заморожены — НЕ менять
cat /home/user/Act/backend/.importlinter | head -50   # 18 контрактов: 1 на raw SQL + 16 BC + 1 outbox
cat /home/user/Act/docker-compose.yml          # Local PG (для будущего Phase 1.4.bis migrate run)
cat /home/user/Act/infra/postgres/init.sql     # PG роли act_app / act_admin создаются здесь
cat /home/user/Act/.env.example                # Environment variables blueprint
```

### 2.5. Skills (mandatory understanding, ~3 минуты)

Эти skills будут триггериться по описанию задач — **используй их через Skill tool, не пиши руками** (особенно RLS policies):

- `write-rls-policy` — при создании любой user-attributed модели. **Обязательно** для всех таблиц с user_id (User, Session, MagicLinkToken, OAuthIdentity, PasskeyCredential, ConsentRecord, EventParticipant, GuestRSVP).
- `create-migration` — если решишь создать миграции (но скорее всего НЕ нужно в этой итерации — миграции в 1.4.bis).
- `outbox-event` — НЕ нужно сейчас, но прочитай для понимания pattern, если будешь делать AuthEvent emit.

`ls /home/user/Act/.claude/skills/` — все 10 skills.

-----

## 3. Цели этой итерации (Definition of Done)

### 3.1. Главная цель — `python manage.py check` = 0 errors

Это primary acceptance criterion из `docs/iterations/iteration-5.5-roadmap.md` § 3 step #14. Detailed criteria:

1. `cd /home/user/Act/backend && python manage.py check` возвращает `System check identified no issues (0 silenced).`
2. `python manage.py check --deploy` warnings допустимы (production hardening — отдельный pass в W10), errors — недопустимы.
3. `python manage.py runserver --noreload 8000` поднимается без traceback (можно kill после 2 секунд).
4. `python manage.py makemigrations --dry-run --check` без unexpected miграций.
5. `cd /home/user/Act/backend && lint-imports` — все 18 контрактов import-linter pass.
6. `pytest --collect-only` без import errors (тесты не пишем, но collection должен работать).

### 3.2. Вторичные цели (deliverables)

| Категория | Файлы | Содержание |
|---|---|---|
| **Settings** | `backend/act/settings/{__init__,base,dev,prod}.py` | Layered — base импортит env, dev добавляет DEBUG/SQLite-fallback, prod использует DATABASE_URL_DIRECT для миграций |
| **WSGI/ASGI** | `backend/act/{wsgi,asgi,urls}.py` + `backend/manage.py` | Standard Django CLI entry-points |
| **Requirements** | `backend/requirements/{base,dev,prod}.in` + автогенерированные `.txt` через `uv pip compile` | Базируется на `pyproject.toml` (уже frozen); .in файлы выделяют dev/prod подсеты |
| **Core middleware** | `backend/apps/core/middleware/rls.py` + `csp.py` | RLS middleware из § Level C Identity & Auth (`SET LOCAL app.current_user_id` в `transaction.atomic()`); CSP — defaults из OWASP A06 |
| **Core utilities** | `backend/apps/core/rls/__init__.py` + `backend/apps/core/outbox/{models,services}.py` (stub) | RLS context manager; Outbox model + publish_event() stub |
| **3 BC scaffolds** | `backend/apps/{identity_auth,events,rsvp}/{models,services,contracts,admin,apps}.py` | По Level C — поля + indexes + RLS policies attached через Meta; services с signatures + `raise NotImplementedError`; contracts с pydantic DTOs |
| **django-allauth wiring** | `INSTALLED_APPS` + `AUTHENTICATION_BACKENDS` + базовый `urls.py` include `allauth.urls` | БЕЗ custom adapters — только default django-allauth setup |
| **Healthz endpoint** | `backend/apps/core/views.py` (`healthz`) + `backend/act/urls.py` | Возвращает `{"status": "ok", "version": "0.1.0"}` (200 OK); не проверяет DB |

### 3.3. Что **НЕ** делать в этой итерации

- **НЕ создавать кастомный Telegram OIDC adapter** (~100 строк — это W1 спринт, отдельный PR).
- **НЕ создавать миграции `apps/<ctx>/migrations/0001_initial.py`.** Phase 1.4.bis сделает это после `0001_extensions.py` через прямой PG.
- **НЕ запускать `python manage.py migrate`** — нет живого PG (compose опционален, но миграции — задача 1.4.bis).
- **НЕ создавать `0001_extensions.py`** — это отдельный шаг Phase 1.4.bis с явным `PG_BOUNCER_HOST=""` invocation.
- **НЕ писать unit-тесты** (Phase 1.4 → skeleton; W1+ покрывает тесты per-BC).
- **НЕ настраивать Sentry SDK init** (placeholder в settings, real DSN — Phase 1.1+).
- **НЕ устанавливать pre-commit hooks** (отдельная задача).
- **НЕ менять `pyproject.toml`** dependencies. Если требуется новый пакет — это знак, что задача вне scope Phase 1.4.
- **НЕ создавать `apps/<ctx>/CLAUDE.md`** для 10 BC без Level C (это Iteration 10 post-Pilot).
- **НЕ трогать `frontend/`** (Phase 1.5).
- **НЕ настраивать GitHub Actions** (Phase 1.6).

-----

## 4. Workflow (suggested order)

Не строгий, но рекомендуемый для минимизации rework:

### Шаг 1. Settings + manage.py + WSGI/ASGI (~1 час)

Создай:
1. `backend/manage.py` — стандартный Django CLI entry-point. `os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'act.settings.dev')`.
2. `backend/act/__init__.py` — пустой.
3. `backend/act/settings/__init__.py` — пустой (или re-export from base).
4. `backend/act/settings/base.py` — общие настройки. `INSTALLED_APPS` с 16 `apps.<ctx>` + `apps.core` + `django.contrib.*` + `allauth` + `allauth.account` + `allauth.socialaccount`. `MIDDLEWARE` с `apps.core.middleware.rls.RLSMiddleware` + `apps.core.middleware.csp.CSPMiddleware` + Django defaults. Database через `DATABASE_URL` env (использовать `dj-database-url`? — НЕТ, это не в pyproject; вместо парсить вручную или просто использовать `psycopg.conninfo`). **Альтернатива**: на этом этапе допускается hardcoded `DATABASES` через `os.environ['DATABASE_URL']` parsing вручную (~10 строк). `AUTH_USER_MODEL = 'identity_auth.User'`. `TIME_ZONE = 'Europe/Moscow'`. `USE_I18N = True`, `USE_TZ = True`. `LANGUAGE_CODE = 'ru'`, `LANGUAGES = [('ru', 'Russian'), ('en', 'English')]`.
5. `backend/act/settings/dev.py` — `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, fallback на SQLite если `DATABASE_URL` отсутствует (для `manage.py check` без live PG).
6. `backend/act/settings/prod.py` — `DEBUG = False`, `ALLOWED_HOSTS = os.environ['ALLOWED_HOSTS'].split(',')`, `DATABASES['default']` обязательно из env, `DATABASES['migrations']` использует `DATABASE_URL_DIRECT` (NN #11 — bypass PgBouncer), `DATABASES['admin']` использует `DATABASE_URL_ADMIN` (BYPASSRLS role для Django Admin).
7. `backend/act/urls.py` — root URL conf: `path('healthz/', healthz), path('accounts/', include('allauth.urls'))`. Никаких api routes сейчас.
8. `backend/act/wsgi.py` + `backend/act/asgi.py` — стандартные Django boilerplate.

**Verify Шаг 1:** `cd backend && DJANGO_SETTINGS_MODULE=act.settings.dev python manage.py check` должен PASS (возможно с warnings, но без errors).

### Шаг 2. Core infrastructure (~2 часа)

`backend/apps/core/` уже содержит `__init__.py`. Добавь:

1. `backend/apps/core/apps.py` — `class CoreConfig(AppConfig)`.
2. `backend/apps/core/middleware/__init__.py`.
3. `backend/apps/core/middleware/rls.py` — middleware который читает `request.user.id` и в `transaction.atomic()` делает `cursor.execute("SET LOCAL app.current_user_id = %s", [str(user_id)])`. Для anonymous — `SET LOCAL app.current_user_id = ''` или skip-atomic. **Code template:**

   ```python
   from django.db import transaction, connection

   class RLSMiddleware:
       def __init__(self, get_response):
           self.get_response = get_response

       def __call__(self, request):
           user_id = getattr(request.user, 'id', None) if request.user.is_authenticated else None
           if user_id is None:
               return self.get_response(request)
           # SET LOCAL живёт только внутри транзакции — оборачиваем весь request handler
           with transaction.atomic():
               with connection.cursor() as cursor:
                   cursor.execute("SET LOCAL app.current_user_id = %s", [str(user_id)])
               return self.get_response(request)
   ```

   **Важно:** этот код использует `connection.cursor()` — это допустимо, потому что middleware живёт в `apps.core.rls.*` (попадает под exception NN #11 + CONTRACT 0 import-linter). Если положишь его в `apps.core.middleware.rls` — переименуй package в `apps.core.rls.middleware` ИЛИ добавь его в `ignore_imports` в .importlinter CONTRACT 0 (но лучше первое — соблюдает naming convention).

4. `backend/apps/core/middleware/csp.py` — простой CSP middleware из OWASP A06 (defaults). `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...`. Можно использовать django-csp, но он не в `pyproject.toml` — лучше hand-roll (~20 строк).
5. `backend/apps/core/views.py` — `def healthz(request): return JsonResponse({"status": "ok", "version": "0.1.0"})`. Без DB-проверки.
6. `backend/apps/core/outbox/__init__.py`.
7. `backend/apps/core/outbox/models.py` — `class OutboxEvent(models.Model)` по схеме из `ARCHITECTURE.md` строки 595–625 (uuid PK через `default=uuid7` если есть Python helper, иначе UUIDv4 placeholder с TODO).
8. `backend/apps/core/outbox/services.py` — `def publish_event(*, event_type, aggregate_type, aggregate_id, payload) -> None:` который делает `OutboxEvent.objects.create(...)`. По § Level C → Outbox строки 631–653.

**Verify Шаг 2:** `python manage.py check` всё ещё PASS + `lint-imports` PASS (особенно CONTRACT 0 — raw SQL только в `apps.core.rls.*`).

### Шаг 3. apps.identity_auth — root BC (~2 часа)

Используй Skill tool с `write-rls-policy` для каждой RLS-таблицы. Создай:

1. `backend/apps/identity_auth/apps.py` — `class IdentityAuthConfig(AppConfig)`.
2. `backend/apps/identity_auth/models.py` — 7 моделей по `apps/identity_auth/CLAUDE.md` Entities table:
   - `User(AbstractBaseUser)` — id UUIDv7 PK (поле `id = models.UUIDField(primary_key=True, default=uuid4)` — placeholder; pg_uuidv7 будет в Phase 1.4.bis), `primary_email_encrypted` (django_cryptography encrypt(TextField())), `primary_email_hash` (CharField max_length=64, db_index=True для HMAC lookup), `phone_e164_encrypted`, `phone_e164_hash`, `telegram_id` (CharField unique nullable), `locale`, `country_code`, `city_id` (UUID nullable — FK on localization_city добавится после Iter 9), `status` (CharField choices), `created_at` (DateTimeField auto_now_add).
   - `Session` — server-side, `user_id` FK, `device_fingerprint`, `created_at`, `last_seen_at`, `expires_at`. RLS owner.
   - `MagicLinkToken` — `token_hash` (CharField unique — HMAC, не сам token), `user_id` FK, `created_at`, `expires_at` (15 min), `used_at` (nullable), `ip_hash`, `user_agent_hash`. RLS owner.
   - `OAuthProvider` — справочник (`name` PK = 'telegram' | 'vk' | 'yandex'). НЕ RLS.
   - `OAuthIdentity` — `user_id` FK, `provider_id` FK to OAuthProvider, `provider_uid` (encrypted + hashed). RLS owner. Unique (provider_id, provider_uid_hash).
   - `PasskeyCredential` — placeholder, пометить `# managed by django-otp-webauthn — реальная схема придёт с миграциями пакета в W1`. Просто проксирующий комментарий, не создавай поля.
   - `ConsentRecord` — `id UUIDv4`, `user_id` FK, `purpose` (CharField choices с 7 значениями из CLAUDE.md глоссария), `consent_text_hash` (CharField 64), `granted_at`, `withdrawn_at` (nullable), `ip_address` (GenericIPAddressField для аудита, не hash — РКН требует читаемый IP).
   - `AuthEvent` — append-only audit log, `actor_user_id` FK, `event_type`, `metadata` JSONField, `ip_address_hash`, `created_at`. RLS owner.
3. `backend/apps/identity_auth/contracts.py` — pydantic DTOs (pydantic уже в `pyproject.toml`? — если нет, использовать `dataclasses` для skeleton): `UserContract`, `SessionContract`, `ConsentContract`. Без sensitive полей (`primary_email_hash`, `phone_e164_hash` — допустимо для server-side lookup, но `*_encrypted` — НЕТ).
4. `backend/apps/identity_auth/services.py` — signatures по `apps/identity_auth/CLAUDE.md` § Conventions + 7 приоритетов. Минимум:
   - `def signup_with_telegram_oidc(*, telegram_id, locale, request_meta) -> UserContract: raise NotImplementedError("W1 sprint")`.
   - `def request_magic_link(*, email, request_meta) -> MagicLinkContract: raise NotImplementedError("W1 sprint")`.
   - `def verify_magic_link(*, token, request_meta) -> UserContract: raise NotImplementedError("W1 sprint, POST only — NN #6")`.
   - `def find_user_by_email(*, email: str) -> UserContract | None: ...` — placeholder с HMAC lookup pattern.
   - `def grant_consent(*, user_id, purpose, consent_text_hash, ip_address) -> ConsentContract: ...`.
   - `def withdraw_consent(*, user_id, purpose) -> None: ...`.
5. `backend/apps/identity_auth/admin.py` — `admin.site.register(User)` минимум. БЕЗ кастомных `ModelAdmin` (Phase W9 сделает custom moderation views).
6. `backend/apps/identity_auth/migrations/__init__.py` — пустой (миграции в 1.4.bis).

**Verify Шаг 3:** `python manage.py check` PASS; `python manage.py makemigrations --dry-run identity_auth` показывает миграции которые будут созданы (это OK — мы их не коммитим, проверка что models валидны).

### Шаг 4. apps.events + apps.rsvp (~2 часа)

Аналогично identity_auth, но проще (нет PII encryption):

**apps.events:**
- `Event` — id UUIDv7 PK, `owner_id` FK to identity_auth.User, `series_id` (nullable, на EventSeries), `title` (JSONField для i18n: `{"ru": "...", "en": "..."}`), `description` (JSONField), `country_id`, `city_id`, `location_text`, `starts_at` TIMESTAMPTZ, `ends_at` TIMESTAMPTZ, `capacity` (PositiveIntegerField nullable), `status` (CharField choices: draft/published/full/cancelled/completed), `format_tags` (ArrayField), `moderation_required` Boolean, `is_paid` Boolean, `price_kopecks` (BigIntegerField nullable), `currency` (CharField 3, default 'RUB'), `created_at`, `updated_at`. RLS: public для published, owner-only для draft.
- `EventSeries` — `id`, `owner_id` FK, `group_id` (nullable), `template` (JSONField — Event template), `rrule` (CharField 256 — RFC 5545), `exdates` (ArrayField of dates), `next_generation_at`, `status` (CharField). RLS owner.
- `RecurrenceOverride` — `series_id` FK, `recurrence_id` (TIMESTAMPTZ — конкретный instance datetime), `override_payload` (JSONField), `created_at`. RLS owner-of-series.
- `services.py`: `create_event(*, owner_id, ...) -> EventContract`, `publish_event(*, event_id, owner_id) -> EventContract`, `cancel_event(*, event_id, owner_id, reason) -> EventContract`. Все `raise NotImplementedError("W3 sprint")`.
- `contracts.py`: `EventContract`, `EventSeriesContract`.

**apps.rsvp:**
- `EventParticipant` — id, `user_id` FK to identity_auth.User, `event_id` FK to events.Event, `status` (CharField: applied/confirmed/waitlisted/declined/checked_in/no_show), `applied_at`, `confirmed_at` (nullable), `merged_from_guest_id` (UUID nullable — для guest-merge tracking). RLS: owner sees own, organizer sees per-event.
- `GuestRSVP` — id, `event_id` FK, `contact_channel` (CharField: email/telegram/phone), `contact_value_encrypted`, `contact_value_hash`, `display_name`, `status` (CharField: pending/going/declined), `merged_into_user_id` (UUID nullable — pointer после signup), `created_at`, `verified_at` (nullable — для email). RLS: visible-to-event-owner.
- `services.py`: signatures из `ARCHITECTURE.md` § Level C RSVP (`rsvp_signed_in`, `rsvp_as_guest`, `merge_guest_on_signup`). Все `raise NotImplementedError("W6 sprint")`.
- `contracts.py`: `ParticipantContract`, `GuestRSVPContract`.

**Verify Шаг 4:** `python manage.py check` PASS; `lint-imports` PASS (особенно CONTRACT 1: identity_auth не импортит из events/rsvp; CONTRACTS для events/rsvp — корректные).

### Шаг 5. Final verification + worklog (~30 мин)

Запусти полный verification suite:

```bash
cd /home/user/Act/backend
python manage.py check                          # 0 errors
python manage.py check --deploy                 # warnings OK, no errors
python manage.py runserver --noreload 8000 &    # background
sleep 2 && curl http://localhost:8000/healthz/ && kill %1   # 200 OK
python manage.py makemigrations --dry-run --check identity_auth events rsvp core   # показывает что было бы создано
lint-imports                                    # все 18 PASS
pytest --collect-only                           # collection без import errors
```

Все 7 команд PASS = Phase 1.4 готов.

-----

## 5. Защита от типовых ошибок

1. **Cross-context импорт.** Если в `apps/events/models.py` появляется `from apps.identity_auth.models import User` — это нарушение. Используй `from django.contrib.auth import get_user_model; User = get_user_model()` ИЛИ FK через string reference: `models.ForeignKey('identity_auth.User', on_delete=models.CASCADE)`.

2. **ORM в views.** Views (когда появятся) НЕ должны делать `Event.objects.filter(...)` — только через `apps.events.services.list_events(...)`. На этой итерации views = только healthz, поэтому риск низкий, но фиксируй паттерн с дня 1.

3. **RLS-таблица без FORCE + default_deny.** Каждая RLS-таблица обязана иметь:
   - `ENABLE ROW LEVEL SECURITY`
   - `FORCE ROW LEVEL SECURITY` (защищает от owner-of-table обхода)
   - RESTRICTIVE policy `default_deny` с `USING (false)` — fail-closed
   - PERMISSIVE policies для каждого разрешённого кейса
   
   В Django это делается через `class Meta: managed = False` (если SQL пишется вручную) ИЛИ через `RunSQL` в миграции. На этой итерации миграции не создаются — RLS DDL живёт **в виде комментариев в models.py** + skill `write-rls-policy` генерирует sql который пойдёт в Phase 1.4.bis migration. **НЕ забывай этот шаг для каждой таблицы**.

4. **`.raw()` вне `apps.core.rls.*`.** import-linter CONTRACT 0 это поймает в CI, но локально проверь: `grep -rn ".raw\|cursor.execute" backend/apps/ --include="*.py" | grep -v apps/core/rls` — должно быть пусто (кроме middleware RLS которое уже в core).

5. **Magic в `prefetch_related` / `select_related` на views/templates.** Эти оптимизации живут в `services.py` методах (например `services.list_events_for_discovery()` делает `.select_related('owner').prefetch_related('participants')`). Views получают уже-готовый DTO.

6. **AUTH_USER_MODEL ошибка.** Если не указать `AUTH_USER_MODEL = 'identity_auth.User'` в `base.py` ДО первой миграции — Django создаст default `auth_user` и потом отказывается переключаться. На этой итерации миграции не создаются, но `AUTH_USER_MODEL` всё равно ставится в settings (валидируется через `check`).

7. **`uuid7()` placeholder.** Python пакет `uuid-utils` или `uuid6` даёт `uuid7()` функцию. Если они не в `pyproject.toml` — на этой итерации использовать `uuid.uuid4` placeholder + `# TODO Phase 1.4.bis: switch to uuidv7 default via pg_uuidv7 extension`. НЕ добавляй новый пакет в `pyproject.toml` — это вне scope.

8. **CSP middleware слишком restrictive.** На skeleton-стадии оставь permissive defaults (`'unsafe-inline'` для script-src OK на dev). Tightening — отдельная задача в W10 security review.

9. **Forgotten `AppConfig`.** Каждый `apps/<ctx>/apps.py` должен содержать `class XxxConfig(AppConfig): default_auto_field = 'django.db.models.BigAutoField'; name = 'apps.identity_auth'`. Если забыть — Django не подхватит app даже с `INSTALLED_APPS`.

10. **Frozen стек compromise.** Если в процессе хочется добавить `redis`, `celery`, `fastapi`, `sqlalchemy`, `dj-database-url` — стоп. Это нарушение «Что Claude НЕ должен делать» в CLAUDE.md. Решение либо через существующий стек, либо через ADR-update (отдельная итерация, не Phase 1.4).

-----

## 6. Формат итогового ответа

В конце сессии:

1. **Executive summary** (≤ 10 строк): сколько файлов создано, сколько строк, какие команды verification прошли, какие — НЕ прошли (если есть).

2. **Files created table:**

   | Файл | Строк | Тип | Покрытие |
   |---|---|---|---|
   | `backend/manage.py` | ~15 | Entry-point | — |
   | `backend/act/settings/base.py` | ~120 | Settings layered | 16 BC + allauth + middleware |
   | ... | ... | ... | ... |

3. **Verification commands output:**

   ```
   $ python manage.py check
   System check identified no issues (0 silenced).
   
   $ lint-imports
   ...
   
   $ curl http://localhost:8000/healthz/
   {"status":"ok","version":"0.1.0"}
   ```

4. **Known limitations** (≤ 5 пунктов): что отложено на Phase 1.4.bis / W1 / W3 / W6 (миграции, реальный Telegram OIDC, реальные services impl).

5. **Next steps** для founder:
   - Локально: `git diff --stat`, проверить PR, merge.
   - Следующая итерация: Phase 1.4.bis (PG extensions migration), затем Phase 1.5 (Next.js skeleton) ИЛИ Phase 1.6 (import-linter в CI).

-----

## 7. Git workflow

Сессия Claude Code on the web автоматически:
1. Создаёт ветку `claude/<random-name>` от свежего main.
2. Коммитит изменения от твоего имени.
3. Пушит и открывает PR.

**Твоя задача:** коммитить **логическими порциями** (не один гигантский коммит). Suggested commit boundaries:

```
chore(backend): add Django manage.py + layered settings (Phase 1.4 step 1)
feat(backend/core): add RLS middleware + CSP middleware + outbox stub (Phase 1.4 step 2)
feat(backend/identity_auth): scaffold 7 models + contracts + services signatures (Phase 1.4 step 3)
feat(backend/events): scaffold Event + EventSeries + RecurrenceOverride (Phase 1.4 step 4a)
feat(backend/rsvp): scaffold EventParticipant + GuestRSVP (Phase 1.4 step 4b)
docs(changelog): record Phase 1.4 Django skeleton iteration
```

Каждый коммит должен оставлять `python manage.py check` в passing state — это позволит легко bisect-ить при regression.

После последнего коммита — `git push -u origin claude/<branch>`. PR откроется автоматически.

**CHANGELOG entry** (последний коммит): добавь в `docs/CHANGELOG.md` под `[Unreleased]` секцию:

```markdown
### Added (Phase 1.4 — Django skeleton)

- `backend/manage.py` + `backend/act/{wsgi,asgi,urls}.py` + `backend/act/settings/{base,dev,prod}.py` — Django CLI entry-points + layered settings (base→dev/prod).
- `backend/apps/core/middleware/rls.py` — RLS middleware (`SET LOCAL app.current_user_id` in `transaction.atomic()`); CSP middleware с OWASP defaults; healthz endpoint.
- `backend/apps/core/outbox/{models,services}.py` — OutboxEvent model + publish_event() stub (ADR-016).
- `backend/apps/identity_auth/{models,services,contracts,admin,apps}.py` — 7 entities (User, Session, MagicLinkToken, OAuthProvider, OAuthIdentity, PasskeyCredential placeholder, ConsentRecord, AuthEvent); все user-attributed таблицы с FORCE + default_deny RLS (через skill write-rls-policy).
- `backend/apps/events/{models,services,contracts,apps}.py` — Event + EventSeries + RecurrenceOverride scaffold.
- `backend/apps/rsvp/{models,services,contracts,apps}.py` — EventParticipant + GuestRSVP scaffold.
- All services.py methods are signatures с `raise NotImplementedError("W{N} sprint")`. Реальная реализация — в MVP-спринтах W1 (auth), W3 (events), W6 (RSVP).

### TODO (Phase 1.4.bis)

- `backend/apps/core/migrations/0001_extensions.py` — pgcrypto, btree_gist, pg_trgm, unaccent, pg_uuidv7 через прямой PG (NN #11).
- `backend/apps/<ctx>/migrations/0001_initial.py` — после extensions, через `PG_BOUNCER_HOST=""`.
- `infra/postgres/init.sql` обновить — добавить `app.current_user_id` GUC setup для RLS.
```

-----

## 8. После выполнения (для founder)

После merge PR с Phase 1.4 — next iteration roadmap:

1. **Phase 1.4.bis** (~1 час) — `backend/apps/core/migrations/0001_extensions.py` + run миграций через прямой PG. **Требует:** живой PG (либо локальный через `docker-compose up postgres`, либо Yandex Managed после Phase 1.1). Founder-driven, не AI: команды простые (`PG_BOUNCER_HOST="" python manage.py migrate`), но требуют env setup.
2. **Phase 1.5** (~3-4 часа AI) — Next.js skeleton с App Router + next-intl proxy + TypeScript strict. Можно запускать параллельно с 1.4.bis.
3. **Phase 1.6** (~1 час AI) — import-linter в GitHub Actions CI workflow. Требует Phase 1.2 (branch protection + secrets) — Founder-bound.

Промпт для Phase 1.5 будет в `prompts/phase-1.5-nextjs-skeleton.md` (создаётся после успешного Phase 1.4 merge).

-----

## Приложение — Quick checklist для founder перед запуском

- [ ] PR #3 (audit-fixes) merged в `main`. `git log main --oneline | head -3` показывает `fix(docs): resolve 9 pre-Phase 1 architecture inconsistencies`.
- [ ] Открыть новую Claude Code сессию из web UI (https://claude.ai/code) на репозитории `baryshevshot1/Act`.
- [ ] Модель: **Claude Opus 4.7**. Fast mode опционально (быстрее, без потери качества).
- [ ] Network policy: default (требуется доступ к PyPI для проверки версий пакетов).
- [ ] Скопировать этот промт целиком (всё содержимое файла `prompts/phase-1.4-django-skeleton.md`) в первое сообщение.
- [ ] Ожидать ~6-8 часов AI-работы (stream tool calls). Не прерывать середину Шага 3 или 4 (RLS DDL генерится skill-ом — атомарность важна).
- [ ] После завершения — `gh pr view <PR-number>` локально, проверить changes, merge через UI.
- [ ] Если ≥ 1 verification command FAIL в финальном отчёте — НЕ merge. Создать issue с трасс-логом и переоткрыть итерацию.

-----

*Конец промта Phase 1.4 — Django skeleton.*
