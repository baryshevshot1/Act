# Act — Glossary (Ubiquitous Language)

> Алфавитный глоссарий 40+ терминов из `CLAUDE.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`. Единый источник истины для domain language (DDD).
> При расхождении определений в этом файле и 4 main files — приоритет у `CLAUDE.md` § Глоссарий (raw verbatim).
> Категории: **Domain** (бизнес-сущности), **Architecture** (паттерны), **Compliance** (152-ФЗ + санкции), **Metrics** (KPIs), **Stack** (технологии), **Process** (Phase / Iteration / Pilot).

## A

**Accept-Rate** *(Metric)*. Главный KPI Pilot Этап 0: доля PR от Claude Code, принятых founder-ом без существенных правок (> 20 строк ручной правки = «существенная»). Target ≥ 60% per `[Г]`. Источник: `docs/ARCHITECTURE.md` § Pilot Этап 0.

**`act_admin`** *(Stack)*. DB-роль для Django Admin с `BYPASSRLS`. `DATABASES['admin']`. Все mutations через эту роль ОБЯЗАТЕЛЬНО логируются в `audit_log_pii_access`. См. RLS Operational Constraints #4.

**`act_app`** *(Stack)*. Основная DB-роль приложения **без `BYPASSRLS`**, подчиняется RLS. `DATABASES['default']`.

**ADR (Architecture Decision Record)** *(Architecture)*. MADR 4.0 формат: Status / Context / Decision / Alternatives / Consequences / Triggers пересмотра. 16 ADR-001..016 готовы. Skill: `.claude/skills/write-adr/`. **Renumbering запрещён** — см. ADR-005↔007 history note.

**ADR-007** *(Architecture)*. Stack commit gate после Pilot Этап 0. Pending — Decision принимается на основе Accept-Rate ≥ 60% + ≤ 10 import-linter violations + 10 risk checks. См. ADR-007 verbatim.

**`audit_log_pii_access`** *(Compliance)*. Wave 3 (planned) таблица централизованного логирования чтений PII-полей admin / moderator / service. Retention 1 год. Требование 152-ФЗ ст. 7.

**AuthEvent** *(Domain)*. Append-only audit log в identity_auth BC; запись на каждый login / logout / signup / password_change. Wave 1+ extension (не из PDF V1.3 verbatim).

## B

**Bounded Context (BC)** *(Architecture)*. DDD концепт: автономный модуль с собственной моделью домена и явной границей. Act = 16 BC под `backend/apps/<ctx>/`. Cross-context calls — только через `apps.<ctx>.contracts`. См. ADR-001.

**Boltzmann pattern** *(Process)*. Anthropic пэттерн: сохранять промты как «portable long-term memory» в `prompts/` репо, чтобы future Claude Code сессии могли восстановить контекст. См. `prompts/README.md`.

## C

**Cold-start liquidity** *(Metric / Strategic)*. Главный риск маркетплейса: новому участнику нечего смотреть, новому организатору некому показать. S3 trigger: < 30 активных еженедельных серий за 4 недели в Этапе 3 = failure. Mitigation — synthetic supply через KudaGo + ручной outreach 50-100 тренеров.

**Coolify** *(Stack)*. PaaS-overlay на Yandex Compute (ADR-004). Open-source alternative to Heroku/Railway. Используется для deploy production-сайта Act.

**Compliance baseline** *(Compliance)*. Pre-Phase 0 чек-лист (5 пунктов): РКН ст. 22 + ст. 12 + Privacy Policy + отдельный документ согласия + cookie consent UI. **БЛОКЕР** для production-публикации. См. ADR-012.

**ConsentRecord** *(Domain / Compliance)*. Отдельный документ согласия по 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025. Purposes: `core_processing`, `marketing`, `contact_sharing`, `cross_border_transfer`, `cookies_essential`, `cookies_analytics`, `cookies_marketing`.

**ContactShare** *(Domain)*. Bilateral consent-based grant раскрытия `UserContactChannel` другому participant на конкретный Event. RLS обеспечивает взаимность (recipient видит только если оба granted).

**Cross-border transfer (ТППД)** *(Compliance)*. 152-ФЗ ст. 12. Telegram Bot API / Telegram Gateway = ТППД (Telegram FZ-LLC, ОАЭ; серверы NL/SG). Требует отдельное opt-in согласие + уведомление РКН. ADR-013.

## D

**`default_deny`** *(Architecture / Compliance)*. RESTRICTIVE policy `USING (false)` на каждой RLS-таблице, fail-closed default. PERMISSIVE policies «открывают» доступ для известных кейсов. См. ADR-006; pattern proven by Alasco engineering blog (2024-03-28).

**Discovery & Search** *(Domain)*. Каталог Events: Country → City → Category → Format. Ранжирование per ADR-008 (weighted sum, НЕ multiplicative).

**DPO (Data Protection Officer)** *(Compliance)*. Ответственный за обработку ПДн. Сам ИП-founder per Act-config; ст. 22.1 152-ФЗ не требует обязательного DPO для соло-ИП без специальных категорий ПДн.

## E

**Event** *(Domain)*. Конкретный экземпляр встречи (одна дата). Owned by organizer. Может быть standalone или часть `EventSeries`.

**EventSeries** *(Domain)*. Родитель recurring; правило по RFC 5545 (RRULE / EXDATE / RECURRENCE-ID). Skill: `.claude/skills/recurrence-rrule/`.

**EventParticipant** *(Domain)*. RSVP залогиненного User. Statuses: `applied`, `confirmed`, `waitlist`, `declined`, `checked_in`, `no_show`.

**Expand-Contract pattern** *(Stack)*. Zero-downtime migration в 4 шага: Expand (add nullable) → Backfill → Switch → Contract (drop old). `docs/ARCHITECTURE.md` § DB Migration Strategy. Skill: `create-migration`.

**Expression index** *(Stack)*. Postgres index на JSONB lookup-by-locale (`(localized_names->>'ru-RU')`). Быстрее GIN для типичного lookup-by-current-locale. Skill: `add-translation`.

## F

**Failed approach** *(Process)*. Anthropic Boltzmann pattern: фиксируем tried-and-rejected approaches в `docs/CHANGELOG.md` § Failed approaches, чтобы Claude Code не возвращался. Примеры: pgcrypto encryption, multiplicative ranking, Django signals для cross-context.

**FORCE ROW LEVEL SECURITY** *(Stack / Compliance)*. Postgres clause; без него owner таблицы (роль `act_app`) bypass'ит политику. Default Postgres allows table-owner bypass; FORCE это закрывает. Обязательно на каждой RLS-таблице (RLS Operational Constraints #2).

## G

**Group** *(Domain)*. Постоянное сообщество (контейнер для Event и Series). Publishing rules per ADR-009 (`owner_only` / `members_moderated` / `members_open`).

**GuestRSVP** *(Domain)*. RSVP без аккаунта (по email / Telegram-handle / phone). Сливается в `EventParticipant` при signup через `merge_guest_on_signup` (PDF V1.3 sec 20.4). Skill: `guest-rsvp-merge`.

## I

**ICU MessageFormat** *(Stack)*. Стандарт для i18n strings с plural / select / number / date formatting. Used by next-intl 4.x. **Russian REQUIRES four plural forms** (one/few/many/other). См. Level C Localization.

**`import-linter`** *(Stack)*. Декларативный enforcement архитектурных границ (`.importlinter` файл). 18 contracts: 16 BC isolation + no-raw-sql + cross-context outbox. Запускается в CI.

## J

**JTBD (Jobs-To-Be-Done)** *(Process)*. Theory of customer needs. Act имеет 8 JTBD; **JTBD-2** = тренеры регулярных групп = wedge primary. См. `docs/jtbd-bc-mapping.md`.

## M

**MADR 4.0** *(Architecture)*. Markdown Architecture Decision Records template. Адаптирован для Act: Status · Context · Decision · Alternatives · Consequences · Триггеры пересмотра. См. `docs/ARCHITECTURE.md` § ADR + skill `write-adr`.

**Magic link** *(Stack)*. Email-based passwordless auth. 256-bit CSPRNG token, 15 min TTL, one-time, IP / UA binding. **POST после явного клика** (NN #6, не GET — link-preview боты сожгут token).

**`merge_guest_on_signup`** *(Domain)*. Service function в rsvp BC: при signup пользователя матчит существующие `GuestRSVP` по (channel, value_hash) и конвертирует в `EventParticipant`. Idempotent. **Только после verify контакт-канала** (impersonation prevention).

**Modular Monolith** *(Architecture)*. Архитектурный подход: один деплой, одна БД, но строгие границы между BC через import-linter. ADR-001. Альтернатива микросервисам для соло-фаундера.

## N

**`next-intl`** *(Stack)*. Next.js 16 i18n library. 4.x использует proxy (не middleware) для App Router. Async Server Components → `await getTranslations(namespace)`.

**Notifications** *(Domain)*. Email transactional, push (web push в MVP), in-app inbox. ADR-010 NotificationDelivery FSM с `acknowledged` как NSM ground truth (НЕ `opened` из-за Apple MPP).

**NSM (North Star Metric)** *(Metric)*. Confirmed Weekly Attendances — RSVP с фактическим check-in за неделю. Главная метрика продукта.

## O

**OWASP Top 10:2025** *(Compliance)*. Mapping таблица в `docs/ARCHITECTURE.md`. Все 10 категорий имеют конкретные mitigation в стеке Act (RLS для A01, django-cryptography для A02, и т.д.).

**`outbox_event`** *(Architecture)*. Таблица **единственного канала cross-context коммуникации** (ADR-016). Mutation основной агрегатной таблицы + запись в `outbox_event` происходят в одной транзакции; Procrastinate worker poll-ит и доставляет subscribers. At-least-once delivery; consumer-side идемпотентность через `event.id` как dedupe key. Retention 30 дней. Skill: `outbox-event`.

## P

**Phase 0** *(Process)*. Legal + Tooling (1-2 недели): ИП + расчётный счёт + РКН + домен + Privacy Policy + Consent doc + Email ESP. Founder-bound (не AI-task).

**Phase 1 (Bootstrap)** *(Process)*. 3-7 дней: Yandex Cloud setup + GitHub + Django/Next.js skeleton + extensions migration + Coolify + cost monitoring. Iteration 8 docs нужны для эффективного Phase 1.4.

**Pilot Этап 0** *(Process)*. 5-7 рабочих дней эмпирической валидации стека на one end-to-end core-flow. Single procedure, превращающая теоретический выбор стека в emprical commit (ADR-007).

**Pre-pilot Compliance baseline** *(Compliance)*. См. **Compliance baseline**.

**Procrastinate** *(Stack)*. Postgres-backed background jobs library. Заменяет Celery+Redis для соло-стека (ADR-006). Используется для Recurrence Engine generation + outbox poller + cost monitoring cron.

## R

**RFC 5545** *(Stack / Domain)*. iCalendar specification. Defines RRULE / EXDATE / RECURRENCE-ID для recurring events. Act follows verbatim для interop с Google Calendar / Apple Calendar.

**ReputationScore** *(Domain)*. Производная метрика; взвешенное среднее с учётом recency, sample size, weight рейтера. Скоупы: `as_organizer` / `as_participant`.

**RLS (Row-Level Security)** *(Stack / Compliance)*. Postgres feature: per-row access control через policies. Обязательно для всех user-attributed таблиц в Act. Skill: `write-rls-policy`. См. RLS Operational Constraints (7 правил).

**RLS Operational Constraints** *(Architecture / Compliance)*. Свод 7 обязательных правил для всех RLS-таблиц: `transaction.atomic()` + `SET LOCAL` middleware (#1), `FORCE ROW LEVEL SECURITY` (#2), RESTRICTIVE `default_deny` (#3), отдельная BYPASSRLS-роль для Admin (#4), запрет `.raw()` вне `apps.core.rls.*` (#5), миграции через прямой PG (#6), performance patterns (#7). Нарушение любого пункта = security incident.

**РКН ст. 22 / ст. 12** *(Compliance)*. Два **РАЗНЫХ** уведомления РКН: ст. 22 = регистрация оператора ПДн; ст. 12 = ТППД (трансграничная передача в Telegram). Подаются ДО первой production-публикации. Штраф за неподачу ст. 22 — **100 000–300 000 ₽ для ИП** (ч. 10 ст. 13.11 КоАП с 30.05.2025; 50%-скидка не действует). ADR-012.

**RSVP** *(Domain)*. «Répondez s'il vous plaît» — ответ на приглашение. В Act — `EventParticipant` (signed-in) или `GuestRSVP` (anonymous).

## S

**SeriesParticipant** *(Domain)*. Default participant list для `EventSeries`; members получают приглашения на каждый сгенерированный Event (subscriber pattern в Recurrence Engine).

**SKILL.md** *(Stack)*. Anthropic Claude Code skills format: frontmatter (`name`, `description`, `allowed-tools`) + markdown body. Загружается on-demand при матче по описанию. 10 skills в `.claude/skills/`.

**Soft launch** *(Process)*. Этап 3 после MVP W10: ручной outreach 50-100 тренеров регулярных групп в Москве. Private beta для wedge validation (target ≥ 30 active series).

## T

**TIMESTAMPTZ** *(Stack)*. PostgreSQL type для timezone-aware timestamps. Используется во всех Act tables (UTC в БД, конвертация в локаль — в сервисах или фронте).

**Transactional Outbox** *(Architecture)*. См. **`outbox_event`**.

## U

**Ubiquitous Language** *(Process / DDD)*. Eric Evans DDD концепт: единая терминология между бизнес-стейкхолдерами и кодом. Этот глоссарий — реализация UL для Act.

**UniSender** *(Stack)*. Default Email ESP (RU). Альтернатива — SendPulse. Никаких Postmark / SendGrid (трансграничная передача ПДн).

**UUIDv7** *(Stack)*. Time-ordered UUID для PK write-heavy таблиц (Events, RSVP, Notifications, AuditLog, Outbox). UUIDv4 / `secrets.token_urlsafe()` — для session/CSRF/magic-link токенов. **Никогда** UUIDv7 для токенов — predictability риск.

## W

**Wedge** *(Strategic)*. Стартовое сужение: одна категория × одна география. На старте — **тренеры регулярных групп × Москва**. Запуск в одной географии × одной категории — обязательное условие выживания горизонтальной площадки.

## Y

**Yandex Cloud** *(Stack)*. Primary hosting (ADR-004). Compute + Managed PostgreSQL 17 + Object Storage + Lockbox + CDN.

**ЮKassa** *(Stack / Compliance)*. RU payment provider. Единственный платёжный путь для Act на MVP (NN #3: No Stripe / Clerk / Convex Pro / Vercel managed). Активируется Слой 1 монетизации (Месяц 4+).

## 0-9

**152-ФЗ** *(Compliance)*. Федеральный закон РФ «О персональных данных». Key articles for Act: ст. 18 (РФ-локальность ПДн), ст. 9 ред. 156-ФЗ (отдельный документ согласия), ст. 12 (ТППД), ст. 22 (регистрация оператора).

**156-ФЗ от 24.06.2025** *(Compliance)*. Поправка к 152-ФЗ ст. 9, требующая **отдельный документ согласия** (НЕ вложенный чекбокс «согласен с правилами»). NN #2.

## Cross-refs

- Полные определения с источниками → `docs/PRODUCT.md` (бизнес-термины) + `docs/ARCHITECTURE.md` (архитектурные).
- 11 NON-NEGOTIABLE → `CLAUDE.md` (compliance + санкции).
- Risk register → `docs/risk-register.md` (Strategic / Operational / Compliance / Technical).
- JTBD ↔ BC mapping → `docs/jtbd-bc-mapping.md`.
