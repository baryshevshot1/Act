# Research request — Act Phase 1.5-1.7 prep + Yandex Managed PG extensions

> **Назначение.** Self-contained research-промт для **параллельной AI-сессии** (ChatGPT / Gemini 2 / Claude.ai с web-search). Не для Claude Code в репозитории — это исследовательская задача с web-fetch, выполняется ВНЕ репо. Founder копирует весь файл (от первой строки до маркера END) в outside-LLM.
>
> **Цель.** Снять 5 открытых технических вопросов, блокирующих Phase 1.4.bis (PG extensions migration), Phase 1.5 (Next.js skeleton), Phase 1.7 (Procrastinate worker) и W1 sprint (Telegram OIDC auth).
>
> **Дата запроса:** 2026-05-28.
> **Дата завершения Phase 1.4:** 2026-05-28 (merged PR #5).

-----

## Context — что такое Act (если LLM не знает)

Act — host-first web-платформа для поиска компании на совместные мероприятия (российский аналог Luma с фокусом на recurring series + per-event RSVP confirmation). Соло-фаундер ИП в РФ. Modular monolith из 16 bounded contexts.

**Текущий статус (frozen V1.2 стек):**

- Backend: **Django 5.2 LTS** + Python **3.12** + PostgreSQL **17**.
- Frontend: **Next.js 16 App Router** + **next-intl** + TypeScript.
- Database hosting: **Yandex Managed Service for PostgreSQL** (Yandex Cloud, регион ru-central1).
- Background jobs: **Procrastinate 3.8+** на Postgres-backend (`procrastinate[django]>=3.8` в pyproject.toml).
- Auth: **django-allauth >= 65.0**, primary social provider — **Telegram** (Russian compliance: Telegram FZ-LLC ОАЭ requires ст. 12 152-ФЗ ТППД consent).
- Module boundary enforcement: import-linter.
- Compliance: 152-ФЗ ст. 18 (первичная обработка ПДн в РФ — НЕЛЬЗЯ AWS/Vercel/Stripe).

**Что уже сделано в repository (для контекста):**

- 16 BC scaffolded под `backend/apps/` (3 BC с моделями: `identity_auth`, `events`, `rsvp`).
- 7 моделей в `apps/identity_auth/models.py` (User AUTH_USER_MODEL, Session, MagicLinkToken, OAuthProvider, OAuthIdentity, PasskeyCredential placeholder, ConsentRecord, AuthEvent). Поля UUIDv7 PK сейчас `default=uuid.uuid4` placeholder.
- RLS middleware в `apps/core/rls/middleware.py` (`SET LOCAL app.current_user_id` в `transaction.atomic()`).
- Outbox stub в `apps/core/outbox/` (ADR-016 transactional outbox).
- Layered settings (`act.settings.{base,dev,test,prod}`); prod fail-fast на отсутствии `DATABASE_URL_DIRECT` (для миграций минуя PgBouncer) и `DATABASE_URL_ADMIN` (для act_admin BYPASSRLS Django Admin).

**Все 5 вопросов влияют на конкретный код, который будет писаться в ближайшие 1-3 недели.** Нужны конкретные ответы, не общие рекомендации.

-----

## Format требований к ответу

1. **Каждый факт — со ссылкой (URL + дата публикации).** Если ссылку проверить нельзя, помечай `[?]`. Без ссылки = гипотеза, помечай `[Г]`.
2. **Verbatim quotes для critical facts** (compat matrix, breaking changes, deprecation notices). НЕ парафраз.
3. **Conservative recommendations.** Если в источнике нет данных, скажи «не нашёл» — не выдумывай.
4. **Дата проверки источника** обязательна (источник 2024 года — менее ценный чем 2026).
5. **Ответ структурируй** строго по 5 секциям (R1-R5) ниже, с подсекциями: `Findings`, `Sources`, `Recommendation for Act`, `Confidence (high/medium/low)`.

-----

## R1. `pg_uuidv7` extension в Yandex Managed PostgreSQL 17 allowlist

### Вопрос

Доступен ли `pg_uuidv7` extension (https://github.com/fboulnois/pg_uuidv7) в Yandex Managed Service for PostgreSQL 17 на дату May 2026?

### Зачем

Act использует UUIDv7 для PK всех write-heavy таблиц (Events, RSVP, Notifications, AuditLog, Outbox — см. `docs/ARCHITECTURE.md` § UUID Strategy). UUIDv7 даёт ~12× speedup на INSERT и ~24% меньше index size на 50M+ rows vs UUIDv4 ([F: credativ.de/en/blog/postgresql-en/a-deeper-look-at-old-uuidv4-vs-new-uuidv7-in-postgresql-18]).

Два пути реализации:
- **(a)** `pg_uuidv7` extension в PG → `DEFAULT uuidv7()` clause в DDL миграции. Простой код, но требует extension allowlist.
- **(b)** Python-side: `uuid-utils` или `uuid6` package → `default=uuidv7` в Django models. Работает без extension, но `DEFAULT` clause в DDL не работает.

Сейчас в моделях `default=uuid.uuid4` placeholder с TODO. Phase 1.4.bis миграция должна резолвить TODO.

### Что проверить

1. **Список allowed extensions в Yandex Managed PG 17** — публичная документация. URL: docs.yandex.cloud/en/managed-postgresql/concepts/extensions (или RU-вариант).
2. Если `pg_uuidv7` в списке — версия?
3. Если НЕ в списке — есть ли возможность запросить добавление (форма / support tickets / времянка)?
4. Альтернативно: **Yandex Managed PostgreSQL 18 availability** — релиз PG 18 был сентябрь 2025. Если доступен в Yandex Managed → нативный `uuidv7()` без extension. Снимает R1 полностью.

### Acceptance criteria для ответа

- Прямая ссылка на Yandex docs allowlist с датой проверки.
- Verdict: `pg_uuidv7` ∈ {available, not_available, can_request, unknown}.
- Если `not_available` — оценка вероятности `can_request` через support (5/10/30 дней SLA?).
- PG 18 availability: `available_now / coming_q3_2026 / unknown`.

-----

## R2. Django-allauth Telegram OIDC adapter — готовый pip-package или custom?

### Вопрос

Существует ли поддерживаемый pip-package для интеграции **Telegram Login / Mini App auth** в **django-allauth 65.x**, или нужно писать кастомный SocialAccount adapter?

### Зачем

W1 sprint Act (Identity & Auth) реализует Telegram OIDC как primary auth method (см. NN #6 в CLAUDE.md). 7 приоритетов аутентификации:
1. **Telegram OIDC** primary
2. VK ID secondary
3. Yandex ID secondary
4-5. Apple / Google deferred (sanctions)
6. Email magic link fallback
7. Phone OTP

Сейчас в `apps/identity_auth/models.py` есть `OAuthProvider` справочник с {telegram, vk, yandex} и `OAuthIdentity` (user ↔ provider_uid). Реальный adapter в W1 — оценка ~100 строк в Phase 1.4 промте, но это hypothesis.

### Что проверить

1. **django-allauth official providers list** — https://docs.allauth.org/en/latest/socialaccount/providers/index.html. Есть ли Telegram?
2. **Community-maintained packages:**
   - `django-telegram-login` (PyPI, last release date?)
   - `python-telegram-login` (PyPI)
   - `allauth-telegram` (PyPI)
   - Другие варианты в GitHub topic `django-allauth-provider`?
3. **Telegram Login Widget vs Telegram Mini App auth** — различия. Какой подходит для Act (web app, не bot inside Telegram)?
4. **Maintenance status** — last commit < 6 months back, > 50 stars, opened issues responded?
5. **Compatibility** с django-allauth 65.x (major version 65 был релиз ~Q1 2026).

### Acceptance criteria

- Список 2-5 кандидатов с last-release-date, stars, last-commit, compat-with-allauth-65.
- Verdict: `best_choice` + почему.
- Если best_choice = «write custom» — примерный scope (LOC, источники reference impl типа examples в django-allauth для других providers).

-----

## R3. next-intl 4.x + Next.js 16 — `proxy` vs `middleware` pattern

### Вопрос

Какой паттерн integration **next-intl 4.x** с **Next.js 16 App Router** рекомендуется на дату May 2026 — старый `middleware.ts` подход или новый proxy/wrapper-based pattern?

### Зачем

Phase 1.5 (Next.js skeleton) blocker. В Act roadmap (`docs/iterations/iteration-5.5-roadmap.md` step #16) явно прописано «next-intl proxy (не middleware) — Next 16». Это намёк на breaking change в Next.js 16 middleware Edge runtime. Нужны конкретные code patterns + источники.

### Что проверить

1. **next-intl docs** — https://next-intl-docs.vercel.app/ (или https://next-intl.dev — главный домен мог переехать). Раздел «Setup» / «Routing».
2. **Next.js 16 release notes** — https://nextjs.org/blog (релиз был ~Q4 2025). Найти breaking changes в:
   - Edge middleware
   - App Router conventions
   - `i18n` config
3. **Какой actual API в next-intl 4.x:**
   - `createMiddleware` (старый, был в next-intl 3.x)?
   - `createNavigation` / `createSharedPathnamesNavigation`?
   - Proxy через `next.config.mjs` `experimental.proxy` или ServerComponents-only?
4. **Migration guide** next-intl 3.x → 4.x — если он есть.
5. **TypeScript strict mode** + next-intl — есть ли gotchas с `useTranslations` типизацией?
6. **Code sample** для `[locale]/(public)(authenticated)(organizer)/page.tsx` структуры из roadmap.

### Acceptance criteria

- Минимум 1 verbatim code snippet рекомендованного pattern для **Next.js 16 + next-intl 4.x**.
- Verdict: `setup_pattern` ∈ {middleware_legacy, proxy_new, server_only, custom}.
- Если proxy_new — конкретно где живёт код (next.config.mjs / middleware.ts / app/layout.tsx).
- Список 2-3 production projects на GitHub с актуальной integration (для reference).

-----

## R4. Procrastinate 3.8 совместимость с Django 5.2 LTS + Python 3.12

### Вопрос

Поддерживает ли **Procrastinate 3.8+** Django 5.2 LTS (релиз апрель 2025) и Python 3.12 на дату May 2026? Какая версия рекомендуется для production?

### Зачем

Act использует Procrastinate как замену Celery (NN: NEVER Celery/Redis на MVP — `pyproject.toml` фиксирует `procrastinate[django]>=3.8`). Phase 1.7 запускает worker + periodic-task (Recurrence Engine 21-day generation, Outbox poller).

### Что проверить

1. **Procrastinate official docs / GitHub**: https://procrastinate.readthedocs.io / https://github.com/procrastinate-org/procrastinate.
2. **CHANGELOG.md** — какие версии поддерживают Django 5.2.
3. **Compatibility matrix** — Python 3.12 + Django 5.2 + Procrastinate 3.8/3.9/4.0.
4. **Breaking changes 3.x → 4.x** (если 4.x уже релизнут) — стоит ли target-ить 4.x?
5. **PgBouncer compatibility** — Procrastinate использует LISTEN/NOTIFY который НЕ работает в PgBouncer transaction-pooling. Какой workaround? (session-pooling для worker connection? отдельный pool?).
6. **Periodic tasks syntax** в 3.8 — `@app.periodic(cron='*/5 * * * *')` или другой?

### Acceptance criteria

- Verbatim quote из CHANGELOG или docs про Django 5.2 support.
- Recommended version pin для production.
- PgBouncer workaround pattern с источником.
- Periodic-task syntax snippet.

-----

## R5. Дополнительно — Yandex Managed PG 17 → PG 18 upgrade path

### Вопрос

Если на сейчас в Yandex Managed только PG 17, есть ли публично анонсированный таймлайн на PG 18 (с нативным `uuidv7()`)?

### Зачем

Снимает зависимость от R1 (`pg_uuidv7` extension). PG 18 нативно поддерживает `uuidv7()`. Если roadmap Yandex Cloud в Q3 2026 включает PG 18 — можно отложить extension setup.

### Что проверить

1. **Yandex Cloud blog** / **roadmap announcements** — последние новости PG версий.
2. **Cloud-status changelog** — yandex.cloud/changelog или аналог.
3. **Russian-language tech-news** (Habr, vc.ru) — анонсы новых PG-версий.

### Acceptance criteria

- Verdict: PG 18 в Yandex Managed = {available_now, q3_2026, q4_2026, not_announced}.
- Link to announcement, если есть.

-----

## Что НЕ нужно исследовать (out of scope этого промта)

- Yandex Cloud pricing (не блокирует разработку — отдельная задача founder).
- РКН uvedomlenija ст. 22 / ст. 12 (compliance, не tech research).
- Apple Sign-In / Google Sign-In (deferred до Phase 6+ per Act CLAUDE.md NN #5).
- ML personalization для discovery (deferred до >10K MAU per ADR-008).
- iOS native (PWA + Telegram Mini App до Phase 5+).

## Финальный формат ответа

Структура (markdown):

```
# Research findings — Act Phase 1.5-1.7 prep
> Date: <ваша дата проверки>; Sources verified through <дата>.

## R1. pg_uuidv7 в Yandex Managed PG 17
### Findings
<...>
### Sources
- [URL — дата]
### Recommendation for Act
<verdict + concrete next action>
### Confidence: high/medium/low + почему

## R2. django-allauth Telegram adapter
<same structure>

## R3. next-intl 4.x + Next.js 16
<same structure>

## R4. Procrastinate compat
<same structure>

## R5. PG 18 в Yandex Managed
<same structure>

## Summary table

| # | Vопрос | Verdict | Confidence | Action for Act |
|---|---|---|---|---|
| R1 | pg_uuidv7 в YMC PG17 | ... | ... | ... |
| ... | ... | ... | ... | ... |
```

-----

*END of research request. Скопируй файл с заголовка «Research request» до этой строки в outside LLM.*
