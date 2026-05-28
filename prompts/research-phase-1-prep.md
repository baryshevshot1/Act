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

1. **Web search ОБЯЗАТЕЛЬНО включён.** Это research-задача, не recall из training. Если твоя сессия не имеет web access — скажи это в первой строке и остановись. Не отвечай из памяти.
2. **Каждый факт — со ссылкой (URL + дата публикации источника, не дата проверки).** Если ссылку проверить нельзя — `[?]`. Без ссылки = гипотеза, помечай `[Г]`.
3. **Verbatim quotes для critical facts** (compat matrix, breaking changes, deprecation notices, version numbers). Парафраз = `[Г]`. Если quote невозможен — пиши «not found in accessible sources».
4. **Conservative recommendations.** Если в источниках нет данных — пиши **`not found`**. Не выдумывай данные про Yandex Cloud (особый риск fabrication для R1, R5) и не reconstruct из training data 2024-го.
5. **Дата публикации источника** обязательна. Источник 2023-2024 годов — менее ценный чем 2025-2026. Если только старые источники доступны — помечай confidence = `low`.
6. **Source quality tiering:** ★★★ official docs / CHANGELOG / GitHub release notes; ★★ maintainers blog / RFC / verified tech-news; ★ Reddit / Hacker News / Stack Overflow — only as secondary signal с явной пометкой `community`. AI-summarized content (Perplexity-snippets etc.) — `[?]`.
7. **Дата проверки источника** (= когда ты открывал URL) обязательна.
8. **Язык ответа:** русский preferred (для consistency с Act docs); английский OK для verbatim quotes.
9. **Time budget:** активный research ~45-90 минут. Не уходи rabbit holes ниже 3-click depth.
10. **Ответ структурируй** строго по 5 секциям (R1-R5) ниже, с подсекциями: `Findings`, `Sources`, `Recommendation for Act`, `Confidence (high/medium/low)` + обязательный `Summary table` в конце.
11. **Recommendation должна быть directly actionable** — конкретный package + version + URL ИЛИ конкретный code pattern + источник. Не subjective opinion.

-----

## R1. `pg_uuidv7` extension в Yandex Managed PostgreSQL 17 allowlist

### Вопрос

Доступен ли `pg_uuidv7` extension (https://github.com/fboulnois/pg_uuidv7) в Yandex Managed Service for PostgreSQL 17 на дату May 2026?

### Зачем

Act использует UUIDv7 для PK всех write-heavy таблиц (Events, RSVP, Notifications, AuditLog, Outbox — см. `docs/ARCHITECTURE.md` § UUID Strategy). UUIDv7 даёт ~12× speedup на INSERT и ~24% меньше index size на 50M+ rows vs UUIDv4 ([F: credativ.de/en/blog/postgresql-en/a-deeper-look-at-old-uuidv4-vs-new-uuidv7-in-postgresql-18]).

Три пути реализации:
- **(a)** `pg_uuidv7` extension в PG → `DEFAULT uuidv7()` clause в DDL миграции. Простой код, но требует extension allowlist.
- **(b)** Python-side: `uuid-utils` или `uuid6` package → `default=uuidv7` в Django models. Работает без extension, но `DEFAULT` clause в DDL не работает.
- **(c)** Compromise: `gen_random_uuid()` (UUIDv4) DEFAULT через `pgcrypto` (уже в allowlist для всех managed PG; см. ADR-006) сейчас + миграция на UUIDv7 в W3+ когда extension/PG 18 будут доступны. Acceptable trade-off для MVP scale (<1M rows).

Сейчас в моделях `default=uuid.uuid4` placeholder с TODO. Phase 1.4.bis миграция должна резолвить TODO.

### Что проверить

1. **Список allowed extensions в Yandex Managed PG 17** — публичная документация. URLs (проверить оба):
   - EN: `https://yandex.cloud/en/docs/managed-postgresql/operations/extensions/cluster-extensions`
   - RU: `https://yandex.cloud/ru/docs/managed-postgresql/operations/extensions/cluster-extensions`
   - Альтернативные: `docs.yandex.cloud` (старый домен), `cloud.yandex.ru` (legacy).
2. Если `pg_uuidv7` в списке — версия + дата добавления (если указана).
3. Если **НЕ** в списке:
   - Yandex Cloud public roadmap (`yandex.cloud/ru/roadmap` или blog tag «managed-postgresql»).
   - GitHub issues `yandex-cloud/docs` upon "pg_uuidv7" requests.
   - Yandex Cloud Community форум / Telegram-канал announcements (если есть).
   - Support tickets — самообслуживание: какой SLA на «request new extension»?
4. **Yandex Managed PostgreSQL 18 availability** (snimaет R1): см. R5 ниже, но для R1 acceptance criteria указать.
5. **Cross-check** — есть ли Yandex Managed PG roadmap-обещание Q1/Q2/Q3 2026 на extension expansion? Поиск по `yandex managed postgresql changelog 2026` + Habr posts.
6. **Geo caveat:** Yandex Cloud docs могут быть достижимы через `.com/en/` или `.ru/`. Если EN-зеркало пустое — проверь RU-домен.

### Acceptance criteria для ответа

- Прямая ссылка на Yandex docs allowlist (URL живой, дата проверки).
- Verdict для `pg_uuidv7`: `{available_with_version, not_available, can_request_with_sla, unknown}`.
- Если `not_available` — оценка вероятности `can_request` через support: SLA (если найден в Yandex SLA matrix).
- PG 18 availability: `{available_now, coming_Q3_2026, coming_Q4_2026, not_announced}` (cross-ref R5).
- **Если все три пути (a/b/c) viable — какой recommend?** Конкретный verdict, не «зависит».

-----

## R2. Django-allauth Telegram auth — готовый pip-package или custom?

### Вопрос

Существует ли поддерживаемый pip-package для интеграции **Telegram Login Widget** в **django-allauth 65.x**, или нужно писать кастомный adapter? Какой flow выбрать: Login Widget vs Mini App `initData`?

### Зачем

W1 sprint Act (Identity & Auth) реализует Telegram auth как primary auth method (см. NN #6 в CLAUDE.md). 7 приоритетов аутентификации:
1. **Telegram** primary (web — Login Widget; Telegram Mini App — `initData` parsing)
2. VK ID secondary
3. Yandex ID secondary
4-5. Apple / Google deferred (sanctions)
6. Email magic link fallback
7. Phone OTP

**CRITICAL:** Telegram **не использует OAuth 2.0 / OIDC** в строгом смысле — это HMAC-SHA256 verified callback. Это другой flow чем VK ID / Yandex ID. Промт переименован с «Telegram OIDC» на «Telegram auth» для точности.

Сейчас в `apps/identity_auth/models.py` есть `OAuthProvider` справочник с {telegram, vk, yandex} и `OAuthIdentity` (user ↔ provider_uid). Реальный adapter в W1 — оценка ~100 строк, но это hypothesis.

### Что проверить

1. **Telegram official auth spec** (ground truth для verification logic):
   - Login Widget HMAC verification: `https://core.telegram.org/widgets/login` секция «Checking authorization».
   - Mini App `initData` verification: `https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app`.
   - **Различия flow** — Login Widget даёт user_id + auth_date hash через GET-redirect; Mini App даёт `initDataUnsafe` через JS bridge inside Telegram client. Разные endpoints, разные verification, разные UX.
   - Для Act выбор: **Login Widget** primary (web app в браузере); Mini App — Phase 5+ (отложено per NN #5).
2. **django-allauth official providers list** — `https://docs.allauth.org/en/latest/socialaccount/providers/index.html`. Есть ли Telegram нативно (не было на 64.x)?
3. **django-allauth GitHub discussions** — `https://github.com/pennersr/django-allauth/discussions` + Issues — search «telegram». Что рекомендуют maintainers?
4. **Community-maintained packages** (поиск на PyPI + GitHub):
   - `django-telegram-login` — PyPI last release date, stars, opened issues.
   - `python-telegram-login` — PyPI.
   - `allauth-telegram` / `django-allauth-telegram` — PyPI.
   - GitHub topic `django-allauth-provider`, `telegram-auth`.
5. **Maintenance health-check** для каждого кандидата:
   - Last commit ≤ 12 months (Telegram API стабилен, но Django/allauth major bumps часты).
   - Open issues с маркером «django 5» или «allauth 6x» — responded?
   - PyPI downloads / month > 1k (signal активности).
6. **Compatibility check** с django-allauth 65.x (релиз ~Q1 2026):
   - Provider plugin API могло меняться между 64.x → 65.x — проверь changelog.
7. **Reference impl examples** в django-allauth для других «not-strictly-OAuth» providers (e.g. ORCID, или custom HMAC-based) — для оценки scope custom adapter.

### Acceptance criteria

- Список 2-5 кандидатов с {last-release, stars, last-commit-date, compat-with-allauth-65, downloads/month}.
- Verdict: `{ready_package_X, custom_adapter, hybrid}` + почему.
- Если `custom_adapter` — примерный scope (LOC) + ссылка на reference impl в django-allauth examples (URL).
- Verbatim quote Telegram HMAC verification algorithm (для будущей impl).
- Подтверждение: **Mini App auth flow — отложен до Phase 5+** (не путать с Login Widget).

-----

## R3. next-intl 4.x + Next.js 16 — `proxy` vs `middleware` pattern

### Вопрос

Какой паттерн integration **next-intl 4.x** с **Next.js 16 App Router** рекомендуется на дату May 2026 — старый `middleware.ts` подход или новый proxy/wrapper-based pattern?

### Зачем

Phase 1.5 (Next.js skeleton) blocker. В Act roadmap (`docs/iterations/iteration-5.5-roadmap.md` step #16) явно прописано «next-intl proxy (не middleware) — Next 16». Это намёк на breaking change в Next.js 16 middleware Edge runtime. Нужны конкретные code patterns + источники.

### Что проверить

1. **next-intl current latest version** на дату May 2026 — может быть 4.x ИЛИ 5.x (релиз дат непредсказуем). Проверь PyPI-аналог: `npm view next-intl version` или https://www.npmjs.com/package/next-intl.
2. **next-intl docs** — основной домен меняется:
   - `https://next-intl.dev` (canonical с 2024)
   - `https://next-intl-docs.vercel.app/` (legacy)
   - Разделы для проверки: «Getting started → App Router setup», «Routing → setRequestLocale», «Migration» (если есть major upgrade).
3. **Next.js 16 release notes** — `https://nextjs.org/blog` (релиз ~Q4 2025). Breaking changes в:
   - Edge middleware (новые runtime ограничения?).
   - App Router conventions (новые file conventions?).
   - Legacy `i18n` config в `next.config.js` — был deprecated ещё в Next 13 для App Router, проверить статус в Next 16.
   - Image optimization domains config (если меняли).
4. **Конкретный recommended setup pattern** для Next.js 16 + next-intl latest:
   - Где живёт locale routing logic? `middleware.ts` (если jstill supported) ИЛИ wrapper в `app/layout.tsx` ИЛИ proxy hook в `next.config.mjs`?
   - `createMiddleware` (next-intl 3.x API) — deprecated в 4.x/5.x?
   - `createNavigation` (новый API в next-intl 4.x) — обязательный или optional?
   - `setRequestLocale` для Server Components — обязательно ли в каждом `page.tsx`?
5. **Migration guides** между major versions — next-intl 3.x → 4.x, и 4.x → 5.x если применимо.
6. **TypeScript strict mode** + next-intl:
   - `useTranslations` типизация — нужен ли `messages.ts` declaration file?
   - JSON schema for translation files (avoid runtime missing-key errors).
7. **Code sample** для Act layout: `app/[locale]/(public)/page.tsx` + `app/[locale]/(authenticated)/dashboard/page.tsx` + `app/[locale]/(organizer)/events/new/page.tsx` (route groups в App Router; `[locale]` dynamic segment).
8. **App-router-only setup** (без legacy `pages/`) — единственный путь для Act; убедись что рекомендованный pattern поддерживает this configuration.
9. **Russian plurals (CLDR)** — next-intl ICU MessageFormat supports `one/few/many/other` для русского? Reference: `https://cldr.unicode.org/index/cldr-spec/plural-rules`.

### Acceptance criteria

- Verbatim version numbers: Next.js 16.{minor} + next-intl {major}.{minor}.
- Минимум 2 verbatim code snippets рекомендованного pattern (routing + page-level usage).
- Verdict: `setup_pattern` ∈ {middleware_only, middleware_plus_wrapper, wrapper_only, server_only, custom}.
- Конкретно файлы где живёт code (`middleware.ts` / `app/[locale]/layout.tsx` / `next.config.mjs` / `i18n.ts`).
- Список 2-3 production GitHub projects с актуальной (≤ 6 months) integration. URL + последний commit к i18n коду.
- Подтверждение Russian plurals поддержки (verbatim или example).

-----

## R4. Procrastinate 3.8 совместимость с Django 5.2 LTS + Python 3.12

### Вопрос

Поддерживает ли **Procrastinate 3.8+** Django 5.2 LTS (релиз апрель 2025) и Python 3.12 на дату May 2026? Какая версия рекомендуется для production?

### Зачем

Act использует Procrastinate как замену Celery (NN: NEVER Celery/Redis на MVP — `pyproject.toml` фиксирует `procrastinate[django]>=3.8`). Phase 1.7 запускает worker + periodic-task (Recurrence Engine 21-day generation, Outbox poller).

### Что проверить

1. **Procrastinate official docs / GitHub**:
   - `https://procrastinate.readthedocs.io` (или `https://procrastinate.org` — canonical может изменяться).
   - `https://github.com/procrastinate-org/procrastinate`.
2. **Latest stable version** на дату May 2026. Procrastinate 3.x активен; есть ли 4.x?
3. **CHANGELOG.md** — verbatim entry про Django 5.2 LTS support.
4. **Compatibility matrix** — Python 3.12 + Django 5.2 + Procrastinate {3.8 / 3.9 / 4.0 / latest}.
5. **Breaking changes** между major versions (если 4.x релизнут) — стоит ли target-ить latest или pin на 3.x?
6. **Sync vs Async API:**
   - Django 5.2 — в основном sync (async views — opt-in).
   - Procrastinate имеет async API. Документация рекомендует sync API для Django sync project? `@app.task` синхронный?
   - Если только async — это блокер для Act (W6 RSVP services — все sync).
7. **PgBouncer compatibility** — Procrastinate использует LISTEN/NOTIFY который **НЕ работает** в PgBouncer transaction-pooling. Workarounds:
   - Session-pooling для worker connection (отдельный pool config)?
   - Polling-mode fallback (без NOTIFY)? Performance impact на ≤5s latency требование Outbox?
   - Direct PG bypass для worker?
8. **Periodic tasks syntax** в latest version (Outbox poller — main use case):
   - `@app.periodic(cron='*/5 * * * * *')` ИЛИ `@app.task + @periodic`?
   - Cron-syntax: 5-field или 6-field (with seconds)?
   - Поддержка sub-minute intervals (Outbox требует ≤5s polling)?
9. **Management command** `python manage.py procrastinate worker` — current syntax + flags (concurrency, queue selection).
10. **Outbox-poller pattern** в Procrastinate — есть ли best-practice docs про polling-style worker для transactional outbox? Альтернатива: PG LISTEN/NOTIFY-driven.

### Acceptance criteria

- Verbatim quote из CHANGELOG или docs про Django 5.2 LTS support (или его отсутствие).
- Recommended version pin для production (e.g. `procrastinate[django]==X.Y.*`).
- Sync API confirmation (`@app.task def my_task(): ...` без async).
- PgBouncer workaround pattern с источником URL + verbatim config snippet.
- Periodic-task syntax snippet for ≤5s polling.
- Management command invocation для worker (verbatim).
- **Если Procrastinate 3.8+ НЕ поддерживает Django 5.2** — recommended fallback: какая Procrastinate version совместима с Django 5.2 LTS?

-----

## R5. Дополнительно — Yandex Managed PG 17 → PG 18 upgrade path

### Вопрос

Если на сейчас в Yandex Managed только PG 17, есть ли публично анонсированный таймлайн на PG 18 (с нативным `uuidv7()`)?

### Зачем

Снимает зависимость от R1 (`pg_uuidv7` extension). PG 18 нативно поддерживает `uuidv7()`. Если roadmap Yandex Cloud в Q3 2026 включает PG 18 — можно отложить extension setup.

### Что проверить

1. **Yandex Cloud blog** / **roadmap announcements** — последние новости PG версий:
   - `https://yandex.cloud/ru/blog` (поиск «PostgreSQL»).
   - `https://yandex.cloud/ru/roadmap` (если страница существует).
2. **Cloud-status changelog** — `https://yandex.cloud/ru/docs/release-notes/` (или аналог).
3. **Russian-language tech-news** — Habr posts (поиск «Yandex Managed PostgreSQL 18»), vc.ru, CNews.
4. **In-place upgrade vs new-cluster migration path**:
   - Yandex Managed PG 16 → 17 — был доступен in-place upgrade или только pg_dump + restore в новый кластер?
   - Этот pattern будет применён для 17 → 18.
   - Документация: `yandex.cloud/ru/docs/managed-postgresql/operations/cluster-version-update` (если есть).
5. **Major version upgrade SLA** в Yandex Managed — downtime expected? Maintenance window?
6. **pg_uuidv7 в PG 18** — нужен ли вообще extension? PG 18 native `uuidv7()` — `https://www.postgresql.org/docs/18/functions-uuid.html` (verify).

### Acceptance criteria

- Verdict: PG 18 в Yandex Managed = `{available_now, planned_Q3_2026, planned_Q4_2026, planned_2027, not_announced}`.
- Link to announcement, если есть.
- Upgrade path 17 → 18: `{in_place_supported, new_cluster_only, unknown}`.
- Подтверждение PG 18 native `uuidv7()` syntax (verbatim из PostgreSQL docs).

-----

## Что НЕ нужно исследовать (out of scope этого промта)

- Yandex Cloud pricing (не блокирует разработку — отдельная задача founder).
- РКН uvedomlenija ст. 22 / ст. 12 (compliance, не tech research).
- Apple Sign-In / Google Sign-In (deferred до Phase 6+ per Act CLAUDE.md NN #5).
- ML personalization для discovery (deferred до >10K MAU per ADR-008).
- iOS native (PWA + Telegram Mini App до Phase 5+).
- Coolify / self-hosted PaaS feature comparison (отдельный research после Phase 1.4.bis).
- Email ESP comparison UniSender vs SendPulse (founder decision D6, не tech research).

## Возможные follow-up research (НЕ в этом промте — упомянуть кратко если время позволяет)

- **R6 [optional]:** `django-cryptography-django5 >= 2.0` compat с Django 5.2 + Python 3.12. Используется в Act для PII field encryption (ADR-014). Если v2 ломан — нужна замена.
- **R7 [optional]:** `django-otp-webauthn >= 0.3` + `django-otp >= 1.5` compat с Django 5.2. Passkeys в W1+ (см. NN #6).
- **R8 [optional]:** `import-linter >= 2.1` + `forbidden` contract — best practices для checking subpackages of external packages. Phase 1.4 hit `Invalid forbidden module django.db.backends.utils` ошибку; workaround — добавить `django` в root_packages. Есть ли cleaner approach?

Если у тебя осталось время после R1-R5 — добавь короткие 5-line answers для R6/R7/R8. Если нет — пропускай.

## Финальный формат ответа

Структура (markdown):

```
# Research findings — Act Phase 1.5-1.7 prep
> Date: <ваша дата проверки YYYY-MM-DD>; Web search: enabled/disabled; LLM: <name>.

## Executive summary (≤ 10 строк)
- R1 verdict: ...
- R2 verdict: ...
- ... 
- Critical blockers (если есть): ...

## R1. pg_uuidv7 в Yandex Managed PG 17
### Findings
<facts со ссылками; verbatim quotes для critical>
### Sources (★★★/★★/★ tiering)
- ★★★ [URL — дата публикации; дата проверки]
- ★★ ...
### Recommendation for Act
<directly actionable: package + version + URL ИЛИ code pattern + источник>
### Confidence: high/medium/low — обоснование (число источников, их свежесть, наличие verbatim quote)

## R2-R5: same structure

## R6/R7/R8 (если время позволяет): ≤ 5 строк each

## Summary table

| # | Вопрос | Verdict | Confidence | Action for Act | Sources count |
|---|---|---|---|---|---|
| R1 | pg_uuidv7 в YMC PG17 | ... | ... | ... | N |
| R2 | django-allauth Telegram | ... | ... | ... | N |
| R3 | next-intl + Next.js 16 | ... | ... | ... | N |
| R4 | Procrastinate compat | ... | ... | ... | N |
| R5 | PG 18 в YMC | ... | ... | ... | N |

## Critical signals to surface

В отдельной секции укажи:
- **Fabrication risk areas** — где у тебя был соблазн заполнить gap из памяти, но удержался?
- **Stale sources** (только 2023-2024) — какие answers строятся на старых данных?
- **Unanswerable questions** — на что не нашёл ответа после reasonable effort? Не симулируй уверенность.
- **Contradictions** — где источники противоречат друг другу? Какие?

## Self-check перед отправкой

Перед тем как finalize ответ, verify:
- [ ] Web search был использован (не recall из training)?
- [ ] Каждый «факт» имеет URL + дата публикации?
- [ ] Verbatim quotes для compat matrix / breaking changes (НЕ парафраз)?
- [ ] Recommendations directly actionable (package + version, не «depends on»)?
- [ ] Yandex Cloud answers (R1, R5) подтверждены official Yandex docs (не Habr-rephrasing)?
- [ ] Confidence levels откалиброваны (high требует ≥ 2 ★★★ источника)?
- [ ] Указал что НЕ нашёл — там где данных нет?
```

-----

*END of research request. Скопируй файл с заголовка «Research request» до этой строки в outside LLM. Если LLM не имеет web search — попроси переключиться на ChatGPT с search ON, Claude.ai с web search tool, ИЛИ Gemini 2 с Google search integration. Без web search этот промт бесполезен — все ответы будут гипотезами из training data.*
