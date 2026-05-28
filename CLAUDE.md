# Act — CLAUDE.md

> **Этот файл — главный AI-контекст проекта.** Зафиксирован, краток (≤200 строк по рекомендации Anthropic Claude Code), не пересказывает остальное. Перед задачами по продукту читай `docs/PRODUCT.md`, перед задачами по коду/архитектуре — `docs/ARCHITECTURE.md`.

|Параметр              |Значение                                                                                     |
|----------------------|---------------------------------------------------------------------------------------------|
|**Версия документа**  |v1.3 + Wave 1 + Wave 2 + Wave 3 applied                                                      |
|**Текущая фаза**      |Pre-Phase 0 (Compliance baseline pending)                                                    |
|**Иерархия CLAUDE.md**|Root (этот файл) + `apps/<context>/CLAUDE.md` per-context (создаются после Phase 1 bootstrap)|
|**Версионирование**   |См. `docs/CHANGELOG.md` (Wave 1/2/3 history + ADR-005↔007 renumber note)                       |
|**Обновлено**         |2026-05-24                                                                                   |

## Проект одной строкой

Act — host-first web-платформа для поиска компании на совместные мероприятия. Архитектура: modular monolith из 16 bounded contexts. Соло-фаундер-ИП (РФ). Разработка через Claude Code (Opus 4.7 + Sonnet 4.6).

## Структура репозитория

```
act/
├── README.md                    # точка входа, quick-start, status
├── CLAUDE.md                    # этот файл — root AI-контекст
├── docs/
│   ├── PRODUCT.md               # стратегия, JTBD, V1.1 UX
│   └── ARCHITECTURE.md          # 16 контекстов, Level C, 16 ADR, Bootstrap
├── prompts/                     # переиспользуемые промты для Claude Code
├── backend/                     # Django 5.2 (создаётся в Phase 1)
│   ├── apps/
│   │   ├── core/                # RLS middleware, outbox, shared utils
│   │   │   └── CLAUDE.md        # per-context (создаётся в Phase 1)
│   │   ├── identity_auth/
│   │   │   ├── CLAUDE.md        # per-context
│   │   │   ├── services.py      # ORM-доступ ТОЛЬКО здесь
│   │   │   ├── contracts.py     # public DTOs для cross-context
│   │   │   └── ...
│   │   ├── events/              # (Level C готов)
│   │   ├── rsvp/                # (Level C готов)
│   │   ├── contacts_sharing/    # (Level C готов)
│   │   ├── recommendations/     # (Level C готов, stub на MVP)
│   │   ├── localization/        # (Level C готов)
│   │   └── ...                  # ещё 10 контекстов (Level C — после Pilot)
│   ├── manage.py
│   └── .importlinter            # запреты cross-context импортов + .raw() вне core.rls
├── frontend/                    # Next.js 16 App Router (создаётся в Phase 1)
└── infra/                       # Coolify + GitHub Actions конфиги
```

## Стек (frozen V1.2 — не предлагать альтернативы)

- **Backend:** Django 5.2 LTS + Python 3.12
- **Frontend:** Next.js 16 App Router + next-intl + TypeScript
- **Database:** PostgreSQL 17 (Yandex Managed Service)
- **ORM:** Django ORM (raw SQL через `.raw()` / `connection.cursor()` **ТОЛЬКО** в `apps.core.rls.*` модулях — enforced через `import-linter` контракт, см. «RLS Operational Constraints» в `docs/ARCHITECTURE.md`)
- **Background jobs:** Procrastinate 3.8 на Postgres-backend. **NEVER** suggest Celery/Redis.
- **Cache / Session / Rate limiter:** in-Postgres. **NEVER** suggest Redis managed на MVP.
- **Search:** PostgreSQL FTS (tsvector + GIN). **NEVER** suggest Elasticsearch/Meilisearch.
- **File storage:** Yandex Object Storage (S3-compat)
- **CDN:** Yandex CDN. **NEVER** assume Cloudflare/AWS edges работают в РФ.
- **Auth:** django-allauth (Telegram OIDC primary, magic-link fallback) + django-otp + django-otp-webauthn (passkeys). **NEVER** propose Clerk / Auth0 / Supabase Auth.
- **Encryption:** PyCA `cryptography` + custom `apps.core.crypto.EncryptedField` + Yandex Lockbox (KMS) для PII полей (ADR-014 revised 2026-05-28; ранее `django-cryptography-django5` — отвергнут R6 как stale fork). **NEVER** использовать pgcrypto для application encryption — ключ в plain в БД.
- **Hosting:** Yandex Cloud Compute + Coolify. **NEVER** assume Vercel / Heroku / AWS managed.
- **CI/CD:** GitHub Actions + self-hosted runner на Yandex Compute. Plan B — Forgejo Actions при блокировке.
- **Email ESP:** UniSender или SendPulse (RU). **Never** Postmark/SendGrid as primary (трансграничная передача ПДн).
- **SMS:** SMS.ru (domestic). Telegram Gateway — только при наличии ст. 12 consent.
- **Telegram Bot:** aiogram 3.x — только для users с ст. 12 consent.
- **Analytics:** PostHog self-hosted.
- **Error tracking:** Sentry self-host или GlitchTip.
- **APM/logs:** LGTM-стек (Grafana + Prometheus + Loki).
- **Module boundary enforcement:** import-linter (`.importlinter`).
- **Testing:** pytest + pytest-django + factory_boy (backend); Playwright (E2E); Vitest + Storybook (фронт, позже).
- **iOS strategy:** PWA + Telegram Mini App на старте. RN+Expo+RuStore — после PMF (Phase 5). **NEVER** предполагать App Store distribution на MVP.

## Common commands

```bash
# Bootstrap (one-time)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements/dev.txt
pnpm install --filter frontend

# DB migrations — ВСЕГДА через прямой PG, минуя PgBouncer
PG_BOUNCER_HOST="" python backend/manage.py migrate

# Tests + lint (pre-commit)
cd backend && pytest && lint-imports        # import-linter
cd frontend && pnpm test && pnpm typecheck && pnpm lint

# Procrastinate worker (background jobs)
python backend/manage.py procrastinate worker

# Local dev (после Phase 1)
docker-compose up -d postgres                # локальный PG
python backend/manage.py runserver
cd frontend && pnpm dev
```

## Конвенции кода

- **Modular monolith.** 16 bounded contexts под `backend/apps/`. Список — в [`docs/ARCHITECTURE.md#16-bounded-contexts`](./docs/ARCHITECTURE.md#16-bounded-contexts).
- **Cross-context calls ТОЛЬКО** через `apps.<ctx>.contracts` (DTOs). Прямые импорты между контекстами запрещены и проверяются `import-linter` в CI.
- **ORM-доступ ТОЛЬКО** в `services.py`. Views / route handlers / templates **MUST NOT** обращаться к ORM напрямую — только через сервисный слой.
- **RLS обязательна** для всех таблиц с user-attributed данными (Identity, Sessions, Passkeys, ConsentRecord, ContactShare, VerificationDocument, GuestRSVP, UserContactChannel, EventParticipant, Rating, RecommendationsScoreCache). На каждой RLS-таблице: `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy. См. «RLS Operational Constraints».
- **Datetimes:** `TIMESTAMPTZ` в БД (UTC), конвертация в locale — в сервисах или фронте.
- **Migrations:** атомарные. Никаких data-migrations внутри schema-migration. Прогон **только через прямой PG**, не через PgBouncer.
- **UUID:** UUIDv7 для PK write-heavy таблиц (Events, RSVP, Notifications, AuditLog, Outbox). UUIDv4 / `secrets.token_urlsafe()` — для session/CSRF/magic-link токенов. **Никогда** UUIDv7 для токенов — predictability риск.
- **Cross-context коммуникация для side-effects** — **только через таблицу `outbox_event`** (transactional outbox, ADR-016). В той же транзакции, что и mutation, пишется запись в outbox; Procrastinate worker poll-ит и доставляет subscribers (~5s latency, at-least-once). Django signals остаются только для intra-context concerns (validation, denormalization внутри одного `apps.<ctx>/`). Никаких прямых cross-context вызовов вне `contracts.py`.

## Глоссарий / Ubiquitous Language (DDD)

|Термин                           |Определение                                                                                                                                                                                                                                                                                                                      |
|---------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Event                            |Конкретный экземпляр встречи (одна дата).                                                                                                                                                                                                                                                                                        |
|EventSeries                      |Родитель recurring; правило по RFC 5545 (RRULE / EXDATE / RECURRENCE-ID).                                                                                                                                                                                                                                                        |
|RecurrenceOverride               |Изменение конкретного instance из series.                                                                                                                                                                                                                                                                                        |
|EventParticipant                 |RSVP залогиненного User.                                                                                                                                                                                                                                                                                                         |
|GuestRSVP                        |RSVP без аккаунта (по email / Telegram-handle / phone). Сливается в EventParticipant при signup через `merge_guest_on_signup`.                                                                                                                                                                                                   |
|ConsentRecord                    |Отдельный документ согласия по 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025. Purposes: `core_processing`, `marketing`, `contact_sharing`, `cross_border_transfer`, `cookies_essential`, `cookies_analytics`, `cookies_marketing`.                                                                                                    |
|Group                            |Постоянное сообщество (контейнер для Event и Series).                                                                                                                                                                                                                                                                            |
|ReputationScore                  |Производная метрика; взвешенное среднее с учётом recency, sample size, weight рейтера.                                                                                                                                                                                                                                           |
|Wedge                            |Стартовое сужение: одна категория × одна география. На старте — тренеры регулярных групп × Москва.                                                                                                                                                                                                                               |
|NSM                              |North Star Metric: Confirmed Weekly Attendances (RSVP с фактическим check-in за неделю).                                                                                                                                                                                                                                         |
|**RLS Operational Constraints**  |Свод обязательных правил для всех RLS-таблиц: `transaction.atomic()` + `SET LOCAL`, `FORCE ROW LEVEL SECURITY`, RESTRICTIVE `default_deny` policy, отдельная BYPASSRLS-роль для Admin, запрет `.raw()` вне `apps.core.rls.*`. См. `docs/ARCHITECTURE.md#rls-operational-constraints`.                                            |
|**`default_deny`**               |RESTRICTIVE policy `USING (false)` на каждой RLS-таблице, гарантирует fail-closed default; PERMISSIVE policies «открывают» доступ для известных кейсов. См. ADR-006; pattern доказан в Alasco engineering blog (2024-03-28).                                                                                                       |
|**`act_app`**                    |Основная DB-роль приложения (без `BYPASSRLS`, подчиняется RLS). Используется в `DATABASES['default']`.                                                                                                                                                                                                                           |
|**`act_admin`**                  |DB-роль для Django Admin с `BYPASSRLS`. Используется в `DATABASES['admin']`. Все mutations через эту роль ОБЯЗАТЕЛЬНО логируются в `audit_log_pii_access`.                                                                                                                                                                       |
|**Pre-pilot Compliance baseline**|Pre-Phase 0 чек-лист: РКН-уведомление ст. 22 + ст. 12 + Privacy Policy + отдельный документ согласия + cookie consent UI. **Блокер** для production-публикации. См. ADR-012.                                                                                                                                                     |
|**`outbox_event`**               |Таблица единственного канала cross-context коммуникации (ADR-016). Mutation основной агрегатной таблицы + запись в `outbox_event` происходят в одной транзакции; Procrastinate worker poll-ит и доставляет subscribers. At-least-once delivery; consumer-side идемпотентность через `event.id` как dedupe key. Retention 30 дней.|
|**`audit_log_pii_access`**       |Wave 3 (planned): таблица централизованного логирования чтений PII-полей admin / moderator / service. Retention 1 год.                                                                                                                                                                                                           |

## NON-NEGOTIABLE (compliance + санкции)

1. **152-ФЗ ст. 18.** Первичная обработка ПДн граждан РФ — **ТОЛЬКО** на серверах в РФ. Никаких US/EU-managed-сервисов для пользовательских данных.
1. **152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025.** Согласие на обработку ПДн — **ОТДЕЛЬНЫЙ** документ, не вложенный чекбокс «согласен с правилами».
1. **Платежи.** No Stripe. No Clerk billing. No Convex Pro. ЮKassa для РФ — единственный платёжный путь на MVP. (основание: ADR-005)
1. **Хостинг.** No Vercel managed. No Heroku. No AWS edges как primary. Yandex Cloud + Coolify.
1. **iOS.** Through Phase 5 — только PWA + Telegram Mini App. App Store distribution требует зарубежного юр.лица и отложен до Phase 6+.
1. **Magic links / OAuth.** Не логинить на GET — link-preview боты (Telegram WebpageBot, Microsoft SafeLinks) сожгут токен. Логин на POST после явного клика. (источники industry pattern: supertokens.com/blog/magiclinks, etodd.io/2026/03/22/magic-link-pitfalls)
1. **PII шифрование.** Phone / email / verification documents — encrypted at rest через `apps.core.crypto.EncryptedField` (PyCA Fernet + MultiFernet keyring). Audit log всех чтений PII-полей обязателен. (основание: ADR-014 revised — `cryptography` + Yandex Lockbox; `audit_log_pii_access` — Wave 3 planned)
1. **Real-time не делаем.** На MVP — polling 30s на event-страницах. WebSocket / Centrifugo — отложено до Phase 5+ при наличии конкретного use case.
1. **Трансграничная передача (ст. 12 152-ФЗ).** Telegram Bot API / Telegram Gateway = ТППД (получатель Telegram FZ-LLC, ОАЭ; серверы NL/SG). Все формы signup ДОЛЖНЫ иметь отдельный opt-in чекбокс на использование Telegram-каналов; `ConsentRecord(purpose='cross_border_transfer')` обязательна. Без согласия — fallback на SMS.ru / Web Push / email через UniSender. **Никогда** не вызывать Telegram API без проверки consent. См. ADR-013.
1. **РКН-уведомления (ст. 22 + ст. 12 152-ФЗ).** ДВА разных уведомления, не путать. Подаются ДО первой production-публикации сайта (Pre-pilot Compliance baseline). Штраф за неподачу по ст. 22 — 100 000–300 000 ₽ для ИП (ч. 10 ст. 13.11 КоАП с 30.05.2025), 50%-скидка не действует. См. ADR-012.
1. **RLS-контекст и PgBouncer.** `SET LOCAL app.current_user_id` обязательно внутри `transaction.atomic()` — PgBouncer transaction-pooling возвращает connection в pool после COMMIT, без LOCAL это cross-tenant leak. Каждая RLS-таблица: `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy. См. «RLS Operational Constraints» в `docs/ARCHITECTURE.md`. (основание: ADR-006; industry source: pganalyze.com/blog/postgres-row-level-security-django-python)

## Что Claude НЕ должен делать

- Не предлагать миграцию на микросервисы. Modular monolith — осознанный выбор (см. ADR-001).
- Не предлагать Stripe / Clerk / Convex / Supabase / Vercel managed / AWS managed. Все они либо несовместимы с 152-ФЗ ст. 18, либо имеют billing через Stripe, который не работает для ИП РФ.
- Не использовать ORM в views/handlers. Только через `services.py`.
- Не делать cross-context прямых импортов. Только через `apps.<ctx>.contracts`.
- Не использовать `prefetch_related` / Django-magic за пределами сервисного слоя — это размывает границы и усложняет миграцию ORM.
- Не предлагать Elasticsearch / Meilisearch до p95 > 500ms на discovery feed (мониторится).
- Не предлагать Celery / Redis до >1000 jobs/min (нескоро на 10K MAU).
- Не использовать `[Г]` / `[?]` пометки как факты при принятии решений.
- Не предлагать UI-kit (Tailwind / shadcn / собственный) — это отложено до пилота.
- Не предлагать ML-персонализацию discovery feed — отложено до >10K MAU.

## Workflow при появлении задачи

1. **Сначала прочитать релевантный раздел `docs/`.** Перед продуктовой задачей — `PRODUCT.md`, перед архитектурной/кодом — `ARCHITECTURE.md`.
1. **Сверить со стеком и конвенциями выше.** Если задача предлагает что-то из «NEVER» — стоп, сначала обсудить с фаундером.
1. **Compliance check (если задача касается ПДн или нового источника/получателя данных):** ведёт ли изменение к расширению категорий ПДн в реестре РКН (ст. 22 ч. 7 — уточнение в течение 10 рабочих дней)? Появляется ли новый зарубежный получатель → нужно ли отдельное согласие на ТППД (ст. 12)? Создаётся ли новое PII-поле → ENCRYPT_AT_REST + audit_log_pii_access?
1. **Один PR = один bounded context** (контекст помещается в один промпт). Cross-context изменения дробить.
1. **Перед коммитом:** import-linter, pytest, django-silk (N+1 check), RLS-policy review (FORCE + default_deny на новых таблицах).
1. **Эпистемическая дисциплина:** факты — со ссылкой; всё что хочется ввести как гипотезу — помечать `[Г]`.

## Текущая фаза

**Pre-Phase 0 — Compliance baseline pending.** Перед Phase 1 (Bootstrap) обязательно выполнить чек-лист из ADR-012 (РКН ст. 22, ст. 12, Privacy Policy, отдельный документ согласия, cookie consent UI). До получения регистрации РКН — никаких production-релизов; ожидаемый срок проверки — до 30 дней.

После compliance baseline идут: Phase 1 (Bootstrap, 3–7 дней) → Pilot Этап 0 (5–7 дней, эмпирическая валидация стека через Accept-Rate ≥ 60% на core-flow) → ADR-007 commit/rollback → MVP-спринты W1–W10 (web only, RU only, Москва, wedge: тренеры регулярных групп).

См. подробно: [`docs/ARCHITECTURE.md#pilot-этап-0`](./docs/ARCHITECTURE.md#pilot-этап-0) и [`docs/ARCHITECTURE.md#pre-pilot-compliance-baseline-блокер-для-phase-1`](./docs/ARCHITECTURE.md#pre-pilot-compliance-baseline-блокер-для-phase-1).

## Версия и источники

- Документация собрана из V1.0 (Уровень A), V1.1 (Addendum, 23 мая 2026), V1.2 + V1.3 (24 мая 2026).
- Все факты сохранены с источниками в подробных файлах в `docs/`.
- При расхождении этого файла с `docs/` — приоритет у `docs/` (там полный контекст).