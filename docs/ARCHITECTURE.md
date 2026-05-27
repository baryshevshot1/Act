# Act — Architecture

> Архитектурные принципы, 16 bounded contexts, ключевые сущности и потоки, технологический стек (Уровень B), Level C для шести контекстов (Identity & Auth, Events с Recurrence, RSVP & Attendance, Contacts Sharing, Recommendations, Localization), bootstrap-план, Pilot Этап 0, 16 ADR-решений и источники. Перед чтением — [`../CLAUDE.md`](../CLAUDE.md) для фиксированных конвенций.

|Параметр                |Значение                                                                                                                                                                                                                                                 |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Статус**              |V1.2 (стек) + V1.3 (Level C для трёх критичных) + Wave 1 (P0) + Wave 2 (P1) + Wave 3 (P2 + 13 gaps) applied                                                                                                                                              |
|**ADR-нумерация**       |001–016 (стабильно; Wave 3 не вводила новых ADR, только расширила существующие и добавила operational секции)                                                                                                                                            |
|**Level C готовы**      |Identity & Auth (+ Cookie consent + audit_log_pii_access) · Events · RSVP & Attendance · Contacts Sharing · Recommendations (+ Stable API contract) · Localization (+ Russian plurals + Server Components patterns) + Outbox cross-cutting infrastructure|
|**Operational sections**|Disaster Recovery · DB Migration Strategy · Feature Flags · Rate Limiting · Data Retention Policies · Cost Monitoring · OWASP Top 10:2025 mapping                                                                                                        |
|**Текущая фаза**        |Pre-Phase 0 (Compliance baseline pending)                                                                                                                                                                                                                |
|**Pending**             |Pilot Этап 0 → ADR-007 commit/rollback → MVP-спринты W1–W10                                                                                                                                                                                              |
|**Обновлено**           |2026-05-24                                                                                                                                                                                                                                               |

## Содержание

- [Архитектурные принципы](#архитектурные-принципы)
- [16 bounded contexts](#16-bounded-contexts)
- [Основные сущности](#основные-сущности)
- [Ключевые потоки данных](#ключевые-потоки-данных)
- [Архитектурные подходы к ключевым проблемам](#архитектурные-подходы-к-ключевым-проблемам)
- [Что НЕ закладываем (deferred)](#что-не-закладываем-deferred)
- [Стек (Уровень B)](#стек-уровень-b)
- [Compliance: 152-ФЗ + OWASP + санкции](#compliance-152-фз--owasp--санкции)
- [Level C для критичных контекстов](#level-c-для-критичных-контекстов)
- [Bootstrap: Phase 0 + Phase 1](#bootstrap-phase-0--phase-1)
- [Pilot Этап 0](#pilot-этап-0)
- [CLAUDE.md иерархия](#claudemd-иерархия)
- [Migration paths](#migration-paths)
- [Risk register](#risk-register)
- [ADR (Architecture Decision Records)](#adr-architecture-decision-records)
- [Источники](#источники)

-----

## Архитектурные принципы

1. **Modular monolith с DDD-bounded contexts.** Это не «маленькие микросервисы», а единый деплой с жёстко enforced границами модулей. Shopify публично подтвердил эту модель на >2.8M строк Ruby в их основном кодбейсе: «We chose to evolve Shopify into a modular monolith, meaning that we would keep all of the code in one codebase, but ensure that boundaries were defined and respected between different components» [F: shopify.engineering/deconstructing-monolith]. Для соло-фаундера на AI-коде это строго оптимальная модель: один деплой, одна БД, стек-трейсы читаемы, транзакции работают по-старому, нет distributed-debugging. Микросервисы для соло-команды добавляют операционный налог без выгоды [F: dev.to/naveens16; singhajit.com, 2024].
1. **i18n с дня 1 через ICU MessageFormat.** ICU — широко поддерживаемый стандарт, позволяющий выражать сложные форматирование (плюрализация, gender, select) [F: next-intl.dev]. Все строки в JSON-каталогах локалей (`messages/ru.json`, `messages/en.json`). Locale-aware форматирование дат, чисел, плюрализация. Маршруты с префиксом `/ru/` и `/en/`. Структура данных учитывает locale: у Event есть `title_translations`, у City — `localized_name`. Zero-cost будущие локали (ES, AR, DE) при росте.
1. **Гео-aware с дня 1.** `Country` (FK), `City` (FK), таймзона — first-class поля на `User`, `Event`, `Group`. Это позволяет корректно фильтровать, отображать время и делать гео-сегментацию feed без необходимости переписывать схему.
1. **Security by design.** RBAC (Role-Based Access Control) на уровне приложения + RLS (Row-Level Security) на уровне БД для PII-чувствительных таблиц. Encryption at rest для PII-полей (телефон, email, документы верификации). OWASP Top 10 2025 как чеклист: первая категория — Broken Access Control, обнаруживается у 3.73% протестированных приложений [F: owasp.org/Top10/2025] — закрывается RBAC+RLS; A07 Authentication Failures — обязательная MFA для Pro и опциональная для всех + rate-limiting на login.
1. **Privacy by design.** Минимизация ПДн: телефон опциональный, приоритет — привязка к Telegram. Контакты участников — opt-in двустороннее согласие. Audit log всех доступов к чувствительным данным. Готовность к 152-ФЗ ст. 9 (ред. с 01.09.2025) — согласие на обработку оформляется отдельным документом [F: garant.ru, 2025], хранение ПДн граждан РФ — на серверах в РФ.
1. **AI-implementability.** Структура модулей и контракты понятны Claude Code для генерации спринт за спринтом: один PR меняет один модуль (контекст помещается в один промпт), межмодульные интеграции — через явные интеграционные события, не через прямые вызовы [В: вытекает из shopify.engineering practice and kgrzybek/modular-monolith-with-ddd pattern]. Каждый модуль имеет публичный API и приватный internals — Claude может работать в internals не нарушая контракт.
1. **First-write locality (ст. 18 ч. 5 152-ФЗ в ред. ФЗ № 23-ФЗ от 28.02.2025).** Первичная запись ПДн ДОЛЖНА происходить в БД на территории РФ. Next.js front **не делает прямых POST-запросов на зарубежные сервисы** с пользовательскими данными; все POST идут через Django backend в Yandex Cloud (RU-region), который затем при необходимости передаёт данные в zarubezhnye сервисы (например, Telegram) — это уже **вторичная** трансграничная передача под ст. 12, не первичная запись. На уровне Next.js это закрывается:
- All API routes → backend `/api/*` proxy через Django.
- Server Actions используют только Yandex-инфраструктуру.
- Сторонние SDK на фронте (PostHog) — self-hosted в РФ.
1. **Transactional outbox для cross-context events.** Cross-context events публикуются через таблицу `outbox_event` в той же транзакции, что и mutation основной агрегатной таблицы; Procrastinate worker poll-ит outbox и доставляет события subscribers. Гарантия at-least-once delivery; идемпотентность обязательна на consumer-side. Django signals остаются как in-process механизм для intra-context concerns (validation, denormalization внутри одного `apps.<ctx>/`); cross-context — только через outbox. См. ADR-016.

-----

## 16 bounded contexts

1. **Identity & Auth** — регистрация (email/Telegram OAuth/phone OTP), login, sessions, MFA для Pro, password recovery, anomaly detection на login.
1. **User Profile** — публичный профиль, био, фото, языки, города, видимость, opt-in настройки.
1. **Verification** — phone OTP, email confirmation, photo-verification (selfie matching profile + gesture-based liveness — Bumble-pattern), ID verification для Pro, верификационные бейджи.
1. **Groups** — группы (open/closed/invite-only), правила, `GroupMembership`, владелец, gating правила, опциональное расписание.
1. **Events** — `Event` entity, статусы (`draft`, `published`, `full`, `cancelled`, `completed`), `capacity`, `location` (привязка к City), `format_tags`, привязка к `Group` или standalone.
1. **Recurrence Engine** — `Series` с RRULE (RFC 5545), генерация Event-экземпляров в background job (ежедневно создаёт экземпляры на 21 день вперёд), синхронизация изменений шаблона с предстоящими экземплярами.
1. **RSVP & Attendance** — `EventParticipant`, статусы (`applied`, `confirmed`, `waitlist`, `declined`, `checked_in`, `no_show`), модерация заявок organizer-ом, check-in flow.
1. **Contacts Sharing** — bilateral consent для обмена контактами; хранится отдельной таблицей с `EncryptedValue`; revocable.
1. **Ratings & Reputation** — двусторонние `Rating`; «simultaneous reveal» (видимы только после обеих оценок или таймаута 14 дней — Airbnb-pattern [F: Fradkin et al., Marketing Science 2021]); `ReputationScore` — производная метрика.
1. **Discovery & Search** — каталог Country → City → Category → Format. Ранжирование: `reputation × activity × recency × proximity`. Карта-вью — deferred до v2.
1. **Recommendations** — placeholder-модуль; в MVP — простая сортировка by reputation; ML-персонализация deferred.
1. **Notifications** — email (transactional), push (web push в MVP), in-app inbox; шаблоны i18n. Critical для RSVP-confirmation flow на серии.
1. **Moderation & T&S** — `ReportedContent`, бан, антифрод, audit log, ручная админ-консоль.
1. **Localization / i18n** — каталоги переводов, locale negotiation, форматирование, country/city localized names.
1. **Analytics** — NSM Confirmed Weekly Attendances, supporting metrics, базовый event-tracking, retention cohort.
1. **Admin Console** — внутренний инструмент для соло-фаундера: модерация, ручная верификация, статус системы, метрики.

Между модулями — асинхронные интеграционные события (например, `EventCompleted` → Ratings подписан → создаёт окна для оценки) — паттерн In-Memory Events Bus, описанный Kamil Grzybek в reference-имплементации modular monolith [F: github.com/kgrzybek/modular-monolith-with-ddd].

-----

## Основные сущности

```
User
  id UUID PK, email/phone (encrypted), telegram_username (optional),
  locale, primary_country, primary_city, created_at, status (active/banned)

UserProfile
  user_id, display_name, bio, photo_url, languages[], visibility settings

UserVerification
  user_id, type (phone/email/photo/id), status, verified_at,
  verification_evidence (encrypted ref)

Group
  id, owner_user_id, name (i18n), description (rich), category,
  country_id, city_id, type, rules, schedule_series_id (nullable)

GroupMembership
  group_id, user_id, role (member/admin), joined_at, status

GroupRule
  group_id, rule_type, parameters

Event
  id, organizer_user_id, group_id (nullable), series_id (nullable),
  title (i18n), description, country_id, city_id, location_text,
  starts_at, ends_at, capacity, status, format_tags[],
  moderation_required, is_paid, price, currency

EventParticipant
  event_id, user_id, status (applied/confirmed/waitlisted/declined/
                              checked_in/no_show),
  applied_at, confirmed_at

Series
  id, organizer_user_id, group_id (nullable), template, rrule,
  next_generation_at, status

SeriesParticipant
  — default participant list (members получают приглашения
  на каждый сгенерированный Event)

Country, City
  — справочники с localized_names_json, timezone, geo (lat/lng — optional на MVP)

Locale, Category, Tag
  — справочники + локализации

Rating
  id, event_id, rater_user_id, ratee_user_id, score (1-5), comment,
  visibility (hidden_until_reciprocal/visible), created_at

ReputationScore
  user_id, scope (as_organizer/as_participant), score, sample_size,
  last_recomputed_at

Notification
  user_id, type, payload, channel (email/push/in_app), status, sent_at

ReportedContent
  reporter_user_id, target_type, target_id, reason, status, moderator_action

AuditLog
  actor_user_id, action, target_type, target_id, timestamp, ip_hash

Contact
  pair (user_a_id, user_b_id) + consent_status_a + consent_status_b
  + revealed_at (если оба consent=true)

PaymentTransaction (deferred к Слою 1)
  event_id, payer_user_id, provider (yookassa/stripe), amount, currency, status
```

**Изменение V1.0 → V1.1:** `GuestRSVP` существует независимо от `User` со слабой identity через `(contact_channel, contact_value)`. При signup — миграция в `EventParticipant` без потери history. Меняет ER-диаграмму V1.0.

-----

## Ключевые потоки данных

### Поток 1. Регистрация и онбординг

1. Гость заходит на `/` → видит локализованный landing (определение locale: query param > cookie > Accept-Language > default RU).
1. Кнопка «Создать аккаунт» → выбор канала (Email + password, Telegram OAuth, Phone OTP).
1. После аутентификации — обязательная мини-анкета: имя, основной город, языки, opt-in на phone-verification.
1. Identity & Auth выпускает session; User Profile создан; событие `UserRegistered` → Analytics подписан.
1. На главной — «Что вы хотите сделать?»: создать встречу / создать группу / найти встречу.

**Cold-start liquidity:** новому пользователю показывается каталог его города (Discovery → city_id filter).

### Поток 2. Создание встречи

1. Organizer открывает `/events/new` → форма (визуальная карточка inspired Partiful/Luma).
1. Submit → Events создаёт `Event(draft)` → validation → `status=published`.
1. Событие `EventPublished` → Notifications уведомляет members группы (если `group_id` есть) → Discovery индексирует.
1. Карточка доступна по `/{locale}/event/{id-slug}` — SEO-page (locale-aware).

### Поток 3. Подача заявки и подтверждение

1. Participant видит карточку Event → нажимает «Прийти».
1. RSVP создаёт `EventParticipant(applied)`, если включена модерация; иначе сразу `confirmed`.
1. Если `applied` → событие `RSVPApplied` → Notifications уведомляет organizer.
1. Organizer в Admin-view нажимает «Confirm» → `status=confirmed` → событие `RSVPConfirmed` → Notifications уведомляет participant.
1. Если capacity достигнут → новые RSVP — в waitlist.

### Поток 4. Создание серии и автогенерация рекуррентных встреч

1. Organizer создаёт `Series` → форма с RRULE-помощью («каждый вторник, 19:00, до конца октября»).
1. `Series` сохранена → background job в Recurrence Engine ежедневно генерирует Event-экземпляры на 21 день вперёд.
1. Каждый сгенерированный `Event` имеет `series_id`, ссылку на template + конкретную дату.
1. Для каждого `SeriesParticipant` создаётся `EventParticipant(invited)` для каждого нового экземпляра.
1. Событие `EventGeneratedFromSeries` → Notifications рассылает «Подтвердите участие в Y» с дедлайном.

### Поток 5. RSVP-подтверждение для регулярной встречи

1. `SeriesParticipant` получает push/email «Тренировка во вторник, подтвердите участие».
1. Кликает «Прийти» → `EventParticipant.status = confirmed`.
1. Не подтвердил за 24 ч до — auto-`status=declined` (не считается).
1. Organizer видит только confirmed-list — это «реальный состав».

### Поток 6. Двусторонний рейтинг

1. После `Event.ends_at + 1 час` — событие `EventCompleted` → Ratings создаёт окна оценки для organizer (оценивает каждого confirmed participant) и для каждого confirmed participant (оценивает organizer).
1. Оценки сохраняются с `visibility=hidden_until_reciprocal`.
1. Когда обе стороны оставили — обе `visibility=visible` одновременно (Airbnb-pattern).
1. Если через 14 дней одна сторона не оценила — другая всё равно становится `visible`.
1. После `Rating` сохранён → событие `RatingPosted` → `ReputationScore` recompute для ratee.

### Поток 7. Discovery / каталог

1. Гость заходит `/ru/discover/moscow` → Discovery возвращает Events отфильтрованные по `city_id=Moscow`, `locale=ru`, `time>=now`.
1. **Фильтры:** country/city/category/format/datetime/price/verified-only.
1. **Sort:** `ranking = reputation × activity × recency × proximity-bucket`.
1. Pagination + опциональная map-view (deferred к v2).

-----

## Архитектурные подходы к ключевым проблемам

### Cold-start liquidity

- **Synthetic supply (consent-based mirror imports):** импорт публичных Telegram-афиш и тренерских расписаний с явной атрибуцией «опубликовано на Telegram-канале X». Это создаёт каталог-ценность для demand-side до того как пришёл organic supply. Critically: только публичные источники, с атрибуцией, и с возможностью владельца забрать импорт.
- **Host-first onboarding:** фаундер вручную приглашает первые 30–50 тренеров, помогает создать первую серию, импортирует расписание из их Telegram-чатов.
- **Geographic concentration:** только один город в первые 3 месяца. Никаких «8000 городов» уже с MVP (ошибка InParty).

### T&S incident handling

- **В архитектуре заложен фаст-патч:** `AuditLog` даёт восстанавливаемую историю; `ReportedContent` — единая точка для жалоб; Identity & Auth поддерживает мгновенный бан (`status=banned` → все сессии invalidated).
- **Pre-event T&S:** organizer-verification обязательна для Pro; для не-Pro — опциональная phone+photo verification повышает rank в discovery.
- **Post-event T&S:** каждый `Rating` низкого score (<3) автоматически создаёт `ReportedContent.review` → ручная модерация.

### Privacy/PII protection

- PII-поля (телефон, email, документы верификации) — encryption at rest + RLS на уровне БД (только service-role + сам пользователь).
- Контакты участников — отдельная таблица `Contact` с bilateral consent; экспорт контактов не делается, только показ в UI.
- Audit log всех чтений PII-полей.
- Готовность к 152-ФЗ: отдельный документ «Согласие на обработку ПДн» (требование с 01.09.2025); политика обработки; уведомление Роскомнадзора при запуске.

### Scalability path

- Modular monolith с явными границами легко расширяется до 100K пользователей без переписывания: вертикальный scale БД, кеширование read-моделей в Redis-аналоге, фоновые job-ы в очереди.
- Если один модуль становится горячим (например, Discovery), его можно экстрагировать в отдельный сервис без переписывания других — это и есть основная выгода modular monolith [F: shopify.engineering, 2020].

### AI-driven development

- **Где помогает:** модули имеют чёткие границы → Claude Code может работать в одном модуле без понимания всей системы. Интеграционные события дают понятный контракт. ICU MessageFormat — стандарт, Claude знает.
- **Где мешает:** если границы размыты или есть «канонический Domain Model» (большой shared User/Event с 30 атрибутами) — Claude генерирует код, который туда дописывается, и через 3 месяца модель деградирует. **Mitigation:** строгая дисциплина границ; static-analysis запреты на cross-module direct calls (как packwerk у Shopify).

-----

## Что НЕ закладываем (deferred)

- **Микросервисы.** Сознательно отложено: дополнительный сетевой/деплой/observability налог без бизнес-выгоды для соло-команды.
- **ML personalization.** Откладывается до >10K MAU, когда есть достаточно данных для обучения. До этого — статическое ранжирование по `reputation × activity × recency`.
- **Real-time chat в продукте.** Внешний канал (Telegram-link на странице события + опциональный встроенный Telegram Group link). Чат — это огромный T&S burden.
- **Mobile native.** iOS — фаза 5, как обёртка над web (либо RN+Expo через RuStore, либо Swift поверх того же бэкенда — решение по обстановке).
- **Payments в MVP.** Слой 1 монетизации (комиссия) включается только после PMF — раньше это premature optimization и большой регуляторный burden.
- **Recommendation feed.** Только список и фильтры в MVP; feed-as-discovery — deferred.
- **Карта-view.** Опциональна на v2 (Yandex Maps / Mapbox).
- **Token-gating / Web3 features.** Не для нашей аудитории.
- **WebSocket / Centrifugo.** На MVP — polling 30s достаточно. SSE как next step. WebSocket — только если specific feature потребует low-latency.
- **Idempotency keys для платёжных операций.** Зарезервированы для Phase 6 (payments). Pattern: `Idempotency-Key` header на POST /api/payments (Stripe-style — клиент генерирует UUIDv4, сервер кеширует response на 24h). На MVP не нужны — критичные mutations (RSVP, share grant) защищены RLS + unique-constraints на (user_id, event_id, …).

-----

## Стек (Уровень B)

### Сводная таблица

|Layer                         |Выбор                                                                   |Обоснование                                    |Cost @ 10K MAU                        |Deferred upgrade                             |
|------------------------------|------------------------------------------------------------------------|-----------------------------------------------|--------------------------------------|---------------------------------------------|
|Backend framework             |Django 5.2 LTS                                                          |Eventbrite-pattern + Claude Code top-3 в Python|₽0 (open-source)                      |Rails 8 если Этап-0 покажет >30% выигрыш     |
|Backend language              |Python 3.12                                                             |top-3 Claude Code productivity                 |₽0                                    |—                                            |
|Frontend framework            |Next.js 16 + App Router                                                 |Luma/Partiful proof-of-scale + SSR для OG      |₽0                                    |—                                            |
|Frontend i18n                 |next-intl + ICU MessageFormat                                           |стандарт production                            |₽0                                    |—                                            |
|Database                      |PostgreSQL 17 (Yandex Managed)                                          |RLS + JSONB + Eventbrite-proven                |~3 000–5 000 ₽/мес [Г]                |upgrade на 18 — Q3 2026                      |
|ORM                           |Django ORM                                                              |встроен + Claude Code training corpus          |₽0                                    |raw SQL для RLS                              |
|Background jobs               |Procrastinate (Postgres-backed)                                         |один меньше компонент в prod                   |₽0 (та же DB)                         |Celery+Redis при >1000 jobs/min              |
|Cache + Session + Rate limiter|in-Postgres                                                             |соло-friendly, минимум moving parts            |₽0                                    |Redis managed при >30% Postgres load         |
|Search                        |PostgreSQL FTS + tsvector                                               |достаточно до ~50K events                      |₽0                                    |Meilisearch self-host при >500ms p95         |
|File storage                  |Yandex Object Storage                                                   |152-ФЗ + унифицированный ecosystem             |~500–1 500 ₽/мес [Г]                  |—                                            |
|CDN                           |Yandex CDN                                                              |РФ-edge, 152-ФЗ-friendly                       |~500–1 000 ₽/мес [Г]                  |—                                            |
|Email ESP                     |UniSender или SendPulse                                                 |российский + deliverability                    |~1 000–3 000 ₽/мес [Г]                |—                                            |
|SMS provider                  |SMS.ru (fallback после Telegram Gateway)                                |tertiary по V1.1 strategy                      |~71–710 ₽/мес [Г]                     |—                                            |
|Telegram Bot library          |aiogram 3.x                                                             |production-стандарт RU                         |₽0                                    |—                                            |
|Auth strategy                 |django-allauth + django-otp + custom Telegram OIDC + django-otp-webauthn|Clerk блокирован Stripe-billing                |₽0                                    |—                                            |
|Real-time                     |Отложен на Phase 5+                                                     |MVP polling 30s достаточен                     |₽0                                    |SSE при необходимости                        |
|Analytics                     |PostHog self-hosted                                                     |152-ФЗ + полный feature set                    |~1 500 ₽/мес (4GB RAM) [Г]            |—                                            |
|Error tracking                |Sentry self-host (или GlitchTip)                                        |152-ФЗ (stack traces = ПДн)                    |~1 000 ₽/мес [Г]                      |—                                            |
|APM/logs                      |LGTM-стек (Grafana+Prometheus+Loki)                                     |open-source full-stack                         |~1 500 ₽/мес [Г]                      |Tempo для distributed traces — Phase 4+      |
|Hosting                       |Yandex Cloud Compute + Managed Postgres                                 |unified RU ecosystem                           |~5 000 ₽/мес VPS + ~5 000 ₽/мес DB [Г]|—                                            |
|CI/CD                         |GitHub Actions + self-hosted runner на Yandex Cloud                     |стандарт + plan B Forgejo                      |₽0 free tier 2000 мин                 |Forgejo при блокировке                       |
|Module boundary               |import-linter                                                           |Django-friendly, активный                      |₽0                                    |—                                            |
|iOS strategy                  |PWA + Telegram Mini App с дня 1; RN+Expo+RuStore — Phase 5              |соло-ИП РФ без зарубежного юр.лица             |RuStore ИП ~₽5 000 одноразово         |App Store через зарубежное юр.лицо — Phase 6+|
|Testing                       |pytest + pytest-django + Playwright (Vitest+Storybook позже)            |full-stack solo приемлемый                     |₽0                                    |—                                            |

**Total cost @ 10K MAU ≈ 13 000–20 000 ₽/мес инфраструктуры + время на ops (~5–10 ч/нед).**

### Backend: почему Django 5.2 LTS

- **Claude Code language productivity** [F: benchlm.ai/benchmarks/sweVerified, 22.05.2026; llm-stats.com/benchmarks, май 2026; mindstudio.ai, апрель 2026]. SWE-bench Verified на 22.05.2026:
  - Claude Mythos Preview: 93.9%
  - Claude Opus 4.7 Adaptive: 87.6%
  - GPT-5.3 Codex: 85%
  - Claude Opus 4.6: ~80%
  - Opus 4.5: 80.9%
  - Бенчмарк работает на Python-репозиториях → implicit advantage. TS медленнее JS из-за типов. Статически-типизированные языки 1.4–2.6× медленнее.
- **Proof-of-scale в нашей домене:** Eventbrite на Django с 2014 — единственный publicly verified events-monolith на масштабе [F: eventbrite engineering blog].
- **152-ФЗ + РКН compliance:** больше готовых django-пакетов для российских требований (django-allauth + российские провайдеры через social-auth-backends, адаптеры к VK ID / Yandex ID в open-source [Г]).
- **i18n из коробки на ICU-уровне** (gettext + format-message).
- **import-linter** для enforcement модульных границ [F: github.com/seddonym/import-linter, активный проект на май 2026].

**Strong alternative — Rails 8 с Packwerk,** если в Этапе 0 окажется, что Claude Code radically лучше на Ruby (тест: за 1 неделю реализовать Identity & Auth bounded context на обеих, замерить количество rework-ов).

**Django 5.2 LTS** [F: docs.djangoproject.com/en/5.2/releases, апрель 2025] вышел 02.04.2025, поддержка security-fixes до апреля 2028. Django 6.0 [F: habr.com/ru/articles/973074, декабрь 2025] вышел 03.12.2025 со встроенным фреймворком фоновых задач. Берём **5.2 LTS** (3-летняя устойчивость).

### Module boundary enforcement

`import-linter` с декларативной конфигурацией в `.importlinter`. Контракты типа `forbidden_modules` и `layers`. Включается в CI через GitHub Actions / pre-commit.

**Конкретные контракты на дне 1:**

1. `Identity & Auth` — не должен импортировать ничего из 15 других контекстов.
1. `Ratings & Reputation` — не должен импортировать `Verification`.
1. `Discovery & Search` — может читать из `Events`, `User Profile`, `Ratings`, но не из `Identity & Auth`, `Notifications`, `Moderation`.
1. Cross-context коммуникация — только через явный `events`-канал (Django signals или own bus).

### Frontend: почему Next.js 16

1. Критический путь OG-cards в V1.1 требует SSR/streaming — Next.js App Router с server-components — наиболее зрелый паттерн.
1. Luma и Partiful на Next.js [F: luma.com Pontis 2021] — proof at scale.
1. i18n через `next-intl` — production-стандарт с ICU MessageFormat.
1. Claude Code на React/TypeScript — крупнейший training corpus [Г].
1. Image optimization через `next/image` с self-host вариантом для РФ.

**Caveat:** TypeScript в Claude Code productivity-bench медленнее JavaScript из-за типов [F: dev.to/mame, март 2026]. **Решение:** оставить TS, но использовать строгий typed-API через `zod` для рантайм-валидации границ, а в простых компонентах не насиловать сложные типы.

**Self-host обязателен** — Vercel hosting не подходит под 152-ФЗ ст. 18; Next.js легко деплоится через standalone build на Node.js в Yandex Cloud Compute.

**Альтернатива при срыве:** SvelteKit — меньший bundle, но Claude Code менее предсказуем на Svelte [Г]; Astro — если 80% страниц статика, но динамика RSVP и organizer-dashboard требует SSR.

### Database

- **PostgreSQL 17** — production-stable на май 2026. Релиз 17 был в сентябре 2024. PostgreSQL 18 — в конце 2025 [Г, нужна проверка]. **Берём 17.x.**
- **Managed Postgres** у Yandex Cloud, VK Cloud, Selectel поддерживают 16/17 [Г] — точные версии проверить в админ-консоли провайдера. На MVP — PostgreSQL 17 managed через **Yandex Cloud Managed Service for PostgreSQL** [F: yandex.cloud/en/docs/managed-postgresql/pricing — новые цены с 01.05.2026].
- **RLS-стратегия:** обязательная политика для таблиц `ContactShare`, `VerificationDocument`, `GuestRSVP`, `UserContactChannel`. Реализация через Postgres-уровень `CREATE POLICY` + `SET app.current_user_id = ...` в начале каждого запроса (transaction-level). Работает с любым ORM при условии установки session-параметра на pool-connection.
- **FTS для MVP:** PostgreSQL встроенный с `tsvector` + GIN-индекс по `name + description + city` для events. RU+EN dictionaries — стандартный `russian` и `english` configs. Достаточно до ~50K events [Г]. После — Meilisearch upgrade.
- **JSONB** для localized strings (`name = {"ru": "...", "en": "..."}`), `og_metadata`, `share_metadata` — native, индексируется через GIN expression-индекс.

### ORM: Django ORM

**Аргументы:**

1. Встроен в Django — никаких дополнительных зависимостей.
1. Поддержка миграций через `manage.py makemigrations / migrate` — proven workflow.
1. Raw SQL escape hatch через `.raw()` и `connection.cursor()` — для RLS, recursive CTE, оконных функций.
1. Claude Code training corpus на Django ORM огромен.
1. `DATABASE_ROUTERS` — можно разнести cache/queue в отдельные DB-роли при необходимости.

**RLS-интеграция:** Django ORM не имеет native RLS-аннотаций. Реализация — через middleware, который ставит `SET LOCAL app.current_user_id` в начале каждого запроса в transaction context. ~50 строк кода. Источник синтаксиса — [F: pganalyze.com/blog/postgres-row-level-security-django-python] + [F: dev.to/dvoraj75/why-postgresql-row-level-security-is-the-right-approach-to-django-multitenancy-3e1m]. Используем session-variable подход (`SET LOCAL` / `set_config(..., true)`).

**Alternative — SQLAlchemy 2.0:** более мощный query-builder, но требует отказа от Django admin и от half-of-Django-batteries. Не оправдано для соло-фаундера.

### Background jobs: Procrastinate

[F: habr.com/ru/articles/973074, декабрь 2025] Django 6.0 ввёл встроенный фреймворк фоновых задач. **Для MVP на Django 5.2 он недоступен** — внешние решения.

|Кандидат         |Backend       |Подходит для нас           |
|-----------------|--------------|---------------------------|
|**Procrastinate**|PostgreSQL    |**идеален для соло**       |
|Celery           |Redis/RabbitMQ|да, но overhead для соло   |
|dramatiq         |Redis         |менее популярен            |
|RQ               |Redis         |overkill                   |
|django-q2        |Postgres/Redis|подходит, но менее активный|

**Procrastinate** использует PostgreSQL как backend — никаких дополнительных Redis-инстансов. Для соло-ИП критично: один меньше компонент. Поддерживает scheduled tasks, retries, dead letter, периодические задачи (cron-style), есть Django-integration.

**Расклад по трём use cases:**

1. **Recurrence Engine** — ежесуточный periodic task на 03:00 МСК: для каждой активной серии генерировать экземпляры в окне [today, today+21]. Идемпотентно (`UPSERT` по `(series_id, instance_date)`).
1. **Notifications-router** — scheduled task per RSVP при создании: T-7д, T-1д, T-3ч, T-15м, каждый — отдельная задача со своим timestamp.
1. **GuestRSVP retention** — daily periodic, удаляет/анонимизирует записи, где `event_date_end + 45 дней < сейчас`.

**Альтернатива:** если нагрузка вырастет до >1000 jobs/мин (нескоро на 10K MAU) — переход на Celery + Redis. Миграция относительно безболезненная.

### Cache + Session + Search + Storage

- **Cache + Session + Rate limiter:** in-Postgres. Django имеет `django.core.cache.backends.db.DatabaseCache` и `django.contrib.sessions.backends.db` встроенные. Для rate-limiter — отдельная таблица с `INSERT ... ON CONFLICT UPDATE` для atomic increment.
- **Когда переходить на Redis:** если cache-hit rate в Postgres начинает занимать >30% CPU базы (мониторится через `pg_stat_statements`). На MVP-scale маловероятно.
- **Search:** PostgreSQL FTS + tsvector + GIN — достаточно до ~50K events. Russian + English dictionaries из коробки. Гео-фильтрация через `earthdistance` или PostGIS.
- **File storage + CDN:** [F: en.wikipedia.org/wiki/2025_internet_restrictions_in_Russia] Cloudflare и Amazon CDN в 2025–2026 регулярно блокируются в РФ-сегменте. Foreign CDN не подходит как primary. → **Yandex Object Storage + Yandex CDN.** Унифицированный bilingual ecosystem с Compute и Managed Postgres снижает операционную сложность.

### Communications

|Слой                |Выбор                                                                                                                                                                                                      |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**Email ESP**       |UniSender или SendPulse [Г, нужно сравнить feature-set в Этапе 0]. SPF/DKIM/DMARC с дня 1 обязательно.                                                                                                     |
|**Telegram Bot SDK**|aiogram 3.x для Python — production-стандарт на 2024–2026 [Г].                                                                                                                                             |
|**Telegram Gateway**|$0.01/code, пополнение через TON-кошелёк → Fragment → Gateway. Test-transaction $5–10 в Этапе 0.                                                                                                           |
|**SMS provider**    |SMS.ru как tertiary (fallback после Telegram Gateway и flash-call). Регистрация через простую форму, оплата с расчётного счёта ИП. SMS.ru: от 2.65 ₽/SMS базовая. Авторизационные через Yandex/MTS — 3–7 ₽.|
|**Web Push**        |VAPID-based стандарт. `django-push-notifications` или `pywebpush` [Г]. iOS Safari поддерживает Web Push с 16.4+ (через PWA installed to home screen).                                                      |

### Auth — re-decision

**Clerk — отвергнут.** [F: clerk.com/docs/guides/billing/overview, май 2026] Clerk billing использует Stripe. Stripe в РФ не оперирует с 2022. Россия не в explicit blocked list, но “depends on Stripe Global”, который не оперирует в РФ. + foreign CDNs блокируются в РФ. + 152-ФЗ ст. 18 нарушено для первичной обработки данных российских пользователей.

**Convex — отвергнут.** [F: srvrlss.io; toolradar.com 2026] Convex имеет open-source backend под FSL-1.1-Apache-2.0. Но:

1. Convex использует свой DSL для functions (queries/mutations в TypeScript). **Incompatible с modular monolith на 16 bounded contexts** — Convex предполагает schema-as-document.
1. Российские карты для биллинга Convex Pro — с высокой вероятностью через Stripe [Г] → не работает для ИП РФ.
1. **Vendor lock-in** — DSL Convex не переводится в стандартный SQL+ORM без полной переписи слоя данных.

**Финальный выбор: self-host через Python-экосистему:**

- `django-allauth` — основной auth-фреймворк, email + multiple OAuth providers. Community-плагины для VK и Yandex (через python-social-auth adapters) [Г]. Telegram OIDC — кастомный adapter (~100 строк) либо `python-telegram-login` пакет [Г].
- `django-otp` — TOTP/passkey/WebAuthn.
- `django-otp-webauthn` [F: github.com/Stormbase/django-otp-webauthn — «As of May 2025, I now consider this package stable enough for production use»].
- Magic link — кастомная реализация поверх Django session (15 мин TTL, one-time, IP/UA binding по V1.1).
- WebAuthn — открытый W3C стандарт, не зависит от санкций.

### Real-time, Analytics, Observability

- **Real-time** отложен. На MVP — polling 30s. SSE как next step. WebSocket — при наличии specific feature.
- **Analytics:** **PostHog self-hosted** на отдельной Compute-инстансе Yandex Cloud (~4 GB RAM = ~1500 ₽/мес [Г]). Out-of-the-box event tracking, dashboards, feature flags, A/B framework. SDK интеграция с Next.js — официальная.
- **Error tracking:** Sentry self-host [Г] для долгосрочного контроля + 152-ФЗ (стек-трейсы могут содержать ПДн); **GlitchTip** как лёгкая альтернатива если Sentry self-host окажется требовательным. **Frontend monitoring**: `@sentry/nextjs` SDK с `tracesSampleRate=0.1` (10% transactions для performance) и `replaysSessionSampleRate=0.05` (5% session replays — privacy-friendly, без записи form inputs). Отдельный Sentry-проект для frontend на том же self-hosted инстансе; нет отдельного infra-компонента.
- **APM/metrics/logs:** LGTM-стек (Grafana + Prometheus + Loki + Tempo) self-hosted, либо **Coroot** как easier-setup альтернатива. На MVP — упрощённо: Prometheus + Grafana + Loki (без Tempo).
- **Uptime:** UptimeRobot free для базового external monitoring. Self-hosted Uptime Kuma если хочется внутренний.

### Hosting: Yandex Cloud + Coolify

[F: selectel.ru, dieg.info август 2025] Selectel: 6 собственных DCs в РФ + партнёрский в Новосибирске; готовые VPS от 800 ₽/мес; 28000+ клиентов; «облака для 152-ФЗ» с явным product offering.

[F: yandex.cloud Apr 2026] Yandex Cloud: новые цены с 01.05.2026, RU billing через Yandex.Cloud LLC, полный экосистемный портфель.

**Архитектурный паттерн:** один Yandex Compute Cloud инстанс с **Coolify** [Г, активный open-source проект 2024–2026] как PaaS-overlay: Coolify деплоит Django + Next.js + PostHog + Sentry self-host + LGTM-стек как отдельные контейнеры на одной машине. Managed Postgres у Yandex (не self-host БД на Compute).

**Размер старт-инстанса:** 4 vCPU + 8 GB RAM = ~3 500–5 000 ₽/мес [Г]. Managed Postgres minimal = ~3 000–5 000 ₽/мес [Г]. Object Storage + CDN — ~1 000–2 000 ₽/мес [Г]. **Итого ~10 000–15 000 ₽/мес на старте.**

**Selectel** как fallback при проблемах с Yandex Cloud.

### CI/CD

GitHub Actions status в РФ неоднозначен, есть отчёты о intermittent блокировках. **Выбор:** GitHub Actions на старте + self-hosted runner на отдельном небольшом Yandex Compute инстансе (~500–1000 ₽/мес [Г]) для deploy-stage, чтобы deploy-traffic шёл из РФ-инфраструктуры (не через сети США).

**Plan B при блокировке:** self-hosted Gitea + Gitea Actions, или Forgejo Actions. Миграция git-репо и actions-конфигов — за день.

### iOS-стратегия

**Контекст ограничений** [F: macdailynews.com, 02.04.2026; appleinsider.com, 02.04.2026]: Apple отключил payment processing в РФ с 01.04.2026 (касается покупок пользователей в РФ, не разработчиков). [F: rustore.ru/developer/blog/self-employed, декабрь 2025] С 01.02.2026 монетизация через RuStore доступна только ИП/юрлицам. Самозанятые/физлица — публиковать без монетизации.

|Путь                             |Solo dev velocity                  |Push                                          |Покрытие                             |Auto-update                |
|---------------------------------|-----------------------------------|----------------------------------------------|-------------------------------------|---------------------------|
|**PWA + RuStore (Android)**      |Высокая (тот же Next.js codebase)  |iOS Web Push (16.4+ через home screen install)|iOS Safari + Android Chrome + RuStore|Web auto; RuStore via store|
|RN + Expo + RuStore-only         |Средняя (separate codebase)        |OneSignal/Firebase                            |Android only (RuStore)               |EAS Updates over-the-air   |
|Native Swift + зарубежное юр.лицо|Низкая (отдельный Swift codebase)  |APNS                                          |iOS (App Store) + Android (US)       |App Store flow             |
|**Telegram Mini App**            |Очень высокая (тот же web codebase)|Telegram push                                 |Telegram users only                  |Мгновенно                  |

**Финальная рекомендация:**

- **Этап 1 (MVP launch):** Telegram Mini App + PWA как primary mobile surface. Никаких native apps. Telegram Mini App открывает события через `t.me/act_bot/event?slug=k7d3` (**TODO: подтвердить хэндл бота**) — внутри Telegram сразу без перехода на сайт. PWA — для пользователей, кто хочет «приложение» на home screen.
- **Этап 2 (после PMF, Phase 5):** React Native + Expo, публикация на RuStore через ИП. Один codebase, EAS Updates.
- **Этап 3 (после revenue):** регистрация зарубежного юр.лица (Армения LLC — самый дешёвый путь, ~$1000 на старте [Г]), Apple Developer Program $99/год, native iOS или RN-сборка для App Store через зарубежный аккаунт.

**Update от 24.05.2026 — Apple частично разблокирован.** С учётом наличия у фаундера Xcode + VPN + (предположительно) рабочей зарубежной карты:

- **Можно сделать на 100%:** Web MVP на Django + Next.js + Yandex Cloud; Telegram Mini App; Native iOS (free, App Store) — через Phase 5; Android через RuStore — через Phase 5; Apple Sign-In + Telegram OIDC + VK ID + Yandex ID.
- **Требует зарубежного юр.лица (Phase 6+):** платные подписки через App Store/Stripe (если ≥ 10% revenue); IAP с Apple payouts; доступ к Stripe, Clerk Billing, Convex Pro.
- **Невозможно вне зависимости от VPN:** Google Play разработчик с RU-выплатами (остановлено 26.12.2024); Apple payment processing для конечных пользователей в РФ (отключено 01.04.2026).

**Вердикт:** проект полностью реализуем как MVP без зарубежного юр.лица. Зарубежное юр.лицо нужно только для App Store/Stripe монетизации, и только после PMF.

### Testing

- `pytest` + `pytest-django` для unit и integration на backend.
- `factory_boy` для test data.
- `Vitest` для unit-тестов frontend (Next.js поддерживает officially).
- `Playwright` для E2E (выбор: Cypress vs Playwright — оба ОК, Playwright лучше для cross-browser и проще CI-интеграция [Г]).
- `Storybook` для UI-компонентов — отложено до W4–W5 спринтов, когда design-system начнёт стабилизироваться.

### Полный стек одной строкой

Django 5.2 LTS · Python 3.12 · Next.js 16 · next-intl · PostgreSQL 17 · Django ORM · Procrastinate · in-Postgres cache/session · PostgreSQL FTS · Yandex Object Storage · Yandex CDN · UniSender · SMS.ru · aiogram 3.x · Telegram Gateway · django-allauth + django-otp + django-otp-webauthn · PostHog self-hosted · Sentry self-host (или GlitchTip) · LGTM-стек · Yandex Cloud · Coolify · GitHub Actions · import-linter · PWA + Telegram Mini App · pytest + Playwright.

-----

## Compliance: 152-ФЗ + OWASP + санкции

### 152-ФЗ

- **ст. 9 в ред. ФЗ № 156-ФЗ от 24.06.2025.** Согласие на обработку ПДн — отдельный документ, не вложенный чекбокс. Действует с 1 сентября 2025. Штрафы за нарушения по разным составам: до 700 тыс. ₽ на юр.лицо [F: garant.ru, 2025].
- **ст. 12 (трансграничная передача).** В ред. ФЗ № 266-ФЗ от 14.07.2022 (действует с 01.03.2023) — обязательное **отдельное** уведомление РКН перед началом ТППД. См. ADR-013.
- **ст. 18 (локализация).** Первичная обработка ПДн граждан РФ — только на серверах в РФ. В ред. ФЗ № 23-ФЗ от 28.02.2025 ч. 5 — первичная запись ДОЛЖНА происходить в БД на территории РФ; Next.js front не должен напрямую POST-ить пользовательские данные на зарубежные сервисы.
- **ст. 5 (минимизация).** Только то, что нужно для цели обработки. Гостю — имя + один контакт.
- **ст. 22 (уведомление оператора РКН)** через `pd.rkn.gov.ru/operators-registry/notification/`. Срок проверки до 30 дней (ч. 4). С 2025 любая компания/ИП с обработкой ПДн обязана зарегистрироваться. См. [Pre-pilot Compliance baseline](#pre-pilot-compliance-baseline-блокер-для-phase-1) и ADR-012.
- **Что — ПДн:** имя, email, телефон, IP-адрес (по практике РКН и судов).

**Штрафы с 30 мая 2025 (ФЗ № 420-ФЗ от 30.11.2024, ч. 10 ст. 13.11 КоАП РФ):**

|Состав                                                     |Должностное лицо|ИП                   |Юр.лицо          |
|-----------------------------------------------------------|----------------|---------------------|-----------------|
|Непредставление уведомления о начале обработки ПДн (ст. 22)|30 000–50 000 ₽ |**100 000–300 000 ₽**|100 000–300 000 ₽|
|Утечка ПДн (новые ч. 10–13 ст. 13.11 КоАП)                 |от 200 000 ₽    |от 1 млн ₽           |от 3 млн ₽       |

**50%-скидка по ст. 4.1.1 КоАП на составы по ч. 10 ст. 13.11 НЕ действует.** Источник: ФЗ от 30.11.2024 № 420-ФЗ; БУХ.1С «Штрафы за персональные данные с 30 мая 2025»; msp03.ru «Штрафы за нарушения в работе с персональными данными с 30 мая 2025».

- **Caveat:** есть законопроект, расширяющий требования с марта 2028 [F: sec.ussc.ru, 2025] — перед запуском обязательна актуальная консультация с юристом по ПДн.

### OWASP Top 10:2025 → mapping таблица

Mapping актуальной версии OWASP Top 10:2025 (Release Candidate анонсирован 6 ноября 2025 на OWASP Global AppSec; финал — январь 2026) [F: fastly.com/blog/new-2025-owasp-top-10-list; parasoft.com/blog/owasp-top-10-2025-what-changed]:

|OWASP 2025                                         |Наш статус                                                                             |Действие / реализация                                                                     |
|---------------------------------------------------|---------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
|A01 Broken Access Control (включая SSRF)           |RLS закрывает большую часть; SSRF — защита server-side fetch (allowlist outgoing hosts)|RLS Operational Constraints + outgoing HTTP через `apps.core.http` с allowlist            |
|A02 Security Misconfiguration                      |Coolify config — risk                                                                  |Hardening checklist в Phase 0; secrets через Yandex Lockbox                               |
|A03 Software Supply Chain Failures **(NEW)**       |Не покрыто                                                                             |`dependabot` + `pip-audit` + SBOM генерация в GitHub Actions (CycloneDX format)           |
|A04 Cryptographic Failures                         |См. ADR-014 (field-level encryption)                                                   |django-cryptography + Yandex Lockbox; TLS 1.3 only; Argon2id для passwords                |
|A05 Injection                                      |Django ORM защищает; FTS — параметризовать                                             |OK + CodeQL в CI на SQL injection patterns                                                |
|A06 Insecure Design                                |Threat modeling раз в спринт                                                           |Добавить в Definition of Done                                                             |
|A07 Authentication Failures                        |Magic links + WebAuthn + RLS                                                           |Rate limit (см. ниже) + audit log PII access                                              |
|A08 Software/Data Integrity Failures               |Webhook signatures (Telegram HMAC, SMS.ru)                                             |Verify all incoming webhooks                                                              |
|A09 Security Logging & Alerting Failures           |Sentry + LGTM                                                                          |Alert thresholds на anomalies (sign-in spikes, RLS-policy denials)                        |
|A10 Mishandling of Exceptional Conditions **(NEW)**|Django default 500 handler                                                             |Generic error pages, no stack traces в production; custom handler с request_id для отладки|

### Rate Limiting

Защита от brute-force на auth, abuse на shareable endpoints, DoS на read endpoints. Реализация — `django-ratelimit` (per-endpoint декораторы; storage в Postgres-backed cache per ADR-006).

|Endpoint                                 |Limit          |Scope                 |
|-----------------------------------------|---------------|----------------------|
|`POST /auth/otp-request`                 |3/min · 5/hour |per IP · per phone    |
|`POST /auth/magic-link-request`          |3/min · 10/hour|per IP · per email    |
|`POST /api/rsvp`                         |10/min         |per session           |
|`POST /api/contacts-share`               |5/min          |per authenticated user|
|`POST /api/events` (create)              |30/hour        |per authenticated user|
|`GET /api/events` (read)                 |100/min        |per authenticated user|
|`GET /e/{short_slug}` (public event page)|60/min         |per IP                |

При превышении — `429 Too Many Requests` с `Retry-After` header. Метрики rate-limit hits — в PostHog event `rate_limit_exceeded` (для anti-fraud detection).

**Alternative**: `django-axes` для credential-stuffing protection на login (auto-lockout после N failed attempts). На MVP — оба пакета установлены, django-ratelimit для API, django-axes для auth.

### Data Retention Policies

152-ФЗ ст. 5 (минимизация) + ст. 14 (право на удаление) + РКН практика: каждая сущность имеет explicit retention. Cleanup — Procrastinate periodic-task раз в сутки.

|Entity                                      |Retention                                 |Trigger                                  |Action                                                            |
|--------------------------------------------|------------------------------------------|-----------------------------------------|------------------------------------------------------------------|
|`rsvp_guest_rsvp` (гость без signup)        |45 дней                                   |`event_date_end + 45 дней`               |Hard delete (нет attribution к User)                              |
|`notifications_delivery` (delivery_metadata)|90 дней                                   |`created_at + 90 дней`                   |Hard delete delivery_metadata; сохраняем aggregate-stats (для NSM)|
|`notifications_suppression`                 |Permanent                                 |Never                                    |Hard bounce — пользователь снова opt-in вручную                   |
|`audit_log_pii_access`                      |1 год                                     |`accessed_at + 365 дней`                 |Hard delete (минимум по РКН-аудиту)                               |
|`identity_auth_consent` (revoked)           |Срок согласия + 3 года (ст. 21 152-ФЗ)    |`withdrawn_at + 3 года`                  |Anonymize (NULL user_id, keep purpose+granted_at для аудита)      |
|`identity_auth_user` (soft-deleted)         |30 дней grace; immediate по ст. 14-запросу|`deleted_at + 30 дней` ИЛИ user requested|Hard delete + cascading через FK                                  |
|`outbox_event` (delivered)                  |30 дней                                   |`published_at + 30 дней`                 |Hard delete                                                       |
|`outbox_event` (poison, error_count ≥ 10)   |Permanent до manual review                |Manual                                   |Не удаляется автоматически; alert в Sentry                        |

### Apple Mail Privacy Protection + ITP

См. [`PRODUCT.md#apple-mail-privacy-protection--itp`](./PRODUCT.md#apple-mail-privacy-protection--itp). Pixel-tracking open rate не работает; UTM-параметры вырезаются (iOS 18 Mail/Safari) → server-side click-through events, attribution через короткие slug’и (URL → 302 redirect).

### Санкционные ограничения, формирующие стек

[F: en.wikipedia.org/wiki/2025_internet_restrictions_in_Russia, en.wikipedia.org/wiki/Wartime_internet_restrictions_in_Russia_(2025-present)]

- Cloudflare и AWS edges регулярно блокируются в РФ-сегменте.
- Stripe в РФ не оперирует с 2022 → отвергает Clerk billing, Convex Pro.
- Google Cloud Billing не принимает российские карты.
- Apple Developer Enterprise Program прекращена для РФ 12 февраля 2025.
- Google Play выплаты на российские счета остановлены 26 декабря 2024.

-----

## Level C для критичных контекстов

Шесть готовых Level C: **Identity & Auth**, **Events (с Recurrence слитой внутрь)**, **RSVP & Attendance** (три критичных, реализуются end-to-end в пилоте) + **Contacts Sharing**, **Recommendations**, **Localization** (добавлены в P0 Wave 1, лёгкое покрытие). Level C для оставшихся 10 контекстов — после Pilot Этапа 0 (см. Iteration 9 в `docs/iterations/iteration-5.5-roadmap.md` step 24).

### UUID Strategy (применимо ко всем PK и токенам)

Стратегия UUID разделена по семантической роли:

- **PK всех write-heavy таблиц** (`events_event`, `rsvp_event_participant`, `rsvp_guest_rsvp`, `contacts_sharing_share`, `notifications_delivery`, `outbox_event`, `audit_log_pii_access`, `events_event_translation`): **UUIDv7**. Содержит timestamp в первых 48 битах → sequential по времени → ~12× быстрее INSERT и ~24% меньше размер индекса по сравнению с UUIDv4 на 50M+ rows [F: credativ.de/en/blog/postgresql-en/a-deeper-look-at-old-uuidv4-vs-new-uuidv7-in-postgresql-18 — 20:39 мин vs 1:46 мин на batch 50M rows; index size 1981 MB vs 1504 MB].
- **PK справочников** (`localization_country`, `localization_locale`, `localization_city`, `events_category`, `events_tag`): UUIDv4 допустим — низкий volume insertions, разница не материальна.
- **Session / CSRF / Magic-link / OTP / API-key tokens**: **НИКОГДА UUIDv7.** UUIDv7 содержит timestamp в первых 48 битах → predictable, атакующий с одним токеном может угадать соседние. Используем `gen_random_uuid()` (UUIDv4) или `secrets.token_urlsafe(32)` для tokens [В: вытекает из IETF RFC 9562 §6.2 «UUID Best Practices» + community guidance Vidun Pallegoda «You should never use UUID v7 for session tokens»].

**Реализация:**

- **PG 18+ (если доступен в Yandex Managed на момент Phase 1):** встроенный `uuidv7()` — без extensions.
- **PG 17 (текущий target):** через extension `pg_uuidv7` [F: github.com/fboulnois/pg_uuidv7] — добавляется в `apps/core/migrations/0001_extensions.py` (см. ADR-006 → Required PostgreSQL extensions). Альтернатива: генерация на стороне Python через `uuid-utils` или `uuid6` package — тогда без extension, но `DEFAULT uuidv7()` в DDL не работает (нужно передавать UUID из приложения).

**[?] Caveat:** Yandex Managed PostgreSQL 18 availability на дату Phase 1 — необходимо verify через `SELECT version()` в Phase 0. Если только PG 17 — `pg_uuidv7` extension; если PG 18 — нативно.

**Backward compatibility:** при переходе с UUIDv4 на UUIDv7 существующие PK НЕ меняются (UUID v4 ↔ v7 — не семантическая конверсия, невозможна). Только новые таблицы используют v7. Для текущего pre-MVP состояния — все Level C DDL ниже сразу написаны с `uuidv7()`.

### Outbox (cross-cutting infrastructure)

Таблица `outbox_event` — единственный канал cross-context коммуникации в проекте (Архитектурный принцип 8). Все side-effects, пересекающие границу bounded context (например, RSVP создан → нужно отправить notification → нужно обновить recommendations cache), идут через outbox, не через прямые вызовы или Django signals.

**Схема:**

```sql
CREATE TABLE outbox_event (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),
    event_type      VARCHAR(128) NOT NULL,
    -- 'RSVPCreated' | 'EventPublished' | 'ContactShareGranted' | 'NotificationAcknowledged' | ...
    aggregate_type  VARCHAR(64) NOT NULL,
    -- 'Event' | 'User' | 'Group' | 'Series' | 'Notification'
    aggregate_id    UUID NOT NULL,
    payload         JSONB NOT NULL,
    -- Денормализованный snapshot для consumers — не requires JOIN на исходную таблицу
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ NULL,
    -- NULL = pending; NOT NULL = доставлено всем subscribers
    error_count     INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT NULL,
    -- Для debug; при error_count > 10 — alert в Sentry + manual review

    CHECK (error_count >= 0)
);

-- Partial index — основной горячий путь worker'а (только pending события)
CREATE INDEX outbox_event_pending_idx
    ON outbox_event (created_at)
    WHERE published_at IS NULL;

-- Index для retention cleanup
CREATE INDEX outbox_event_published_idx
    ON outbox_event (published_at)
    WHERE published_at IS NOT NULL;
```

**RLS:** не применяется — это infrastructure-таблица. Доступ только через service-роль (`act_app`), Django Admin через `act_admin`. Никакие user-attributable данные не должны попадать в `outbox_event.payload` без явного encryption.

**Service-layer паттерн:**

```python
# apps/core/outbox/services.py
from django.db import transaction
from .models import OutboxEvent

def publish_event(
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict,
) -> None:
    """Записывает событие в outbox внутри текущей транзакции.
    Procrastinate worker позже доставит подписчикам.
    Гарантия at-least-once: consumer ОБЯЗАН быть идемпотентен
    (использовать event.id как dedupe key).
    """
    OutboxEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
```

```python
# apps/events/services.py
def create_event(*, organizer_user_id: UUID, ...) -> EventDTO:
    with transaction.atomic():
        event = Event.objects.create(...)
        outbox.publish_event(
            event_type='EventPublished',
            aggregate_type='Event',
            aggregate_id=event.id,
            payload={
                'organizer_id': str(organizer_user_id),
                'city_id': str(event.city_id),
                'starts_at': event.starts_at.isoformat(),
            },
        )
    # Транзакция закоммитилась — outbox_event запись гарантированно есть в БД
    # Worker подхватит через ≤5 секунд
    return EventDTO.from_orm(event)
```

**Procrastinate periodic task** (poll каждые 5 секунд):

```python
# apps/core/outbox/tasks.py
@app.periodic_task(cron='*/5 * * * * *')
def deliver_outbox_events():
    events = (
        OutboxEvent.objects
        .filter(published_at__isnull=True)
        .order_by('created_at')
        [:100]
    )
    for event in events:
        try:
            dispatch_to_subscribers(event)
            event.published_at = timezone.now()
            event.save(update_fields=['published_at'])
        except Exception as e:
            event.error_count += 1
            event.last_error = str(e)[:1000]
            event.save(update_fields=['error_count', 'last_error'])
            if event.error_count >= 10:
                # Alert; нужно ручное расследование
                logger.error('Outbox event poison message', event_id=event.id)
```

**Subscribers** регистрируются в `apps/<ctx>/subscribers.py` через декоратор:

```python
# apps/notifications/subscribers.py
@subscribe('RSVPCreated')
def send_rsvp_confirmation(event_payload: dict) -> None:
    # Идемпотентно: проверяем notification_delivery по correlation_id = outbox event.id
    ...
```

**Retention** — outbox events удаляются через 30 дней после `published_at` (Procrastinate cron task; см. Data Retention Policies в Wave 3). Это даёт окно для re-replay при инциденте и компактен для monitoring (`SELECT COUNT(*) FROM outbox_event WHERE published_at IS NULL` — alert > 100).

**Альтернативные библиотеки** (если ручная реализация окажется громоздкой): `django-outbox-pattern` v3.1.0 (PyPI, Feb 2026, активный) или `jaiminho` (Loadsmart). Выбор — после Phase 1 на основе опыта; ручная реализация выше — ~150 строк Python.

### RLS Operational Constraints (применимо ко всем RLS-таблицам)

Этот раздел собирает обязательные операционные правила для всех RLS-таблиц проекта. **Нарушение любого пункта = security incident.** Все Level C ниже опираются на эти правила; в DDL-блоках конкретных контекстов они не дублируются.

#### 1. Middleware-pattern с обязательной транзакцией

`SET LOCAL` живёт только до `COMMIT`. PgBouncer в transaction-pooling режиме возвращает connection в pool после commit — без оборачивания в `transaction.atomic()` следующий запрос на этом же физическом коннекте получит чужой `app.current_user_id`. Это **cross-tenant leak**, потенциальный CVE.

```python
# apps/core/rls_middleware.py
from django.db import connection, transaction

class RLSContextMiddleware:
    NULL_UUID = '00000000-0000-0000-0000-000000000000'

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = (
            str(request.user.id)
            if request.user.is_authenticated
            else self.NULL_UUID
        )
        with transaction.atomic():
            with connection.cursor() as cursor:
                # SET LOCAL ограничен текущей транзакцией;
                # PgBouncer transaction-mode pooling безопасен.
                cursor.execute(
                    "SELECT set_config('app.current_user_id', %s, true)",
                    [user_id],
                )
            return self.get_response(request)
```

Источник риска: PgBouncer features matrix; pganalyze.com/blog/postgres-row-level-security-ruby-rails («have a risk that the security context gets mixed up»); dev.to/dvoraj75 «Why PostgreSQL Row-Level Security Is the Right Approach to Django Multitenancy».

#### 2. FORCE ROW LEVEL SECURITY на каждой RLS-таблице

Без `FORCE` владелец таблицы (типично — application DB role) обходит политики. Это типичная ошибка Django-проектов, где app-роль владеет всеми таблицами.

```sql
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <table> FORCE ROW LEVEL SECURITY;
```

[F: PostgreSQL 17 docs `ALTER TABLE ... FORCE ROW LEVEL SECURITY`]

#### 3. Fail-closed default policy (RESTRICTIVE) на каждой RLS-таблице

PERMISSIVE policies (specific) комбинируются OR-логикой. RESTRICTIVE policies — AND-логикой. Дефолтная RESTRICTIVE policy `USING (false)` блокирует доступ к строкам, не покрытым specific policies — гарантирует, что забытая на новой колонке/view policy не даст implicit allow.

```sql
CREATE POLICY <table>_default_deny ON <table>
    AS RESTRICTIVE
    FOR ALL
    TO PUBLIC
    USING (false);
-- Дальше идут specific PERMISSIVE policies; они «открывают» доступ для известных кейсов.
```

#### 4. Отдельная DB-роль для Django Admin с BYPASSRLS

Django Admin должен видеть ВСЕ строки независимо от RLS — иначе модерация невозможна. Решение — отдельная роль:

```sql
-- Основное приложение (без BYPASSRLS, под RLS):
CREATE ROLE act_app LOGIN PASSWORD '<...>';
GRANT USAGE ON SCHEMA public TO act_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO act_app;

-- Django Admin (с BYPASSRLS):
CREATE ROLE act_admin LOGIN PASSWORD '<...>';
ALTER ROLE act_admin BYPASSRLS;
GRANT USAGE ON SCHEMA public TO act_admin;
GRANT ALL ON ALL TABLES IN SCHEMA public TO act_admin;
```

`DATABASES['default']` в Django использует `act_app`; `DATABASES['admin']` (отдельный alias) — `act_admin`. Django Admin views декорируются `@using('admin')` либо переключают через middleware. Каждое чтение PII через admin-роль логируется в `audit_log_pii_access` (см. Wave 3). Источник: Supabase docs «Bypass RLS for specific roles».

#### 5. Запрет `.raw()` queries вне `apps.core.rls`

Raw SQL и `pg_dump` — известные RLS bypass-векторы. Защита через `import-linter` контракт:

```ini
[importlinter:contract:no-raw-sql-outside-rls]
name = Raw SQL only in apps.core.rls
type = forbidden
source_modules = apps.*
forbidden_modules =
    django.db.models.expressions.RawSQL
    django.db.connection.cursor
ignore_imports =
    apps.core.rls.* -> django.db.connection.cursor
    apps.core.rls.* -> django.db.models.expressions.RawSQL
```

Источник: dev.to/dvoraj75.

#### 6. Миграции прогоняются прямым подключением к PG

`PG_BOUNCER_HOST=""` для `manage.py migrate` — `CREATE INDEX CONCURRENTLY` и advisory locks несовместимы с transaction-pooling. Прописать в Coolify deploy script как `pre-deploy hook`.

#### 7. RLS Performance Patterns

[F: supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices-Z5Jjwv] «Always index columns referenced in RLS policies. Missing indexes are the top performance killer» — Supabase benchmarks показывают ~100× speedup на больших таблицах при правильном indexing. Применяем три обязательных pattern:

**(a) Индексы под policy expressions обязательны.** Каждое поле, упомянутое в RLS-предикате, должно иметь индекс — partial где применимо (например, `WHERE revoked_at IS NULL` для `contacts_sharing_share` отсекает ~50% rows из индекса). Конкретные индексы — в DDL соответствующих таблиц Level C.

**(b) `(SELECT)` wrap для функций.** Вместо `USING (current_setting('app.current_user_id')::uuid = user_id)` пишем `USING (user_id = (select current_setting('app.current_user_id'))::uuid)`. PG оптимизатор переключается на `InitPlan` и кеширует результат функции на весь запрос вместо вызова на каждую row — speedup от 10× до 1000× на больших sequential scans. Все Level C RLS policies ниже используют этот pattern.

**(c) Минимизация policy expressions.** Избегать сложных `JOIN` / `EXISTS` внутри `USING`. Если необходимо (как в `contacts_share_recipient_select` с bilateral consent через EXISTS) — обеспечить index на колонки подзапроса (см. `contacts_share_reverse_idx`). Альтернатива — вынести логику в SQL function с `STABLE`-volatility (PG может cache результат function на whole query).

**Пример (применён в Contacts Sharing):**

```sql
-- Без partial index: full table scan
-- CREATE INDEX contacts_share_to_idx ON contacts_sharing_share(to_user_id);

-- С partial index: только активные share-grants в индексе → ~50% размер,
-- index-only scan для RLS-предиката
CREATE INDEX contacts_share_to_active_idx
    ON contacts_sharing_share(to_user_id)
    WHERE revoked_at IS NULL;
```

**Не-immutable выражения в partial index:** PG отклоняет `WHERE expires_at > NOW()` (NOW() is volatile). Для recommendations cache — обычный B-tree + фильтрация в WHERE-clause запроса:

```sql
-- НЕ работает (NOW() volatile):
-- CREATE INDEX ... WHERE expires_at > NOW();

-- Работает — фильтрация в запросе, не в индексе:
CREATE INDEX recommendations_score_user_score_idx
    ON recommendations_score_cache(user_id, score DESC);

-- В сервисе:
-- SELECT ... WHERE user_id = $1 AND expires_at > NOW()
--   ORDER BY score DESC LIMIT 20;
```

-----

### Identity & Auth

**Ключевые таблицы:**

|Таблица             |Поля                                                                                                                                           |
|--------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
|`identity_auth_user`|`id UUID PK`, `primary_email`, `phone_e164`, `telegram_id` (unique nullable), `locale`, `country_code`, `city_id`, `status`, `created_at`      |
|`Session`           |server-side sessions с device fingerprinting                                                                                                   |
|`MagicLinkToken`    |256-bit CSPRNG, 15 min TTL, one-time use                                                                                                       |
|`OAuthProvider`     |справочник: `telegram`, в будущем `vk`, `yandex`                                                                                               |
|`OAuthIdentity`     |связь `User ↔ provider_uid`                                                                                                                    |
|`PasskeyCredential` |через `django-otp-webauthn` [F: github.com/Stormbase/django-otp-webauthn]                                                                      |
|`ConsentRecord`     |`id`, `user_id`, `purpose` (`core_processing`, `marketing`, `contact_sharing`, `cross_border_transfer`, `cookies_essential`, `cookies_analytics`, `cookies_marketing`), `consent_text_hash`, `granted_at`, `withdrawn_at`, `ip_address`|

**RLS-policies (пример):**

> Все три таблицы ниже подчиняются [RLS Operational Constraints](#rls-operational-constraints-применимо-ко-всем-rls-таблицам): обязательны `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy. PERMISSIVE policies ниже «открывают» доступ для конкретных кейсов.

```sql
-- Sessions
ALTER TABLE identity_auth_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_auth_session FORCE ROW LEVEL SECURITY;
CREATE POLICY identity_auth_session_default_deny ON identity_auth_session
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY session_owner ON identity_auth_session
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);

-- Passkeys
ALTER TABLE identity_auth_passkey ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_auth_passkey FORCE ROW LEVEL SECURITY;
CREATE POLICY identity_auth_passkey_default_deny ON identity_auth_passkey
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY passkey_owner ON identity_auth_passkey
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);

-- Consent records
ALTER TABLE identity_auth_consent ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_auth_consent FORCE ROW LEVEL SECURITY;
CREATE POLICY identity_auth_consent_default_deny ON identity_auth_consent
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY consent_owner ON identity_auth_consent
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);
```

Синтаксис `(select current_setting(...))` — обязательная обёртка (см. RLS Operational Constraints): PG кеширует `initPlan` на весь запрос, ~10–100× speedup vs прямой вызов. Источник синтаксиса — [F: pganalyze.com/blog/postgres-row-level-security-django-python] + [F: dev.to/dvoraj75/why-postgresql-row-level-security-is-the-right-approach-to-django-multitenancy-3e1m] + [F: supabase.com/docs/guides/troubleshooting/rls-performance-and-best-practices].

#### Cookie consent UI

Компонент `<CookieConsentBanner>` появляется при первом визите неаутентифицированного пользователя на любую страницу. **Non-modal**, не блокирует контент — баннер фиксирован внизу viewport с тремя explicit-чекбоксами:

|Уровень            |Default                                                                  |Применение                                                     |
|-------------------|-------------------------------------------------------------------------|---------------------------------------------------------------|
|`cookies_essential`|Всегда granted (информационно — отказаться нельзя без потери функционала)|Session ID cookie, CSRF token, locale preference               |
|`cookies_analytics`|Default off; opt-in                                                      |PostHog tracking events (page views, feature usage)            |
|`cookies_marketing`|Default off; opt-in                                                      |Retargeting (если будет добавлено в Phase 6+); сейчас неактивно|

Выбор пользователя записывается в `identity_auth_consent` тремя отдельными записями с purpose ∈ `{cookies_essential, cookies_analytics, cookies_marketing}`, с `ip_address` (для аудита РКН), `user_agent`, `granted_at`. Withdraw — через `/settings/privacy` страницу (запись `withdrawn_at`).

**ВАЖНО:** баннер появляется ДО первого PostHog `init()` call — иначе analytics tracking начинается без consent, что нарушает 152-ФЗ ст. 9. Реализуется через client-side guard в `app/[locale]/layout.tsx`:

```typescript
'use client';
import { useConsent } from '@/lib/consent';
// PostHog инициализируется только при consent.analytics === true
```

#### PII Audit Log

Каждое чтение PII-поля (`phone_e164`, `channel_value`, `verification_documents`, и т.д.) admin-ом, moderator-ом или service-ролью **должно** логироваться в `audit_log_pii_access`. Это требование 152-ФЗ ст. 7 (защита ПДн) + готовый artifact для РКН-аудита.

```sql
CREATE TABLE audit_log_pii_access (
    id                  UUID PRIMARY KEY DEFAULT uuidv7(),
    actor_user_id       UUID NOT NULL REFERENCES identity_auth_user(id),
    actor_role          VARCHAR(32) NOT NULL,
    -- 'self' | 'admin' | 'moderator' | 'service'
    accessed_user_id    UUID NOT NULL REFERENCES identity_auth_user(id),
    accessed_field      VARCHAR(64) NOT NULL,
    -- 'phone' | 'email' | 'telegram_id' | 'verification_doc' | 'channel_value' | ...
    purpose             VARCHAR(128) NOT NULL,
    -- человекочитаемое: 'admin_user_lookup', 'rsvp_merge_on_signup',
    -- 'notification_delivery', 'self_view'
    ip_hash             VARCHAR(64) NOT NULL,
    -- SHA-256(actor IP + daily salt) — не сам IP (избегаем хранения PII актора)
    request_id          UUID NULL,  -- корреляция с Sentry/LGTM trace
    accessed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX audit_log_pii_access_accessed_user_idx
    ON audit_log_pii_access(accessed_user_id, accessed_at DESC);
CREATE INDEX audit_log_pii_access_actor_idx
    ON audit_log_pii_access(actor_user_id, accessed_at DESC);

ALTER TABLE audit_log_pii_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log_pii_access FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_log_pii_default_deny ON audit_log_pii_access
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
-- Subject access: user видит логи доступа К СВОИМ данным (право знать кто читал)
CREATE POLICY audit_log_pii_subject_read ON audit_log_pii_access FOR SELECT
USING (accessed_user_id = (select current_setting('app.current_user_id'))::uuid);
```

**Implementation pattern**: middleware-декоратор на все PII-read endpoints + DTO-уровень `pii_access_logger` оборачивает чтения из `services.py`. `self_view` (когда `actor = accessed`) логируется, но менее детально (только counters для antifraud).

**Retention**: 1 год от `accessed_at` (минимум для РКН-аудита; см. Data Retention Policies).

### Events context (включая Recurrence)

**Сущности:** `Event`, `EventSeries`, `RecurrenceRule` (RFC 5545), `EXDate`, `RecurrenceOverride`, `EventCoverImage`.

[F: RFC 5545]:

- `RRULE` — правило (`FREQ=WEEKLY;BYDAY=TU,TH`)
- `EXDATE` — исключения
- `RECURRENCE-ID` — id конкретного экземпляра при override

### RSVP & Attendance — services + endpoints (signatures)

```python
def rsvp_signed_in(*, user_id: UUID, event_id: UUID, note: str | None) -> ParticipantDTO:
    ...

def rsvp_as_guest(*, event_id: UUID, contact_channel: str, contact_value: str,
                  display_name: str, request_meta: RequestMeta) -> GuestRSVPDTO:
    """
    Creates GuestRSVP in 'pending' if channel='email' (sends verify mail);
    immediate 'going' if channel='telegram_handle'.
    Enforces UNIQUE (event_id, channel, value).
    """

def merge_guest_on_signup(*, user_id: UUID, contact_channel: str, contact_value: str) -> int:
    """
    Called from identity_auth.signup_with_telegram_oidc / verify_magic_link.
    Finds all GuestRSVP where (channel, value) match and merged_into_user_id IS NULL.
    For each: create EventParticipant(merged_from_guest_id), set GuestRSVP.merged_into_user_id.
    Returns number of merged.
    """
```

**RLS policies:**

> Применяются [RLS Operational Constraints](#rls-operational-constraints-применимо-ко-всем-rls-таблицам). `(select …)` wrap для `current_setting` — обязателен.

```sql
-- EventParticipant: участник видит свои записи; organizer видит все по своему event
ALTER TABLE rsvp_event_participant ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvp_event_participant FORCE ROW LEVEL SECURITY;
CREATE POLICY rsvp_event_participant_default_deny ON rsvp_event_participant
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY participant_visibility ON rsvp_event_participant FOR SELECT
USING (
    user_id = (select current_setting('app.current_user_id'))::uuid
    OR event_id IN (
        SELECT id FROM events_event
        WHERE owner_id = (select current_setting('app.current_user_id'))::uuid
    )
);

-- GuestRSVP: видим только organizer-у соответствующего event-а
ALTER TABLE rsvp_guest_rsvp ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvp_guest_rsvp FORCE ROW LEVEL SECURITY;
CREATE POLICY rsvp_guest_rsvp_default_deny ON rsvp_guest_rsvp
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY guest_visible_to_owner ON rsvp_guest_rsvp FOR SELECT
USING (
    event_id IN (
        SELECT id FROM events_event
        WHERE owner_id = (select current_setting('app.current_user_id'))::uuid
    )
);
```

### Contacts Sharing

**Назначение.** Хранит каналы связи пользователей (Telegram username, phone, email, Instagram, custom URL) и bilateral consent-based раскрытия контактов на конкретный Event. Используется UI профиля и RSVP-флоу. Cross-context зависимости: ссылается на `identity_auth_user`, `identity_auth_consent` (для 152-ФЗ ст. 9), `events_event`. Не дублирует `ConsentRecord` — переиспользует с `purpose='contact_sharing'`.

**Схема таблиц:**

```sql
-- Каналы связи пользователя
CREATE TABLE contacts_sharing_channel (
    id              UUID PRIMARY KEY DEFAULT uuidv7(),  -- write-heavy (новые каналы при signup); UUIDv7 для производительности
    user_id         UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    channel_type    VARCHAR(32) NOT NULL,
    -- 'telegram_handle' | 'phone' | 'email' | 'instagram' | 'custom_url'
    channel_value           TEXT NOT NULL,
    -- ENCRYPT_AT_REST через django-cryptography (Yandex Lockbox key). См. ADR-014.
    channel_value_hash      VARCHAR(64) NOT NULL,
    -- HMAC-SHA256(PII_HMAC_SECRET, channel_value) для exact-match lookup
    -- (например, find_user_by_phone в merge_guest_on_signup)
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, channel_type, channel_value_hash)
    -- Hash в UNIQUE — позволяет один user + один тип + множественные значения
    -- (например, два phone-канала: личный и рабочий)
);
CREATE INDEX contacts_sharing_channel_user_idx ON contacts_sharing_channel(user_id);
CREATE INDEX contacts_sharing_channel_hash_lookup_idx
    ON contacts_sharing_channel(channel_type, channel_value_hash);
-- HMAC-lookup для merge_guest_on_signup и подобных flows

-- Bilateral раскрытие контакта на конкретный Event
CREATE TABLE contacts_sharing_share (
    id                  UUID PRIMARY KEY DEFAULT uuidv7(),  -- write-heavy (share grants)
    from_user_id        UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    to_user_id          UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    event_id            UUID NOT NULL REFERENCES events_event(id) ON DELETE CASCADE,
    channel_id          UUID NOT NULL REFERENCES contacts_sharing_channel(id) ON DELETE CASCADE,
    consent_record_id   UUID NOT NULL REFERENCES identity_auth_consent(id),
    -- 152-ФЗ ст. 9 ред. 156-ФЗ: ссылка на отдельный документ согласия
    granted_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at          TIMESTAMPTZ NULL,

    UNIQUE (from_user_id, to_user_id, event_id, channel_id),
    CHECK (from_user_id <> to_user_id)
);
CREATE INDEX contacts_sharing_share_to_active_idx
    ON contacts_sharing_share(to_user_id, event_id) WHERE revoked_at IS NULL;
CREATE INDEX contacts_sharing_share_from_idx
    ON contacts_sharing_share(from_user_id);
CREATE INDEX contacts_sharing_share_event_idx
    ON contacts_sharing_share(event_id);
```

**RLS-policies:**

> Применяются [RLS Operational Constraints](#rls-operational-constraints-применимо-ко-всем-rls-таблицам).

```sql
-- Channels: пользователь видит только свои каналы
ALTER TABLE contacts_sharing_channel ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts_sharing_channel FORCE ROW LEVEL SECURITY;
CREATE POLICY contacts_sharing_channel_default_deny ON contacts_sharing_channel
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY contacts_sharing_channel_owner ON contacts_sharing_channel
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);

-- Shares: bilateral consent с reverse-lookup
ALTER TABLE contacts_sharing_share ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts_sharing_share FORCE ROW LEVEL SECURITY;
CREATE POLICY contacts_sharing_share_default_deny ON contacts_sharing_share
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);

-- Donor видит все свои grants (для UI «Мои общие контакты», включая revoked)
CREATE POLICY contacts_share_donor_select ON contacts_sharing_share FOR SELECT
USING (from_user_id = (select current_setting('app.current_user_id'))::uuid);

-- Recipient видит активные grants ТОЛЬКО при взаимности
CREATE POLICY contacts_share_recipient_select ON contacts_sharing_share FOR SELECT
USING (
    to_user_id = (select current_setting('app.current_user_id'))::uuid
    AND revoked_at IS NULL
    AND EXISTS (
        SELECT 1 FROM contacts_sharing_share rev
        WHERE rev.from_user_id = (select current_setting('app.current_user_id'))::uuid
          AND rev.to_user_id = contacts_sharing_share.from_user_id
          AND rev.event_id = contacts_sharing_share.event_id
          AND rev.revoked_at IS NULL
    )
);

-- Donor управляет только своими grants
CREATE POLICY contacts_share_donor_modify ON contacts_sharing_share
FOR ALL USING (from_user_id = (select current_setting('app.current_user_id'))::uuid);
```

**Дополнительный partial index** под EXISTS-подзапрос в recipient-policy (предотвращает sequential scan):

```sql
CREATE INDEX contacts_share_reverse_idx
    ON contacts_sharing_share (from_user_id, to_user_id, event_id)
    WHERE revoked_at IS NULL;
```

Примечание: RLS подтверждает «грант существует и доступен взаимной стороне». Гейтинг по времени (показывать channel_value только в день экземпляра серии / после starts_at одиночного Event) реализуется в сервисном слое `resolve_shared_channel`, не в RLS.

**Service-layer API:**

```python
def add_contact_channel(
    *,
    user_id: UUID,
    channel_type: ContactChannelType,
    channel_value: str,
    is_default: bool = False,
) -> ContactChannelDTO:
    """Добавляет канал пользователя; UNIQUE на (user_id, channel_type) — UPDATE при повторе."""

def remove_contact_channel(*, channel_id: UUID, user_id: UUID) -> None:
    """Soft-delete не нужен — каскад на share через ON DELETE CASCADE."""

def list_my_channels(*, user_id: UUID) -> list[ContactChannelDTO]:
    """Возвращает каналы без раскрытия value другим контекстам."""

def grant_contact_share(
    *,
    from_user_id: UUID,
    to_user_id: UUID,
    event_id: UUID,
    channel_id: UUID,
    consent_record_id: UUID,
) -> ContactShareDTO:
    """Записывает grant. Идемпотентно по UNIQUE — повторный вызов обновляет granted_at и сбрасывает revoked_at."""

def revoke_contact_share(*, share_id: UUID, user_id: UUID) -> None:
    """Только donor может revoke. Уведомление recipient НЕ отправляется (V1.1 5.2)."""

def list_my_shared_contacts(
    *,
    user_id: UUID,
    event_id: UUID | None = None,
    include_revoked: bool = False,
) -> list[ContactShareDTO]:
    """UI «Мои общие контакты» с фильтром по событию."""

def resolve_shared_channel(
    *,
    viewer_user_id: UUID,
    target_user_id: UUID,
    event_id: UUID,
    now: datetime,
) -> ContactChannelDTO | None:
    """Возвращает канал с раскрытым value, ТОЛЬКО если:
       (a) есть взаимный активный grant в обе стороны;
       (b) event.starts_at <= now (для серии — instance-date day in viewer's timezone)."""
```

**Cross-context contracts (DTOs):**

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

ContactChannelType = Literal[
    'telegram_handle', 'phone', 'email', 'instagram', 'custom_url'
]

@dataclass(frozen=True)
class ContactChannelDTO:
    id: UUID
    user_id: UUID
    channel_type: ContactChannelType
    # channel_value намеренно отсутствует в DTO — раскрытие только через resolve_shared_channel
    is_default: bool

@dataclass(frozen=True)
class ContactChannelResolvedDTO:
    """Расширенный DTO с раскрытым value — только из resolve_shared_channel."""
    id: UUID
    channel_type: ContactChannelType
    channel_value: str  # plain text для отображения в UI viewer-а

@dataclass(frozen=True)
class ContactShareDTO:
    id: UUID
    from_user_id: UUID
    to_user_id: UUID
    event_id: UUID
    channel_id: UUID
    granted_at: datetime
    revoked_at: datetime | None
```

**Integration events:**

- Публикует: `ContactShareGranted(share_id, from_user_id, to_user_id, event_id)`, `ContactShareRevoked(share_id, from_user_id, to_user_id, event_id)`.
- Подписывает: `EventCancelled(event_id)` → revoke все grants по этому event_id; `UserDeleted(user_id)` → anonymize grants, где user участвует (для 152-ФЗ право на удаление).

**Ключевые потоки:**

1. **Revocation без уведомления.** Donor клик «удалить» в UI → `revoke_contact_share` → `UPDATE revoked_at=NOW()`. Событие `ContactShareRevoked` публикуется, но Notifications его игнорирует (явное правило, не отправлять recipient — V1.1 5.2 «избегаем awkward dynamics»). Recipient на следующем `resolve_shared_channel` получит `None`.
1. **Bilateral reveal.** Donor сделал grant A→B. RLS не показывает grant B-стороне до тех пор, пока B не сделает встречный grant B→A. При втором grant обе стороны выходят из `resolve_shared_channel` с раскрытыми channel_value (если event.starts_at <= now).
1. **Каскад при отмене Event.** Organizer отменяет Event → `EventCancelled` → handler revoke все `contacts_sharing_share` по этому event_id одним UPDATE. RLS делает их невидимыми; история сохраняется для audit.

### Recommendations

**Назначение.** MVP-stub: возвращает отсортированные Events для пользователя через делегирование в Discovery с весом, смещённым в reputation. На MVP **не содержит ML, не строит профилей предпочтений, не имеет embeddings**. Используется UI каталога и e-mail дайджестами. ML-персонализация deferred до >10K MAU (см. `Что НЕ закладываем (deferred)`).

#### Stable API contract (выживает ML-миграцию без breaking changes)

Главный design goal Recommendations контекста — **стабильная сигнатура** между MVP-stub и будущей ML-реализацией. Замена implementation НЕ требует изменений в callers (UI каталога, email digest service, RSS-feed builder и т.д.).

```python
# apps/recommendations/contracts.py
def recommend_for_user(
    *,
    user_id: UUID,
    city_id: UUID | None = None,
    limit: int = 20,
    use_cache: bool = True,
) -> list[EventDTO]:
    """Возвращает ranked list events для пользователя.

    MVP-stub: top-N events from Discovery sorted by reputation_score + city filter.
    Post-ML: replace implementation (collaborative filtering / matrix factorization /
    LLM embeddings) WITHOUT changing this signature.

    Контракт:
    - Возвращает EventDTO (public DTO, не internal model) — никакого ML-leakage.
    - Идемпотентен в read-only режиме (use_cache=True): тот же user_id + city_id
      + limit → тот же result в пределах cache_ttl (текущий: 1 час).
    - Безопасен по RLS — фильтрует только публичные events видимые user_id.
    """
```

**Migration path**: смена `apps/recommendations/services.py` от stub-реализации к ML — это replace-implementation, не replace-interface. EventDTO в contracts остаётся неизменным; ranking algorithm меняется внутри.

**Anti-pattern**: добавлять параметры типа `algorithm_version` или `embedding_vector` в публичную сигнатуру — это leakage internal деталей. Все ML-параметры остаются внутри `apps/recommendations/internal/`.

**Схема таблиц:**

```sql
-- Опциональный кеш precomputed scores per (user, event).
-- На MVP может быть пустым — recommend_for_user считает on-the-fly.
-- Существует, чтобы при добавлении ML миграция была seamless.
CREATE TABLE recommendations_score_cache (
    id                  UUID PRIMARY KEY DEFAULT uuidv7(),  -- write-heavy (recomputed scores)
    user_id             UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    event_id            UUID NOT NULL REFERENCES events_event(id) ON DELETE CASCADE,
    score               NUMERIC(10, 6) NOT NULL,  -- нормализованный [0, 1]
    algorithm_version   VARCHAR(32) NOT NULL DEFAULT 'mvp_reputation_sort_v1',
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ NOT NULL,

    UNIQUE (user_id, event_id, algorithm_version)
);
CREATE INDEX recommendations_score_user_idx
    ON recommendations_score_cache(user_id, score DESC)
    WHERE expires_at > NOW();
```

**RLS-policies:**

```sql
ALTER TABLE recommendations_score_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE recommendations_score_cache FORCE ROW LEVEL SECURITY;
CREATE POLICY recommendations_score_cache_default_deny ON recommendations_score_cache
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY recommendations_score_owner ON recommendations_score_cache
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);
```

Раскрытие подобранных рекомендаций другому пользователю — это leak профиля интересов; RLS обязательна, даже если на MVP таблица почти пустая.

**Service-layer API:**

```python
def recommend_for_user(
    *,
    user_id: UUID,
    city_id: UUID | None = None,
    limit: int = 20,
    use_cache: bool = True,
) -> list[EventDTO]:
    """MVP-stub: делегирует в discovery.score_events_for_user с весами 'mature_weights'
    (см. ADR-008), фильтрует по city_id если указан. На MVP read-path — нет writes в cache."""

def recommend_for_anonymous(
    *,
    city_id: UUID,
    limit: int = 20,
) -> list[EventDTO]:
    """Для гостей без user_id — pure recency × city-fit через cold_start_weights ADR-008.
    Никакой персонализации, никакого fingerprint-tracking."""

def invalidate_user_recommendations(*, user_id: UUID) -> int:
    """Удаляет записи cache для user_id. Вызывается из event-handler на RatingPosted,
    UserPreferencesUpdated, etc. Возвращает число удалённых строк."""
```

**Cross-context contracts (DTOs):**

```python
# Контекст не вводит собственных DTO — переиспользует EventDTO из apps.events.contracts.
# В будущем (post-MVP) появится:
# @dataclass(frozen=True)
# class RecommendationDTO:
#     event: EventDTO
#     score: Decimal
#     algorithm_version: str
#     reasoning: dict | None  # для explainability в UI «почему мне это показано»
```

[Г] Решение не вводить `RecommendationDTO` на MVP: пока scoring логика тривиальна (reputation sort), оборачивание `EventDTO` создаёт техдолг без выгоды. Когда появится ML и нужны будут score/reasoning — введём отдельный DTO без ломки контракта (additive change).

**Integration events:**

- Публикует: ничего на MVP.
- Подписывает: `RatingPosted(ratee_user_id)` → `invalidate_user_recommendations(user_id=ratee_user_id)` для всех users, чьи кеши могли содержать события этого ratee (на MVP — просто truncate cache, оптимизация позже); `EventCancelled(event_id)` → удалить кеш для этого event_id; `UserPreferencesUpdated(user_id)` → `invalidate_user_recommendations` (future-proof, событие пока не публикуется).

**Ключевые потоки:**

1. **Stub recommend flow.** `recommend_for_user` → `discovery.score_events_for_user(user_id, weights=mature_weights, filters)` → возвращает топ-N. Никакого кеша на MVP.
1. **Migration-readiness.** Когда добавится ML — заменяем тело `recommend_for_user` на cache lookup → fall back to ML inference → write to cache. Сигнатура и DTO остаются.

### Localization / i18n

**Назначение.** Справочники стран/городов/категорий/тегов с локализованными именами в JSONB; список поддерживаемых UI-локалей; negotiation locale для запроса; fallback chain. Используется всеми контекстами через `apps.localization.contracts`. UI-строки фронта живут в `messages/{locale}.json` (next-intl + ICU MessageFormat), не в БД — БД хранит только локализуемые данные доменных сущностей.

#### Translation strategy by use case

Не вся локализация одинакова — стратегия зависит от частоты обновлений и сложности структуры:

|Тип контента                                                  |Подход                                                   |Причина                                                                                         |
|--------------------------------------------------------------|---------------------------------------------------------|------------------------------------------------------------------------------------------------|
|UI-строки фронта (кнопки, labels, error messages)             |`messages/{locale}.json` в репо (next-intl)              |Управляется кодом, версионируется через git, no DB roundtrip, ICU MessageFormat для плюрализации|
|Справочники (country, city, category, tag, locale)            |JSONB колонка `localized_names`                          |Маленький объём (≤500 rows), редкие изменения, expression index на конкретный locale            |
|Пользовательский контент (event title, description, group bio)|Выделенная translation-таблица `events_event_translation`|Per-field updates, audit, FTS per-locale dictionary, content-moderation per language            |

**JSONB-индексы для справочников.** Замена GIN на expression index — GIN полезен только для «search across all locales» (например, искать «Москва» в любой из локалей), но для типичного lookup-by-current-locale он избыточен:

```sql
-- Старая стратегия (GIN — overkill для locale lookup):
-- CREATE INDEX localization_country_names_gin ON localization_country USING GIN (localized_names);

-- Новая: expression index per-locale (быстрее, меньше):
CREATE INDEX localization_country_name_ru_idx
    ON localization_country ((localized_names->>'ru-RU'));
CREATE INDEX localization_country_name_en_idx
    ON localization_country ((localized_names->>'en-US'));

-- GIN держим ТОЛЬКО если нужен cross-locale search:
-- CREATE INDEX localization_country_names_gin
--     ON localization_country USING GIN (localized_names);
-- (на MVP не нужен — добавим если появится use case)
```

#### Russian plural rules в ICU MessageFormat

Русский язык имеет **четыре** плюральных формы (one / few / many / other), английский — две (one / other). Копировать английский паттерн в `messages/ru-RU.json` ломает грамматику.

**Корректный пример** в `messages/ru-RU.json` (next-intl + ICU MessageFormat):

```json
{
  "events_count": "{count, plural, one {# событие} few {# события} many {# событий} other {# событий}}"
}
```

Где:

- `one` — для 1, 21, 31, … (1 событие)
- `few` — для 2–4, 22–24, … (2 события)
- `many` — для 0, 5–20, 25–30, … (5 событий)
- `other` — fallback для дробных и unknown

**АНТИ-ПАТТЕРН** (часто делает AI без знания русского):

```json
{
  "events_count": "{count, plural, one {# событие} other {# событий}}"  // ❌ ЛОМАЕТ грамматику для 2, 3, 4
}
```

Каждый человекочитаемый ключ в `messages/ru-RU.json` с числом должен использовать четыре формы. CI-проверка через `intl-messageformat-parser` валидирует наличие всех four cases для `ru-RU` локали при наличии `{n, plural, ...}`.

#### Next.js integration patterns (next-intl 4.x)

|Контекст                            |API                                                              |Когда использовать                                                                                                    |
|------------------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
|Async Server Component              |`await getTranslations(namespace)`                               |Server-rendered страницы (`app/[locale]/...`) — основной случай                                                       |
|Client Component                    |`useTranslations(namespace)` hook                                |Только если нужна интерактивность с локалью (language switcher, dynamic forms)                                        |
|Static rendering                    |`setRequestLocale(locale)` обязателен в `app/[locale]/layout.tsx`|Иначе fall-back на dynamic rendering, SSG ломается [F: next-intl docs «Server Components» + Next.js 16 ISR guidelines]|
|Background jobs / outbox subscribers|`apps.localization.contracts.get_translated_string(key, locale)` |Server-only функция; нет React-контекста                                                                              |

**Server-only функции** в `apps.localization.contracts` имеют префикс `get_*` (async-friendly через Django ORM); **client-side** — только через next-intl hooks. Никогда не импортируем `next-intl` в Python service-layer и наоборот.

**Схема таблиц:**

```sql
-- Поддерживаемые UI-локали
CREATE TABLE localization_locale (
    code                    VARCHAR(8) PRIMARY KEY,  -- 'ru-RU', 'en-US', 'en-GB', ...
    icu_language_tag        VARCHAR(16) NOT NULL,    -- BCP 47, например 'ru' или 'en'
    fallback_locale_code    VARCHAR(8) NULL REFERENCES localization_locale(code),
    is_rtl                  BOOLEAN NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order              INTEGER NOT NULL DEFAULT 100,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Страны (ISO 3166-1 alpha-2)
CREATE TABLE localization_country (
    id                      UUID PRIMARY KEY DEFAULT uuidv7(),
    iso_code                VARCHAR(2) NOT NULL UNIQUE,
    localized_names         JSONB NOT NULL,
    -- {"ru-RU": "Россия", "en-US": "Russia"}
    default_locale_code     VARCHAR(8) NULL REFERENCES localization_locale(code),
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order              INTEGER NOT NULL DEFAULT 100,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Expression indexes per-locale (см. Translation strategy выше) — быстрее GIN для locale lookup
CREATE INDEX localization_country_name_ru_idx
    ON localization_country ((localized_names->>'ru-RU'));
CREATE INDEX localization_country_name_en_idx
    ON localization_country ((localized_names->>'en-US'));

-- Города
CREATE TABLE localization_city (
    id                      UUID PRIMARY KEY DEFAULT uuidv7(),
    country_id              UUID NOT NULL REFERENCES localization_country(id) ON DELETE RESTRICT,
    localized_names         JSONB NOT NULL,
    -- {"ru-RU": "Москва", "en-US": "Moscow"}
    iana_timezone           VARCHAR(64) NOT NULL,  -- 'Europe/Moscow'
    latitude                NUMERIC(9, 6) NULL,
    longitude               NUMERIC(9, 6) NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order              INTEGER NOT NULL DEFAULT 100,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX localization_city_country_idx ON localization_city(country_id);
CREATE INDEX localization_city_name_ru_idx
    ON localization_city ((localized_names->>'ru-RU'));
CREATE INDEX localization_city_name_en_idx
    ON localization_city ((localized_names->>'en-US'));

-- Категории активности (тренировка, консультация, тусовка, культурное, …)
CREATE TABLE localization_category (
    id                      UUID PRIMARY KEY DEFAULT uuidv7(),
    slug                    VARCHAR(64) NOT NULL UNIQUE,
    -- 'training', 'consultation', 'meetup', 'cultural', 'networking', 'walk', 'other'
    parent_category_id      UUID NULL REFERENCES localization_category(id),
    localized_names         JSONB NOT NULL,
    localized_descriptions  JSONB NOT NULL DEFAULT '{}',
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order              INTEGER NOT NULL DEFAULT 100,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Свободные теги
CREATE TABLE localization_tag (
    id                      UUID PRIMARY KEY DEFAULT uuidv7(),
    slug                    VARCHAR(64) NOT NULL UNIQUE,
    localized_names         JSONB NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Хеш каталога для frontend cache busting (next-intl)
CREATE TABLE localization_catalog_version (
    locale_code             VARCHAR(8) PRIMARY KEY REFERENCES localization_locale(code),
    catalog_hash            VARCHAR(64) NOT NULL,  -- SHA-256 первой 32 hex символа
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Переводы пользовательского контента (per-field, не JSONB) —
-- см. Translation strategy by use case выше.
-- Логически принадлежит Events context, но schema живёт здесь для consistency
-- с другими translation-таблицами (пока их одна; будут groups_group_translation etc).
CREATE TABLE events_event_translation (
    id                      UUID PRIMARY KEY DEFAULT uuidv7(),
    event_id                UUID NOT NULL,
    -- REFERENCES events_event(id) ON DELETE CASCADE — добавится после events_event DDL
    locale_code             VARCHAR(8) NOT NULL REFERENCES localization_locale(code),
    field_name              VARCHAR(64) NOT NULL,
    -- 'title' | 'description' | 'location_text' | 'agenda_html'
    value                   TEXT NOT NULL,
    is_machine_translated   BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by_user_id      UUID NULL REFERENCES identity_auth_user(id),

    UNIQUE (event_id, locale_code, field_name)
);

CREATE INDEX events_event_translation_event_idx
    ON events_event_translation(event_id);
CREATE INDEX events_event_translation_locale_idx
    ON events_event_translation(locale_code);

-- FTS per-locale: разные dictionary для русского и английского
CREATE INDEX events_event_translation_fts_ru
    ON events_event_translation USING GIN (to_tsvector('russian', value))
    WHERE locale_code = 'ru-RU';
CREATE INDEX events_event_translation_fts_en
    ON events_event_translation USING GIN (to_tsvector('english', value))
    WHERE locale_code = 'en-US';
```

**RLS-policies:**

```sql
-- RLS НЕ включена на справочниках localization_*: это reference data, world-readable
-- для всех активных строк. Мутации ограничены на application-уровне (admin-only services).
-- Это явное архитектурное решение — комментарий обязателен для миграций.
```

**Service-layer API:**

```python
def list_active_locales() -> list[LocaleDTO]:
    """Список UI-локалей для language switcher."""

def get_locale_for_request(
    *,
    query_param: str | None,
    cookie_locale: str | None,
    accept_language_header: str | None,
    default: str = 'ru-RU',
) -> str:
    """Negotiation order: query_param > cookie > Accept-Language > default 'ru-RU'.
    Возвращает code из localization_locale, гарантированно is_active=TRUE."""

def resolve_localized_name(
    *,
    localized_names: dict[str, str],
    locale_code: str,
) -> LocalizedStringDTO:
    """Возвращает имя с обходом fallback chain: locale → fallback_locale → 'ru-RU'.
    Помечает is_fallback=True если использован не запрошенный locale."""

def list_active_countries(*, locale_code: str) -> list[CountryDTO]:
    """Все активные страны, отсортированные по sort_order, с resolved именами."""

def list_active_cities(*, country_id: UUID, locale_code: str) -> list[CityDTO]:
    """Активные города страны с resolved именами."""

def list_active_categories(
    *,
    locale_code: str,
    parent_category_id: UUID | None = None,
) -> list[CategoryDTO]:
    """Категории; если parent_category_id=None — только top-level."""

def list_active_tags(*, locale_code: str, slugs: list[str] | None = None) -> list[TagDTO]:
    """Все активные теги или подмножество по slugs."""

def get_catalog_hash(*, locale_code: str) -> str:
    """SHA-256 hash для frontend cache busting next-intl каталога."""

def admin_set_localized_name(
    *,
    table: Literal['country', 'city', 'category', 'tag'],
    row_id: UUID,
    locale_code: str,
    value: str,
    actor_user_id: UUID,
) -> None:
    """Admin-only: обновляет JSONB localized_names[locale_code]=value. Audit log записывается."""
```

**Cross-context contracts (DTOs):**

```python
@dataclass(frozen=True)
class LocaleDTO:
    code: str                        # 'ru-RU'
    icu_language_tag: str            # 'ru'
    fallback_locale_code: str | None
    is_rtl: bool

@dataclass(frozen=True)
class LocalizedStringDTO:
    value: str
    actual_locale_code: str          # может отличаться от запрошенного при fallback
    is_fallback: bool

@dataclass(frozen=True)
class CountryDTO:
    id: UUID
    iso_code: str
    name: str                        # уже разрешено в caller's locale

@dataclass(frozen=True)
class CityDTO:
    id: UUID
    country_id: UUID
    name: str                        # разрешено
    iana_timezone: str
    latitude: Decimal | None
    longitude: Decimal | None

@dataclass(frozen=True)
class CategoryDTO:
    id: UUID
    slug: str
    name: str                        # разрешено
    parent_category_id: UUID | None

@dataclass(frozen=True)
class TagDTO:
    id: UUID
    slug: str
    name: str                        # разрешено
```

**Integration events:**

- Публикует: `LocalizationCatalogUpdated(locale_code, new_hash)` — для frontend cache invalidation (next-intl re-fetch).
- Подписывает: ничего на MVP (admin-driven changes).

**Ключевые потоки:**

1. **Fallback chain.** Запрос `resolve_localized_name(localized_names={"ru-RU": "Россия"}, locale_code='en-US')` → `en-US` отсутствует → `localization_locale.fallback_locale_code` для `en-US` = `ru-RU` → возвращает `"Россия"` с `is_fallback=True`. Frontend по флагу `is_fallback=True` показывает (опционально) пометку, что перевод недоступен.
1. **Translation workflow.** UI-строки фронта живут в `messages/{ru-RU,en-US}.json` (next-intl + ICU MessageFormat); CI lint падает, если ключи в `en-US.json` отсутствуют относительно `ru-RU.json` (это нарушение i18n с дня 1). Локализуемые данные доменных сущностей (имена городов, категорий, тегов, описания) — в JSONB БД через admin UI.
1. **Cache busting фронта.** Admin меняет имя категории → `LocalizationCatalogUpdated` → backend пересчитывает `catalog_hash` → frontend на следующем bootstrap получает новый hash и re-fetch-ает каталог.

-----

## Bootstrap: Phase 0 + Phase 1

### Phase 0 — Legal + Tooling (1–2 недели)

|#      |Задача                                                                                                           |Срок                    |
|-------|-----------------------------------------------------------------------------------------------------------------|------------------------|
|0.1    |ИП открыто, ОКВЭД 62.01 + 63.11                                                                                  |3–5 дней через ФНС      |
|0.2    |Расчётный счёт (Тинькофф/Сбер)                                                                                   |1–3 дня                 |
|0.3    |Регистрация в реестре операторов ПДн РКН по ст. 22 (`pd.rkn.gov.ru/operators-registry/notification/`) — бесплатно|до 30 дней проверки     |
|0.3.bis|**Отдельное** уведомление РКН по ст. 12 (трансграничная передача в Telegram)                                     |параллельно с 0.3       |
|0.4    |Договор с Yandex.Cloud LLC                                                                                       |при первом billing-event|
|0.5    |Регистрация домена `.ru` / `.app` через Reg.ru или Yandex Domains                                                |1 день                  |
|0.6    |Политика обработки ПДн (Privacy Policy) опубликована на `/privacy`                                               |1 день (взять template) |
|0.7    |Согласие на обработку ПДн как ОТДЕЛЬНЫЙ документ (ст. 9 в ред. ФЗ № 156-ФЗ)                                      |1 день                  |
|0.8    |KudaGo API access запрошен (`max@kudago.com`)                                                                    |1–2 недели ответа       |
|0.9    |Test transaction Telegram Gateway $5–10 через TON                                                                |1 день + проверка       |
|0.10   |Email ESP final choice: UniSender vs SendPulse                                                                   |2 часа                  |

**Pre-MVP compliance artefacts checklist** (готовы ДО первой production-публикации):

- [ ] Privacy Policy (`/privacy`) — шаблон + кастомизация под Act (содержит ТППД-получателей: Telegram FZ-LLC, ОАЭ; страны хранения; категории ПДн)
- [ ] Terms of Service (`/terms`) — оферта на использование сервиса
- [ ] Acceptable Use Policy (`/acceptable-use`) — правила публикации events; основа для модерации
- [ ] Cookie Policy (`/cookies`) — для cookie consent UI (Essential / Analytics / Marketing)
- [ ] **DPO**: сам ИП. Ст. 22.1 152-ФЗ не требует обязательного DPO для соло-ИП без специальных категорий ПДн.
- [ ] **Возрастное ограничение**: 16+ на UI. Ст. 9 ч. 6 152-ФЗ — до 14 лет согласие законных представителей, с 14 — самостоятельно. Простая «16+» политика выше обоих порогов; снижает T&S-риск и упрощает compliance.

### Phase 1 — Bootstrap (3–7 дней)

|#      |Группа                   |Конкретные действия                                                                                                                                                                                                                                                                                                                                                |
|-------|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|1.1    |**Yandex Cloud**         |folder структура `prod`/`dev`, IAM service-account, VPC, 1× Compute (4 vCPU + 8 GB), Managed PostgreSQL 17 (s3.micro), Object Storage bucket                                                                                                                                                                                                                       |
|1.2    |**GitHub monorepo**      |init с структурой `backend/ frontend/ infra/ docs/ .claude/`, branch protection на `main`, secrets для GHA                                                                                                                                                                                                                                                         |
|1.3    |**Local dev**            |Python 3.12 pyenv, Node 20 + pnpm, Docker Compose с локальным PG, redis-free стек                                                                                                                                                                                                                                                                                  |
|1.4    |**Django skeleton**      |`requirements/{base,dev,prod}.in` + pip-compile, settings layered (base→dev/prod), apps структура с 3 контекстами (`identity_auth`, `events`, `rsvp`), CSP middleware, django-allauth, RLS middleware                                                                                                                                                              |
|1.4.bis|**PostgreSQL extensions**|`apps/core/migrations/0001_extensions.py` создаёт `pgcrypto`, `btree_gist`, `pg_trgm`, `unaccent`, `pg_uuidv7` (см. ADR-006 → Required PostgreSQL extensions). Прогон через **прямой PG**, минуя PgBouncer (`PG_BOUNCER_HOST="" python manage.py migrate`) — `CREATE EXTENSION` и advisory locks несовместимы с transaction-pooling [F: PgBouncer features matrix].|
|1.5    |**Next.js skeleton**     |App Router structure `[locale]/(public)/(authenticated)/(organizer)/`, next-intl proxy (не middleware — Next 16), TypeScript strict                                                                                                                                                                                                                                |
|1.6    |**import-linter**        |`.importlinter` с контрактами на все 16 контекстов + запрет `.raw()` вне `apps.core.rls`                                                                                                                                                                                                                                                                           |
|1.7    |**Procrastinate**        |install + первая periodic-task (заглушка для Recurrence Engine + outbox poller)                                                                                                                                                                                                                                                                                    |
|1.8    |**Coolify**              |install на Yandex Compute, admin аккаунт создан немедленно                                                                                                                                                                                                                                                                                                         |
|1.9    |**Cost monitoring**      |Yandex Cloud Budget Alerts: 1000 / 5000 / 10000 ₽ MTD; нотификации в Telegram-bot (aiogram) + email                                                                                                                                                                                                                                                                |

### DB Migration Strategy

Zero-downtime migrations через **expand-contract pattern** [F: Adam Johnson «Boost your Django DX»]:

1. **Expand**: добавить nullable колонку / новый индекс / новый model field без NOT NULL constraints.
1. **Backfill**: Procrastinate periodic-task заполняет новую колонку из старой (батчами по 1k rows).
1. **Switch**: код приложения переключается на новую колонку (deploy code).
1. **Contract**: через 1–2 deploy-цикла удалить старую колонку.

**Pre-deploy hook в Coolify**: `PG_BOUNCER_HOST="" python manage.py migrate --noinput`. Миграции прогоняются прямым подключением к PG, минуя PgBouncer (transaction-pooling несовместим с `CREATE INDEX CONCURRENTLY` и advisory locks). См. RLS Operational Constraints #6.

**Запрещённые операции в online migration** (требуют maintenance window):

- `RENAME COLUMN` (Django backend ломается до cutover; используй add+backfill+drop).
- `DROP NOT NULL` без default (existing rows валидируются).
- `ADD COLUMN NOT NULL` без default (lock на таблицу + полная переписка).
- `ALTER COLUMN TYPE` для большой таблицы (rewrite таблицы; используй add new + backfill + drop old).
- `ADD FOREIGN KEY` без `NOT VALID` (full table scan; используй `NOT VALID` + `VALIDATE CONSTRAINT` отдельно).

### Cost Monitoring

Бюджет соло-ИП ограничен; runaway costs — экзистенциальный риск. Yandex Cloud Budget Alerts на три тира:

|Threshold                  |Action                                          |Notification                         |
|---------------------------|------------------------------------------------|-------------------------------------|
|1 000 ₽ MTD (Month-To-Date)|Informational                                   |Telegram bot — daily digest          |
|5 000 ₽ MTD                |Warning — review usage                          |Telegram + email                     |
|10 000 ₽ MTD               |Critical — kill expensive resources если runaway|Telegram + email + SMS (через SMS.ru)|

**Monthly review** через Procrastinate cron-task: 1-го числа каждого месяца агрегирует prev-month spending по Yandex services и отправляет breakdown в admin email + Telegram bot. Если spending growth > 30% MoM — alert на manual review.

**Common runaway causes** (документировать в `apps/core/CLAUDE.md`):

- Procrastinate poller с слишком частым интервалом + high error_count → infinite retries.
- Outbox event с poison message (см. ADR-016) — alert через Sentry.
- Yandex Object Storage egress на uncached OG-images.

### Спринты MVP (W1–W10)

После успешного Pilot Этапа 0 — разработка MVP web по неделям, в каждом — один модуль или один user flow:

- **W1:** Identity & Auth + User Profile + i18n bootstrap
- **W2:** Verification (phone + email + photo)
- **W3:** Events (CRUD + страница события)
- **W4:** Groups + GroupMembership
- **W5:** Series + Recurrence Engine
- **W6:** RSVP + Attendance + Notifications (email)
- **W7:** Ratings + Reputation
- **W8:** Discovery + поиск + фильтры
- **W9:** Admin Console + Moderation
- **W10:** Polish + Security review + 152-ФЗ compliance чеклист

-----

## Pilot Этап 0

> До сих пор стек выбран теоретически. Pilot Этап 0 — единственная процедура, превращающая теоретический выбор в эмпирический commit, либо отбрасывающая его. Pilot проверяет связку «соло-фаундер + Claude Code (Opus 4.7 + Sonnet 4.6) + Django 5.2 + Next.js 16» на одном end-to-end сценарии, а не на абстрактных метриках производительности.

### Pre-pilot: Compliance baseline (БЛОКЕР для Phase 1)

Соло-ИП, обрабатывающий ПДн физлиц граждан РФ через B2C event-платформу, **обязан** выполнить compliance-чек-лист **ДО** первой production-публикации сайта. С 30 мая 2025 (ФЗ № 420-ФЗ от 30.11.2024) ч. 10 ст. 13.11 КоАП РФ установила штраф для ИП **100 000–300 000 ₽** за неуведомление РКН об обработке ПДн; 50%-скидка по ст. 4.1.1 КоАП на эти составы **не действует** [F: БУХ.1С «Штрафы за персональные данные с 30 мая 2025»]. Подробное решение — в ADR-012.

Подаётся параллельно с Phase 1.1 (Yandex Cloud setup); срок РКН-регистрации — до 30 дней (ч. 4 ст. 22 152-ФЗ), поэтому начинать одновременно с инфра-setup-ом. Чек-лист (все пункты обязательны):

|#  |Действие                                                                                                                                                                                                                                                                                                                              |Срок                       |
|---|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
|0.1|Уведомление РКН по ст. 22 152-ФЗ через `pd.rkn.gov.ru/operators-registry/notification/`. Категории ПДн: ФИО, email, телефон, IP, геолокация города, фото-аватар, паспортные данные (для Pro-верификации L4). Цель: предоставление сервиса поиска компании на совместные мероприятия. Способ обработки: автоматизированный + смешанный.|До 30 дней проверки        |
|0.2|Уведомление РКН по **ст. 12** (трансграничная передача) — ОТДЕЛЬНОЕ от ст. 22; см. ADR-013. Получатель: Telegram FZ-LLC (ОАЭ), серверы NL/SG. Категории передаваемых ПДн: phone, telegram_user_id.                                                                                                                                    |Подаётся одновременно с 0.1|
|0.3|Privacy Policy опубликована на `/privacy` (ст. 18.1 152-ФЗ). Содержит явный список ТППД-получателей: Telegram FZ-LLC (ОАЭ); страны хранения; категории.                                                                                                                                                                               |1 день                     |
|0.4|Документ согласия на обработку ПДн — **отдельный** от оферты и Privacy Policy (ст. 9 в ред. ФЗ № 156-ФЗ от 24.06.2025). Отдельный чекбокс на signup. Запись в `identity_auth_consent` с purpose=‘core_processing’.                                                                                                                    |1 день                     |
|0.5|Cookie consent UI компонент с тремя уровнями (Essential / Analytics / Marketing); выбор → `identity_auth_consent` с разделёнными purposes. См. Wave 3 / W3.6.                                                                                                                                                                         |1–2 дня                    |
|0.6|**НЕ публиковать сайт production** до получения регистрации РКН по 0.1 и 0.2.                                                                                                                                                                                                                                                         |Блокер                     |

### Главный KPI (одна строка)

**Доля «принятых без существенных правок» PR от Claude Code (Accept-Rate) на завершённом core-flow ≥ 60% при общем времени реализации core-flow ≤ 7 рабочих дней при ≤ 10 import-linter violations за весь пилот.**

«Существенная правка» = ручная правка > 20 строк в выводе одной задачи, либо переписывание архитектурного решения. Accept-Rate считается по задачам (atomic feature), не по строкам.

> **`[Г]` 60% Accept-Rate — это target hypothesis, не доказанный benchmark.** Конкретного benchmark в стеке Django + Next.js + RLS нет (контекстный survey не существует на дату 2026-05-24). Доступные референсы: [F: Pragmatic Engineer Survey, Jan–Feb 2026] — 95% разработчиков используют AI еженедельно, 75% — для >половины работы; среди использующих AI agents — 71% выбирают Claude Code как primary tool. [F: JetBrains State of Django 2025] — 69% Django разработчиков используют ChatGPT, 15% — Claude. Метрика трекается в PostHog с тегом `source=claude_code`: `Accept-Rate = PR merged без manual fix / All PR closed`. Через 30 событий после Pilot — пересчитать с реальными данными, скорректировать порог.

**Обоснование порога 60%:** в публичных source-grounded данных 2026 года конкретного benchmark «Accept-Rate Claude Code на Django+Next» нет. Ближайший верифицируемый ориентир — [F: digitalapplied.com/blog/case-study-claude-code-team-adoption-30-dev-shop-2026, опубликовано 15 мая 2026]: «A thirty-engineer product organisation moved from install-only to a working Claude Code capability in a single quarter … a sustained 35% productivity lift that held into month four». На 100-dev composite — 28%. Anthropic Console трекает метрику «Suggestion accept rate». 60% — наш собственный target, не из публичных источников; он откалиброван по консервативной нижней границе [Г].

### Три exit-критерия

1. **Pilot succeeded (commit).** Core-flow работает end-to-end в проде на Coolify, Accept-Rate ≥ 60%, ≤ 10 import-linter violations за пилот, ≤ 7 рабочих дней. → переход к V1.4 на этом стеке.
1. **Pilot inconclusive (3-day extension).** Core-flow собран, но Accept-Rate в диапазоне 45–59% ИЛИ ≥ 1 риск из risk-check попал в зону «Fix». → 3-дневное продление с конкретным fix-планом (refactor CLAUDE.md, добавление 2–3 SKILL.md, явные subagents). После продления — повторный замер.
1. **Pilot failed (re-open stack).** Accept-Rate < 45% ИЛИ > 1 риск в зоне «Pivot» ИЛИ невозможно собрать core-flow за 10 дней. → переоткрытие backend (FastAPI как альтернатива Django).

### Core flow для пилота (end-to-end)

1. Anonymous пользователь приходит на лендинг.
1. Создаёт аккаунт через Telegram OIDC (приоритет 1 по V1.1).
1. Создаёт первое событие (минимум полей: название, дата/время, локация-текст, фото-обложка опционально).
1. Получает share-ссылку с серверной OG-картинкой.
1. Делится ссылкой другу.
1. Друг открывает ссылку, видит OG-превью в Telegram.
1. Друг RSVP-нится как guest (без аккаунта, по email/Telegram-handle).
1. Организатор видит RSVP в админ-панели.

### Что трекать (в `docs/pilot/day-N.md`)

- `accepted_tasks / total_tasks` — числитель Accept-Rate
- `rework_lines / generated_lines`
- `time_per_feature_min` (медиана)
- `claude_errors_log` (типы: галлюцинация импорта, N+1, RLS violation, i18n missing key)
- `import_linter_violations` за день
- `n_plus_one_detected` через django-silk

### Risk checks перед commit (10 пунктов)

Для каждого пункта декларированы Pass/Fix/Pivot criteria:

|# |Риск-чек                                              |Pass                   |Fix                                        |Pivot                                         |
|--|------------------------------------------------------|-----------------------|-------------------------------------------|----------------------------------------------|
|1 |Скорость Claude Code — реальное время на одну фичу    |≥3 фичи/день           |1–2 фичи/день, оптимизация CLAUDE.md       |<1 фича/день — backend под вопросом           |
|2 |Качество ORM-кода — N+1 в generated коде (django-silk)|0–2 N+1 за пилот       |3–5 N+1, добавить N+1 detector в pre-commit|>5 N+1 — Django ORM проблематичен             |
|3 |RLS-correctness — Claude Code понимает границы        |0 RLS violations       |1–2, эксплицитная инструкция в CLAUDE.md   |≥3 — pivot на app-level authz                 |
|4 |i18n-correctness — ICU MessageFormat                  |0 missing keys         |1–3 missing, лучшая интеграция next-intl   |>3 — переосмыслить ICU                        |
|5 |Module boundary discipline                            |≤10 violations за пилот|11–25, refactor с явными contracts         |>25 — Django module-структура слабая          |
|6 |OG-generation — Satori standalone в Next.js           |работает с дня 1       |требует custom server                      |Pivot на Cloudflare Image API                 |
|7 |Coolify deploy reliability                            |100% успешных деплоев  |1–2 фикса конфига                          |>50% fails — Selectel direct                  |
|8 |Yandex Cloud-специфика                                |без сюрпризов          |1–2 quirks с workaround                    |>2 серьёзных блокера — Selectel               |
|9 |Telegram OIDC adapter — готовый пакет                 |нашёлся в pip          |custom 100–200 строк                       |требует >500 строк — рассмотреть VK ID primary|
|10|Procrastinate vs Celery достаточность                 |работает на 3 use cases|1 use case требует Redis                   |требует Celery с дня 1 → +Redis в инфру       |

**Decision gate:** при Pivot хотя бы по одному пункту — pilot failed, переоткрытие выбора стека.

### Decision gate после пилота

Если **Go** — записать в `docs/decisions/ADR-007-stack-commit.md` (MADR 4.0):

```markdown
# ADR-007 — Stack commit (Django + Next.js)

## Status
Accepted (после Pilot Этап 0, дата YYYY-MM-DD)

## Context
Pilot завершён с Accept-Rate XX%, import-linter violations Y, RLS violations Z.
См. /docs/pilot/day-7-decision.md.

## Decision
Commit к стеку V1.2 без изменений. V1.4 пишется на нём.

## Consequences
Все будущие архитектурные решения принимают стек как given.
```

-----

## CLAUDE.md иерархия

[F: hipcamp.com/journal/engineering/scout-our-in-house-ai-agent] критическое наблюдение для соло на 100%: «AI was ignoring our internal patterns or confusing itself with older code … Claude’s output quality was unreliable, often missing important logic and considerations». Адаптация: вместо «orchestration layer для команды» — строгая 3-уровневая CLAUDE.md иерархия + 5–7 SKILL.md + 2–3 subagent definitions.

[F: anthropic.com/engineering/claude-code-best-practices, 18 апреля 2025, Boris Cherny]: «There’s no required format for CLAUDE.md files. We recommend keeping them concise and human-readable». Цель — ≤ 200 строк [F: agentfactory.panaversity.org/docs/General-Agents-Foundations/claude-code-teams-cicd/claude-md-configuration-hierarchy].

**Root `CLAUDE.md`** — см. [`../CLAUDE.md`](../CLAUDE.md) (этот репозиторий).

**Per-context `apps/<ctx>/CLAUDE.md`** — добавляется по мере роста кодбейса: что хранит, кто может читать, кто может писать, ключевые DTO в `contracts.py`, RLS-политики.

**Per-task SKILL.md** (в `.claude/skills/`) — для повторяющихся операций: «Добавить новый bounded context», «Написать RLS policy», «Создать миграцию с zero downtime», «Добавить OG-картинку для новой entity». **Текущие skills (10/10 после Iteration 6, 2026-05-27):** `write-rls-policy`, `outbox-event`, `recurrence-rrule`, `guest-rsvp-merge`, `auth-flow`, `add-translation`, `create-migration`, `add-bounded-context`, `write-adr`, `deploy-check`. Полный список с триггерами и cross-refs — `docs/AI-WORKFLOW.md` § Skills cheatsheet.

-----

## Migration paths

Ранжирование по сложности замены (от тривиального к невозможному):

1. **SMS provider** (SMS.ru → SMSC) — 1 час, поменять API-ключи и endpoint.
1. **Email ESP** (UniSender → SendPulse) — 1 день, переключить SMTP/API.
1. **CDN** (Yandex CDN → другой) — 1–2 дня, перенастроить DNS и cache invalidation.
1. **CI/CD** (GitHub Actions → Forgejo) — 2–3 дня, переписать workflow.yml.
1. **Cache/Session** (in-Postgres → Redis managed) — 3–5 дней, поменять backend и тесты.
1. **Object Storage** (Yandex → Selectel) — 1 неделя, миграция данных + переписать клиент.
1. **Background jobs** (Procrastinate → Celery+Redis) — 1–2 недели, переписать task-логику.
1. **Auth provider** (внутренний → managed) — 2–3 недели миграция user-state.
1. **Search** (PG FTS → Meilisearch) — 2–4 недели индексирования + переписи query-кода.
1. **Frontend framework** (Next.js → Remix) — 1–2 месяца, переписать UI-слой.
1. **ORM** (Django ORM → SQLAlchemy) — 2–3 месяца, переписать query-слой.
1. **Database** (Postgres → MySQL) — практически невозможно без переписки.
1. **Backend framework** (Django → Rails или другое) — 6–12 месяцев, full rewrite.

### Топ-3 сложно-заменяемых с mitigations

**1. Backend framework (Django).** Если через 6 месяцев Claude Code на Ruby/Rails окажется значительно продуктивнее — миграция = переписать MVP. **Mitigation:**

- (a) Этап 0 pilot-тест Rails на одной фиче до commitment-а;
- (b) держать business-logic в отдельных Python модулях, не в views — переписать с Django на FastAPI или другую Python-framework проще;
- (c) database schema как «контракт» — она переживёт смену backend.

**2. Database (PostgreSQL).** Сменить нельзя без full rewrite. **Mitigation:**

- (a) использовать standard Postgres-фичи, не Yandex-специфичные;
- (b) регулярные pg_dump backup-ы хранить и в Yandex Object Storage, и локально (raid-1 на disk у соло-ИП);
- (c) self-host Postgres backup-сценарий как exit-план от Yandex Cloud.

**3. ORM (Django ORM).** Сменить можно, но дорого. **Mitigation:**

- (a) держать complex queries в `models/managers.py` методах, не разбросанными по views — переписать на raw SQL или другой ORM проще;
- (b) не использовать Django-specific фичи типа `prefetch_related` через все слои — реализовать через DTOs;
- (c) RLS-логика на Postgres-уровне, не в Python — переживает смену ORM.

**Принцип:** заложить day-1 паттерны (DTOs, business logic in services not views, RLS in Postgres) — снижают migration cost в 5× если когда-то понадобится.

-----

## Risk register

|#|Риск                                                                                                                                             |Probability|Impact|Trigger для mitigation                                                           |Mitigation                                                                                                                                                                             |
|-|-------------------------------------------------------------------------------------------------------------------------------------------------|-----------|------|---------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|1|Vendor lock-in на Yandex Cloud при росте цен или политических ограничений                                                                        |M          |H     |Yandex Cloud прайс растёт >30% за квартал, или закрытие сервиса для ИП           |Backup-стратегия в Selectel: pg_dump weekly в Selectel S3 как cold-storage; Docker Compose файл inferable для re-deploy за день; Coolify-config portable                               |
|2|Performance ceiling Django ORM при росте до 100K MAU через N+1 queries и slow ORM-overhead                                                       |M          |M     |p95 latency >500ms на любом endpoint                                             |Включить django-silk для query profiling сразу; raw SQL fallback в hot paths; рассмотреть FastAPI extraction для read-heavy endpoints (Discovery feed)                                 |
|3|Hiring impossibility если позже понадобится команда — Python+Django в РФ имеет более узкий hiring pool, чем JS-стек                              |L          |M     |Решение нанять первого разработчика и неделя без подходящих кандидатов           |Не делать ничего предупредительно; при наступлении — phased rewrite разовых частей на TypeScript+NestJS, начиная с Frontend BFF                                                        |
|4|Санкционный риск GitHub Actions / Yandex Cloud / других сервисов — внезапные блокировки или удаление аккаунтов                                   |H          |H     |Один пропущенный билд в GitHub Actions или один отказ Yandex Cloud в обслуживании|Plan B на Forgejo + Selectel готов через документацию; backup git-repo еженедельно в S3 (не только GitHub); SBOM зависимостей хранить локально                                         |
|5|Burnout / wrong-choice rollback cost — выбор Django + Yandex окажется не таким productive как казалось                                           |M          |H     |Через 30 дней разработка идёт ≤50% от плана; rework rate >30%                    |Этап 0 (5–7 дней) pilot-тест на одной core-фиче с явным KPI: signup → создать event → расшарить → RSVP. Если KPI не достигнут — переоткрыть выбор без emotional sunk-cost              |
|6|РКН меняет статус ОАЭ / Нидерландов / Сингапура в перечне адекватных стран по Приказу № 128 от 05.08.2022 — Telegram-каналы становятся недоступны|L          |H     |Изменение перечня на сайте РКН или официальное письмо                            |Domestic-fallback готов (ADR-013); migration plan на чисто-SMS режим за 1 неделю; в Notifications context уже есть routing по channel-type                                             |
|7|Compliance audit РКН с штрафом по ч. 10 ст. 13.11 КоАП (100k–300k ₽ для ИП за неуведомление)                                                     |L          |H     |Жалоба пользователя или плановая проверка                                        |Compliance baseline в Pre-pilot (ADR-012) выполнен ДО первой production-публикации; уведомление по ст. 22 и ст. 12 поданы и подтверждены                                               |
|8|PostgreSQL major version migration (17 → 18 → 19) — downtime + breaking changes в extensions (`pg_uuidv7` встроен в PG 18)                       |L          |M     |Yandex объявляет EOL PG 17                                                       |Yandex Managed PG поддерживает logical replication для zero-downtime upgrade; план: read-only mode → parallel upgrade → cutover; extensions список аудит ежегодно                      |
|9|Apple Mail / iOS shifts — расширение MPP / Link Tracking Protection / новые tracking-блокировки разрушают email engagement-метрики ещё сильнее   |M          |M     |Apple анонсирует новую privacy-фичу в WWDC                                       |ADR-010 уже использует `acknowledged` (не `opened`) как ground truth; server-side click-through через short-slug 302 redirect устойчив; pivot на in-app + SMS для критичных нотификаций|

-----

## Disaster Recovery

|Параметр                          |Значение                       |Реализация                                                                                                 |
|----------------------------------|-------------------------------|-----------------------------------------------------------------------------------------------------------|
|**RPO** (Recovery Point Objective)|15 минут                       |Yandex Managed PG continuous WAL streaming + PITR backup                                                   |
|**RTO** (Recovery Time Objective) |1 час                          |Восстановление инстанса из snapshot + replay миграций (через CI/CD pipeline)                               |
|**Backup frequency**              |Daily snapshot + continuous WAL|Yandex Managed PG default; retention 14 дней                                                               |
|**Locality**                      |RU-only (ст. 18 152-ФЗ)        |Yandex Object Storage cross-zone backup в одном регионе РФ                                                 |
|**Restore drill**                 |Раз в квартал                  |Full restore в staging environment + smoke-тест core flows (signup → create event → RSVP). Проводит фаундер|
|**Off-site secondary**            |Weekly `pg_dump` в Selectel S3 |Cold storage для catastrophic Yandex failure (см. Risk #1)                                                 |

**Failure scenarios и их handling:**

|Сценарий                            |Detection                                    |Recovery                                                    |
|------------------------------------|---------------------------------------------|------------------------------------------------------------|
|PG instance failure                 |Yandex auto-failover на replica (built-in HA)|Автоматический; ~30 сек                                     |
|PG data corruption                  |Procrastinate `health_check` task fails      |PITR на точку до corruption                                 |
|Yandex region failure               |Monitoring alert через PostHog event drop    |Manual restore в Selectel из weekly snapshot (~2-4 часа RTO)|
|Code-level data loss (bad migration)|User reports / data integrity check          |PITR + replay non-broken migrations                         |

**Что НЕ покрыто DR на MVP**: real-time replica в другом регионе (HA в multi-region) — добавляется при >10K MAU.

-----

## Feature Flags

**Стек:** PostHog (self-hosted) для backend через `posthog-python` + frontend через `posthog-js`. Frozen-stack — никаких LaunchDarkly / Unleash / ConfigCat.

**Конвенция именования**: `<context>_<feature>_<variant>` (lowercase, snake_case). Примеры:

- `discovery_ranking_mode` (variants: `cold_start`, `mature`)
- `discovery_ranking_w_rep` (numeric override; см. ADR-008 per-weight flags)
- `notifications_telegram_enabled` (boolean kill-switch)
- `onboarding_skip_phone_otp` (experimental flow)

**Что должно быть feature flag:**

- Все ranking weights (ADR-008 hybrid blend — 6 параметров).
- Per-channel kill-switches в Notifications (если SMS.ru deg → выключить SMS).
- Experimental onboarding flows (A/B на progressive profile).
- Canary releases для рискованных features (например, paid events когда-то).

**Что НЕ должно быть feature flag** (антипаттерн — это **data**, не switch):

- Compliance choices (`cross_border_transfer` — это `ConsentRecord` row, не flag).
- Group publishing policies (стейтное поле `Group.publishing_policy`).
- User preferences (locale, notification channels — DB fields).
- Pricing tiers (DB schema + RLS).

**Default discipline:** flag всегда имеет hardcoded fallback в коде на случай PostHog недоступен. Не делать «PostHog → default behavior unknown» — это runtime crash вместо graceful degradation.

```python
# apps/discovery/services.py
from apps.feature_flags.contracts import get_flag_value

def get_ranking_weights(city: City) -> RankingWeights:
    mode = get_flag_value(
        flag='discovery_ranking_mode',
        user_id=None,  # city-level flag
        default='cold_start',  # ← обязателен fallback
    )
    return COLD_START_WEIGHTS if mode == 'cold_start' else MATURE_WEIGHTS
```

-----

## ADR (Architecture Decision Records)

Декомпозированный список ключевых решений в формате MADR 4.0. Каждое решение зафиксировано отдельным пунктом ниже; при необходимости — выделить в отдельные файлы под `docs/decisions/`.

### ADR-001 — Modular monolith из 16 bounded contexts

- **Status:** Accepted (V1.0).
- **Context:** соло-фаундер на AI-коде; нужна архитектура, которая держит границы при AI-генерации и не требует distributed debugging.
- **Decision:** modular monolith с 16 bounded contexts; cross-context calls — только через `apps.<ctx>.contracts`; enforcement через `import-linter`.
- **Alternatives considered:** микросервисы (отвергнуто: операционный налог без выгоды для соло); большой монолит без границ (отвергнуто: 6 месяцев AI-генерации размывает domain model).
- **Consequences:** один деплой, одна БД, читаемые stack traces; необходимость дисциплины с границами; модуль можно экстрагировать в сервис при необходимости.

### ADR-002 — Backend: Django 5.2 LTS + Python 3.12

- **Status:** Accepted (V1.2), pending Pilot Этап 0.
- **Context:** Claude Code productivity по SWE-bench Verified выше на Python/Ruby; нужен proof-of-scale в нашем домене.
- **Decision:** Django 5.2 LTS + Python 3.12 + Django ORM. import-linter для границ.
- **Alternatives considered:** Rails 8 + Packwerk (равнозначен; будет проверен в пилоте на одной фиче); NestJS (TS медленнее JS из-за типов); Phoenix/Elixir (узкое сообщество); Spring Modulith (избыточно).
- **Consequences:** мы привязаны к Python-экосистеме; Django admin доступен; миграция на другой Python-framework (FastAPI) возможна с сохранением schema.

### ADR-003 — Frontend: Next.js 16 App Router + next-intl

- **Status:** Accepted (V1.2).
- **Context:** OG-cards в V1.1 требуют SSR/streaming; нужен i18n routing с дня 1.
- **Decision:** Next.js 16 App Router + next-intl + TypeScript строгий на API-границах через zod, либеральный внутри компонентов.
- **Alternatives considered:** Remix/RR v7 (равнозначен по SSR, меньше adoption); SvelteKit (меньше Claude Code training data); Astro (динамика RSVP требует SSR); SolidStart / TanStack Start (ранняя стадия).
- **Consequences:** self-host через `standalone build` на Yandex Cloud Compute (Vercel не подходит под 152-ФЗ ст. 18).
- **Триггеры пересмотра:** (a) Next.js 16+ становится EOL без 5-летнего LTS path; (b) Server Components patterns ломаются в major upgrade и breaking changes > 2 раз/год; (c) bundle size grows > 2× на equal feature set → пересмотреть на Remix/RR v7 или Astro.

### ADR-004 — Hosting: Yandex Cloud + Coolify

- **Status:** Accepted (V1.2).
- **Context:** соло-ИП РФ; 152-ФЗ ст. 18 требует первичной обработки ПДн в РФ; Cloudflare/AWS edges нестабильны.
- **Decision:** Yandex Cloud Compute (4 vCPU + 8 GB) + Coolify как PaaS-overlay + Managed Postgres 17 + Yandex Object Storage + Yandex CDN.
- **Alternatives considered:** VK Cloud (меньше документации [?]); Selectel (хороший fallback, менее интегрированный экосистема); Timeweb/Cloud.ru/Beget (меньше managed-сервисов).
- **Consequences:** vendor lock-in на Yandex; mitigation — Docker Compose файл inferable для re-deploy в Selectel за день.

### ADR-005 — Отвергнут зарубежный managed-стек (Stripe / Clerk / Convex / Vercel managed)

- **Status:** Accepted (V1.2).
- **Context:** Stripe в РФ не оперирует с 2022; Clerk billing использует Stripe; Convex Pro — также Stripe-based; Vercel hosting не соответствует 152-ФЗ ст. 18.
- **Decision:** **No Stripe, no Clerk billing, no Convex Pro, no Vercel managed.** Использовать ЮKassa для платежей; self-host auth через `django-allauth` + `django-otp` + custom Telegram OIDC adapter + `django-otp-webauthn`.
- **Alternatives considered:** Turborepo + Next.js + Expo + Convex + Clerk (отвергнуто по трём причинам: Stripe billing, Convex DSL несовместим с modular monolith, 152-ФЗ ст. 18).
- **Consequences:** больше кода на self-host auth (~100 строк custom Telegram OIDC adapter); полный контроль над user-data, что критично для compliance.

### ADR-006 — PostgreSQL как single source of truth

- **Status:** Accepted (V1.2).
- **Context:** соло-ИП не может управлять 8 managed-сервисами параллельно; каждый компонент = +20–60 мин/нед ops.
- **Decision:** в PostgreSQL хранятся: основные данные, cache (`django.core.cache.backends.db.DatabaseCache`), sessions (`django.contrib.sessions.backends.db`), background jobs (Procrastinate), rate limiter, search (FTS + tsvector + GIN).
- **Alternatives considered:** Redis для cache/session/queues с дня 1 (отвергнуто: +1 managed компонент); Meilisearch с дня 1 (отвергнуто: преждевременно до 50K events); Celery+Redis (отвергнуто: преждевременно до 1000 jobs/мин).
- **Consequences:** меньше moving parts; миграция на Redis/Meilisearch — простая, когда понадобится (триггер: >30% Postgres CPU на cache; >500ms p95 на discovery feed).

#### Required PostgreSQL extensions

`gen_random_uuid()` в PG ≥ 13 — это core-функция ядра [F: PostgreSQL 17 docs F.26 pgcrypto; pgPedia gen_random_uuid()], но `pgcrypto` всё равно требуется для encryption (см. ADR-014). Полный список:

|Extension   |Использование                                                                                                                                                                             |
|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`pgcrypto`  |`pgp_sym_encrypt`/`pgp_sym_decrypt` для ENCRYPT_AT_REST полей; backup для `gen_random_uuid`                                                                                               |
|`btree_gist`|Composite GIST индексы для exclusion constraints (overlap-проверка Recurrence-инстансов)                                                                                                  |
|`pg_trgm`   |Fuzzy search в discovery для misspellings; backup к FTS                                                                                                                                   |
|`unaccent`  |Поиск без учёта диакритики (импортируемые данные с акцентами)                                                                                                                             |
|`pg_uuidv7` |`uuidv7()` для PK write-heavy таблиц (см. [UUID Strategy](#uuid-strategy-применимо-ко-всем-pk-и-токенам)). Только если Yandex Managed PG 17; в PG 18 — встроенный `uuidv7()` без extension|

**Бутстрап-миграция** `apps/core/migrations/0001_extensions.py`:

```python
from django.db import migrations

class Migration(migrations.Migration):
    initial = True
    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS pgcrypto; "
                "CREATE EXTENSION IF NOT EXISTS btree_gist; "
                "CREATE EXTENSION IF NOT EXISTS pg_trgm; "
                "CREATE EXTENSION IF NOT EXISTS unaccent; "
                # pg_uuidv7 — только если PG < 18 (в PG 18+ uuidv7() в ядре).
                # CREATE EXTENSION IF NOT EXISTS — идемпотентен; на PG 18
                # extension может отсутствовать в allowlist — установка
                # пропускается без ошибки если есть условие.
                "CREATE EXTENSION IF NOT EXISTS pg_uuidv7;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
```

**[?] Caveat:** статус доступности `pg_uuidv7` и набора extensions в Yandex Managed PostgreSQL allowlist — необходимо подтвердить в Phase 0 через `SELECT * FROM pg_available_extensions;`. Если Yandex добавит ограничения — fallback на Selectel Managed или self-host PG (см. Risk register).

### ADR-007 — Stack commit (pending Pilot Этап 0)

- **Status:** Proposed.
- **Context:** все вышеперечисленные решения теоретические; нужен эмпирический commit.
- **Decision:** будет принят после Pilot Этап 0 (см. [`#pilot-этап-0`](#pilot-этап-0)).
- **Consequences:** см. exit-критерии пилота.

> **Historical note.** В PDF V1.3 секция 17.5 этот ADR был зафиксирован как ADR-005 (stack commit decision). После Wave 1 renumbering: ADR-005 = «Отвергнут зарубежный managed-стек (Stripe / Clerk / Convex / Vercel managed)», stack commit перенесён на ADR-007. Внешние ссылки на «ADR-005» в исторических промтах / PDF — устаревшие. См. полный renumbering note в `docs/CHANGELOG.md`.

### ADR-008 — Discovery ranking formula (cold-start + mature weights)

- **Status:** Accepted (2026-05-24).

**Context.** V1.0 раздел 5.5 фиксирует ранжирование Discovery как «reputation × activity × recency × proximity» (умножение), V1.1 раздел 5.4 даёт cold-start сигналы (recency, verified, category-fit, city-fit, filling, time-of-day). Конкретных весов в источниках нет. Умножение даёт «всё или ничего» поведение: нулевая `activity` (новое событие без RSVP) обнуляет весь score, что катастрофично для cold-start фазы Phase 5 soft launch.

**Decision.** Используется **взвешенная сумма** (не умножение). Зафиксированы **два набора весов** в одном `apps/discovery/config.py`, переключаемые через PostHog feature flag `discovery_ranking_mode ∈ {'cold_start', 'mature'}`:

```python
# apps/discovery/config.py

@dataclass(frozen=True)
class RankingWeights:
    w_rep: Decimal
    w_act: Decimal
    w_rec: Decimal
    w_prox: Decimal
    verified_boost: Decimal       # additive, после взвешенной суммы
    filling_boost: Decimal        # additive, при ≥60% capacity

COLD_START_WEIGHTS = RankingWeights(
    w_rep=Decimal('0.15'), w_act=Decimal('0.05'),
    w_rec=Decimal('0.45'), w_prox=Decimal('0.35'),
    verified_boost=Decimal('0.10'),
    filling_boost=Decimal('0.05'),
)

MATURE_WEIGHTS = RankingWeights(
    w_rep=Decimal('0.40'), w_act=Decimal('0.20'),
    w_rec=Decimal('0.25'), w_prox=Decimal('0.15'),
    verified_boost=Decimal('0.05'),
    filling_boost=Decimal('0.05'),
)
```

Финальная формула:

```
score = w_rep × reputation_score
      + w_act × activity_score
      + w_rec × recency_score
      + w_prox × proximity_score
      + (verified_boost if organizer.verification_level >= L2 else 0)
      + (filling_boost  if event.capacity_fill_ratio >= 0.6 else 0)
```

Все компоненты нормализованы в [0, 1]. `recency_score` — **экспоненциальный decay с half-life 14 дней**: `recency_score = 2 ** (−Δdays / 14)`, где `Δdays = (event.starts_at − now).days`, clip [0, 1]. Для прошедших событий — 0.

**Триггер переключения** `cold_start` → `mature`: в целевом городе достигнуто ≥100 событий с completed two-sided rating И прошло ≥4 календарных недели с момента запуска города. До этого порога — `cold_start`.

**Hybrid blend transition (вместо stepwise switch).** Резкое переключение на пороге 100 событий даст «прыжок» в выдаче — events, которые были на топе по cold_start, могут провалиться. Решение — **linear blend по числу rated events** в зоне 30–100:

```python
def get_weights_for_city(rated_event_count: int) -> RankingWeights:
    if rated_event_count <= 30:
        return COLD_START_WEIGHTS
    if rated_event_count >= 100:
        return MATURE_WEIGHTS
    # Blend zone 30-100:
    t = (rated_event_count - 30) / (100 - 30)  # 0.0 → 1.0
    return RankingWeights(
        w_rep=lerp(COLD_START_WEIGHTS.w_rep, MATURE_WEIGHTS.w_rep, t),
        w_act=lerp(COLD_START_WEIGHTS.w_act, MATURE_WEIGHTS.w_act, t),
        w_rec=lerp(COLD_START_WEIGHTS.w_rec, MATURE_WEIGHTS.w_rec, t),
        w_prox=lerp(COLD_START_WEIGHTS.w_prox, MATURE_WEIGHTS.w_prox, t),
        verified_boost=lerp(COLD_START_WEIGHTS.verified_boost, MATURE_WEIGHTS.verified_boost, t),
        filling_boost=lerp(COLD_START_WEIGHTS.filling_boost, MATURE_WEIGHTS.filling_boost, t),
    )
```

**Per-weight feature flags.** Каждый из шести параметров (`w_rep`, `w_act`, `w_rec`, `w_prox`, `verified_boost`, `filling_boost`) экспонируется через PostHog feature flag `discovery_ranking_<weight_name>` — позволяет A/B-тестировать индивидуальные веса без deploy. Default flag = текущее значение из `RankingWeights`. Конвенция именования согласована в [Feature Flags section](#feature-flags) (создаётся в Wave 3).

**Recency half-life — `[Г]` гипотеза.** 14 дней выбраны из соображения, что большинство events планируется за 1–4 недели до даты. Это **необоснованная эмпирически** константа — пересмотр после Pilot (≥30 событий с completed RSVP + check-in). Альтернативы для ревизии:

- **Sigmoid decay:** `1 / (1 + exp(k × (days − midpoint)))` — менее агрессивный на близкие даты, smooth transition.
- **Two-piece linear:** до event_date — boost (нелинейный); после — drop. Лучше отражает «горящий» эффект.
- **Per-category half-life:** consultation (longer planning) → 21 день; spontaneous walk → 3 дня. Требует categorical data.

Метрика для ревизии: `CTR(event, days_to_event)` distribution — если сильно skewed к одной части кривой → пересмотреть формулу.

**Alternatives considered:**

- **Multiplicative formula из V1.0 (`rep × act × rec × prox`).** Каноничная форма из источников. Отвергнута: для cold-start обнуляет любое новое событие до первого RSVP.
- **ML learning-to-rank с дня 1 (например, через `xgboost` на ratings/clicks).** Дала бы лучшую relevance long-term. Отвергнута: требует labeled data, которой нет на старте; противоречит deferred-списку «ML personalization до >10K MAU».
- **Простая сортировка by recency.** Дешевле всех. Отвергнута: не использует verified и proximity сигналы, что необходимо для T&S и localization.
- **Stepwise switch вместо hybrid blend.** Отвергнут: «прыжок» в выдаче ломает UX trust для returning users.

**Consequences:**

- Положительные: cold-start фаза получает осмысленное ранжирование без data dependency; A/B-тестирование весов через PostHog без миграций; hybrid blend сглаживает transition между фазами; миграция на ML — заменой одной функции `score_event_for_user`.
- Отрицательные: подбор весов вручную — risk of suboptimal ranking; PostHog flag = единая точка отказа для discovery (mitigation: hardcoded fallback в коде); 14d half-life — необоснованная гипотеза.
- **Триггеры пересмотра:**
  - p50 click-through rate из discovery feed падает ниже 8% на `cold_start` весах в течение 2 недель → перевзвесить.
  - `filling_boost` ведёт к спаму (организаторы искусственно завышают capacity_fill_ratio) → убрать или защитить anti-gaming.
  - 10K MAU и ≥5K event-rating pairs в БД → переоткрыть для ML ranking как отдельный ADR.
  - CTR distribution by `days_to_event` сильно skewed → пересмотреть recency formula (sigmoid / two-piece).

### ADR-009 — Group publishing rules

- **Status:** Accepted (2026-05-24).

**Context.** V1.0 раздел 2.3 описывает роли (owner, member, organizer как любой Participant, опубликовавший встречу); раздел 5.2 контекста Groups включает `GroupRule`. Конкретного правила «кто публикует события от имени группы» нет. Tradeoff: слишком открыто = scam-риск (member публикует фейковую тренировку от имени trusted-группы); слишком закрыто = убивает organic growth в JTBD-4 (хобби-группы, где члены активны и публикуют сами). JTBD-2 (тренерские группы) и JTBD-4 (хобби) имеют разные UX-ожидания — фиксированное правило для всех групп не подходит.

**Decision.** На таблице `groups_group` вводится поле `publishing_policy VARCHAR(32) NOT NULL DEFAULT 'owner_only'`, enum из трёх значений:

```python
class GroupPublishingPolicy(str, Enum):
    OWNER_ONLY = 'owner_only'
    MEMBERS_MODERATED = 'members_moderated'
    MEMBERS_OPEN = 'members_open'
```

Семантика:

- **`owner_only`** (DEFAULT для всех новых групп). Только owner создаёт Event с `group_id=this.id`. Подходит для JTBD-2 (тренер ведёт группу, members — клиенты).
- **`members_moderated`.** Любой member submits Event → создаётся `Event(status='pending_moderation', group_id=this.id)`. Owner approves или rejects в admin-флоу за 48 часов; при отсутствии решения — auto-`cancelled`. Все pending события невидимы в Discovery.
- **`members_open`.** Любой member публикует Event напрямую (`status='published'`). Owner должен явно включить эту policy с T&S-предупреждением UI «Поведение участников — твоя ответственность». Откатывается obi одним кликом.

**Авторизационная проверка** в `apps.events.services.create_event`:

```python
def create_event(*, organizer_user_id: UUID, group_id: UUID | None, ...) -> EventDTO:
    if group_id is not None:
        group = groups.get_group(group_id=group_id)
        membership = groups.get_membership(group_id=group_id, user_id=organizer_user_id)
        policy = group.publishing_policy
        if policy == 'owner_only' and membership.role != 'owner':
            raise PermissionDenied(...)
        if policy == 'members_moderated' and membership.role == 'member':
            status = 'pending_moderation'
        # else: owner или members_open → status='published'
```

Owner может менять `publishing_policy` в любой момент через `apps.groups.services.set_publishing_policy(group_id, policy, actor_user_id)`. Изменение логируется в AuditLog.

**Alternatives considered:**

- **Фиксированное `owner_only` без per-group field.** Проще, нет сложного авторизационного слоя. Отвергнуто: убивает JTBD-4 (хобби-группы — настолки, бук-клубы), где members хотят сами публиковать.
- **`any_member` фиксированное.** Максимальный organic growth. Отвергнуто: T&S-риск для тренерских групп критичен; scam-сценарий «фейковая тренировка от имени trusted-тренера» становится реален.
- **`GroupRule`-таблица с произвольной DSL.** Гибко на бумаге. Отвергнуто: over-engineering для соло-команды; добавляет concept-нагрузку для пользователей; первые 6 месяцев трёх preset-полиции хватит с запасом.

**Consequences:**

- Положительные: JTBD-2 и JTBD-4 обслужены разными policies без концептуальной сложности; default `owner_only` безопасен; `members_moderated` даёт безопасный middle ground.
- Отрицательные: moderation-burden для `members_moderated` групп (48-часовое окно требует регулярного check-in owner-а); фаундер на ранних этапах должен включать в admin-консоль queue по pending events групп.
- **Триггеры пересмотра:**
  - Conversion pending → published в `members_moderated` падает ниже 70% (т.е. >30% событий отменяются по timeout) → расширить окно или упростить approval-flow.
  - T&S-incident rate в `members_open` группах превышает 2× rate в `owner_only` → откатить default `members_open` (запретить выбор без manual override фаундером).
  - 100 групп используют `members_moderated` → автоматизировать approval через trust-score.

### ADR-010 — NotificationDelivery state machine

- **Status:** Accepted (2026-05-24).

**Context.** V1.1 раздел 5.6 фиксирует каналы (Email / Web Push / In-app / SMS / Telegram Bot) и приоритеты, но не state machine доставки. V1.1 раздел 4.5 явно фиксирует: Apple Mail Privacy Protection даёт ~100% open rate независимо от реального открытия (open-tracking сломан); iOS 18 Mail/Safari вырезают UTM. Это значит, что **`opened` не может быть ground truth для NSM** (Confirmed Weekly Attendances). Нужна state machine, унифицированная между каналами, но допускающая channel-specific нюансы (email bounce ≠ push not_subscribed ≠ SMS undeliverable).

**Decision.** Единая state machine с core states и channel-specific extensions в JSONB. Ground truth для NSM — `acknowledged` (явное действие пользователя), не `opened`.

**Core states** (линейный flow с двумя терминальными ветками):

```
pending → queued → sent → delivered → [acknowledged | expired]
                                  ↓
                                  [failed | bounced | suppressed]  (terminal)
```

|Состояние     |Значение                                                                                                                                                                                                                                                                       |
|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|`pending`     |Запись создана, ожидает scheduling                                                                                                                                                                                                                                             |
|`queued`      |Передано в Procrastinate, в очереди                                                                                                                                                                                                                                            |
|`sent`        |Отдано провайдеру (UniSender API 2xx, Telegram API ok, push-сервер принял payload)                                                                                                                                                                                             |
|`delivered`   |Провайдер подтвердил доставку (где поддерживается: SMTP 2xx + DMARC report; Telegram returned message_id; push receipt; SMS DLR)                                                                                                                                               |
|`acknowledged`|**Ground truth для NSM.** Пользователь явно отреагировал: click-through по короткому slug; return to app в течение 15 минут после delivered; RSVP submission с привязкой к notification_id; пометка in-app notification как read; callback_query на inline button Telegram-бота|
|`expired`     |Не acknowledged в течение retention-окна (default 30 дней)                                                                                                                                                                                                                     |
|`failed`      |Generic terminal failure: network error, provider 5xx, retry budget exhausted                                                                                                                                                                                                  |
|`bounced`     |**Hard bounce** (email/SMS): permanent failure — invalid address, mailbox unavailable, blocked. Адресат автоматически попадает в suppression list для канала. См. `bounce_classification` ниже                                                                                 |
|`suppressed`  |Адресат уже в suppression list для канала — нотификация НЕ отправлена; запись для audit и unsubscribe attribution                                                                                                                                                              |

**Channel-specific extensions** в столбце `delivery_metadata JSONB`:

- `email`: `{bounce_type, bounce_classification, suppressed_at, complained_at, smtp_response_code}` — может содержать PII (адрес отправки в bounce-сообщении) → **ENCRYPT_AT_REST** (см. ADR-014). `bounce_classification` ∈ `{InvalidAddress, MailboxUnavailable, Technical, Reputation}` [F: twilio.com/docs/sendgrid/for-developers/tracking-events/event].
- `web_push`: `{subscription_active, error_code}`.
- `in_app`: `{read_at}`.
- `sms`: `{dlr_status, network_error}`.
- `telegram_bot`: `{message_id, chat_blocked, button_callback_data}`.

**Apple MPP-явное правило:** на email-канале НЕ записываем `acknowledged` по pixel-open. Сигналы для `acknowledged` на email — ТОЛЬКО (a) click-through по tracked link через short-slug 302 redirect + (b) RSVP submission с notification_id в attribution-цепочке (server-side через короткий slug, не UTM — iOS 18 их режет).

**NSM формула per channel:**

```
acknowledged_rate(channel) = COUNT(state = 'acknowledged' WHERE channel = X)
                           / COUNT(state ∈ {'acknowledged', 'expired', 'failed', 'bounced'} WHERE channel = X)
```

Числитель — только `acknowledged`; знаменатель — все terminal states (исключая `suppressed`, т.к. это не «доставленные» нотификации). Альтернативная формула `acknowledged / delivered` искажается Apple MPP — pixel-tracking даёт ложно-100% `delivered` на email клиентах iCloud (~45.51% всех email opens по Litmus Email Analytics, февраль 2026). `opened_raw` сохраняется в `delivery_metadata` справочно для debugging — **но не используется** в продуктовых метриках.

**Storage:** таблица `notifications_delivery (id, user_id, notification_type, channel, state, delivery_metadata jsonb, created_at, sent_at, delivered_at, acknowledged_at, expired_at, failed_at, bounced_at, suppressed_at)`. RLS: только owner. Подробная схема — в Level C Notifications post-Pilot (текущий Level C status: **missing**, добавится в Iteration 9; см. `docs/iterations/iteration-5.5-roadmap.md` step 24).

**Suppression list:** отдельная таблица `notifications_suppression (channel, address_hash, suppressed_at, reason, source_delivery_id)`. Перед отправкой — service-layer проверка hash(address) в suppression. При hard bounce — автоматическая запись в suppression.

**Alternatives considered:**

- **Pixel-tracking `opened` per email.** Industry-standard «open rate» метрика. Отвергнуто: Apple MPP делает её бесполезной для ≥30% пользователей (RU iCloud users — критичная аудитория); ложно высокая метрика будет вводить в заблуждение продуктовые решения.
- **Бинарное `delivered/failed` без `acknowledged`.** Проще state machine. Отвергнуто: теряем способность отличить «провайдер доставил, пользователь не открыл» от «провайдер доставил, пользователь среагировал» — это разные продуктовые сигналы (engagement vs deliverability).
- **Per-channel независимые state machines.** Дала бы более точное моделирование. Отвергнуто: сложность хранилища и UX в admin-консоли; общие core states + JSONB extensions покрывают 95% реальных кейсов.
- **Без `bounced` и `suppressed` (всё в `failed`).** Отвергнуто: blacklist домена через дни без suppression handling; необходимо отдельно от network failures для retry logic и domain reputation.

**Consequences:**

- Положительные: единая семантика «доставлено и сработало» через все каналы; NSM не искажается Apple MPP; channel-specific нюансы доступны для debugging без миграций схемы (JSONB); suppression handling защищает domain reputation.
- Отрицательные: `acknowledged` собирается через 5 разных механизмов (click, in-app return, RSVP attribution, callback_query, read mark) — повышает риск bugs в acknowledgment-логике.
- **Триггеры пересмотра:**
  - `acknowledged_rate` на критичные T-24h reminder-нотификации падает ниже 25% в течение 2 недель → revisit channel-mix или timing.
  - Добавляется новый канал (RCS, WhatsApp Business для EN-сегмента) → extend `delivery_metadata` schema + при необходимости core states.
  - `bounced_rate` на email > 5% → пересмотреть email warmup и SPF/DKIM/DMARC.
  - Возникает потребность в “delivered but unread” сегментации (например, для re-engagement campaigns) → добавить промежуточное состояние `read` (in-app and email click without RSVP).

### ADR-011 — Admin Console scope (hybrid: Django admin + custom Next.js views)

- **Status:** Accepted (2026-05-24).

**Context.** V1.0 раздел 5.2 фиксирует Admin Console как 16-й bounded context: «внутренний инструмент для соло-фаундера: модерация, ручная верификация, статус системы, метрики». Конкретной реализации в источниках нет. Tradeoffs: фаундер один, ему нужен time-to-market; Django admin даётся бесплатно из коробки, но UX устарел и плохо подходит для high-frequency workflows (moderation queue без сортировки/фильтров/bulk action съест часы в неделю); отдельный Next.js дашборд даёт лучший UX, но требует отдельной работы. 152-ФЗ: все операции с PII (просмотр ID-документов, ручная верификация) логируются в AuditLog независимо от UI.

**Decision.** **Гибрид:**

1. **Django admin** на `/admin/` (Django default route) как baseline для CRUD-операций над всеми 16 контекстами. Автогенерация через `ModelAdmin` для всех моделей; кастомизация `list_display`, `list_filter`, `search_fields`. Доступ только staff_required + IP allowlist + MFA.
1. **Кастомные Next.js views** в группе роутов `[locale]/(admin)/...` Next.js приложения для 3 high-frequency workflows:
- `/admin/moderation/` — очередь `ReportedContent` + `Event(status='pending_moderation')` с bulk-actions и keyboard shortcuts.
- `/admin/verification/` — ручной review L3 (photo) и L4 (ID) verification: side-by-side viewer документов с decision-кнопками.
- `/admin/metrics/` — NSM dashboard (Confirmed Weekly Attendances + supporting metrics), embedded PostHog dashboards.
1. **Session sharing.** Next.js admin views вызывают Django backend API с тем же session cookie; backend применяет staff_required check. Никакого отдельного admin-auth — переиспользуется django-allauth session.
1. **AuditLog обязательно.** Все mutations через admin (любой UI) записывают `AuditLog(actor_user_id, action, target_type, target_id, ip_hash, timestamp)`. PII-просмотры (документы верификации) тоже логируются как `action='pii_view'`.

**Alternatives considered:**

- **Django admin only (без custom Next.js views).** Минимум работы; всё на месте с дня 1. Отвергнуто: модерационная очередь без удобной сортировки/фильтров/bulk-action превратится в bottleneck — фаундер будет тратить часы в неделю на действия, которые в custom-UI занимают минуты.
- **Next.js dashboard only (без Django admin).** Лучший UX по всем экранам. Отвергнуто: построение CRUD-интерфейсов для ~30 моделей вручную — недели работы; диминишные returns для редко используемых таблиц (Locale, Category — open by month).
- **Third-party self-host admin (Retool, AppSmith).** Снижает время разработки custom views. Отвергнуто: добавляет дополнительный managed/self-host компонент против духа ADR-006 (PostgreSQL single source); ещё одна точка авторизации; ещё один runtime.

**Consequences:**

- Положительные: Django admin покрывает 80% rare-use админ-задач бесплатно; custom Next.js views ускоряют 3 high-frequency workflows; единый design-language с публичной частью; session reuse упрощает auth.
- Отрицательные: техдолг — два UI-стиля (Django admin старый, Next.js views современный); фаундер должен поддерживать оба; AuditLog должен покрывать оба входа единообразно (легко забыть один из путей).
- **Триггеры пересмотра:**
  - Подключается второй модератор → пересмотреть UX (особенно visibility «кто что делал» + per-user-rate limiting в moderation queue).
  - Daily admin time превышает 2 часа на стабильно поддерживаемых workflows → выделить ещё один custom view (например, для analytics drill-down).
  - Кастомных Next.js views становится больше 7 → рассмотреть полный переход на Next.js admin с отказом от Django admin (full SPA migration).

### ADR-012 — Compliance Baseline (РКН + согласие + локализация)

- **Status:** Accepted (2026-05-24).

**Context.** Соло-ИП, обрабатывающий ПДн физлиц граждан РФ через B2C event-платформу, обязан выполнить три compliance-требования **ДО** первой строки production-кода: (1) уведомление РКН по ст. 22 152-ФЗ, (2) Privacy Policy по ст. 18.1, (3) отдельный документ согласия по ст. 9 в ред. ФЗ № 156-ФЗ от 24.06.2025. Невыполнение (1) с 30.05.2025 (ФЗ № 420-ФЗ от 30.11.2024, ч. 10 ст. 13.11 КоАП) — штраф **100 000–300 000 ₽** для ИП без 50%-скидки [F: БУХ.1С «Штрафы за персональные данные с 30 мая 2025»; msp03.ru].

Закрытый перечень исключений ч. 2 ст. 22 152-ФЗ (ГИС безопасности; обработка без средств автоматизации; транспортная безопасность) **не покрывает** B2C event-платформу — наш сервис попадает под общий режим уведомления [F: ст. 22 152-ФЗ; pravovest-audit.ru «Ответственность за неподачу уведомления в Роскомнадзор»].

**Decision.** Compliance baseline — это часть Phase 0 (Pre-pilot) и **блокер** для Phase 1 production-публикации. Чек-лист:

1. Уведомление РКН по ст. 22 — подано через `pd.rkn.gov.ru/operators-registry/notification/`, регистрация в реестре операторов получена.
1. Уведомление РКН по **ст. 12** (трансграничная передача) — подано отдельно (см. ADR-013).
1. Privacy Policy опубликована на `/privacy` (ст. 18.1 152-ФЗ); содержит ТППД-получателей.
1. Cookie consent UI с тремя уровнями (Essential / Analytics / Marketing) реализован; выбор записывается в `identity_auth_consent` с разделёнными purposes (см. Wave 3 / W3.6).
1. Signup form: отдельный чекбокс «Согласен на обработку ПДн» (НЕ объединённый с принятием оферты), запись в `identity_auth_consent` с `purpose='core_processing'`.
1. **Сайт production НЕ публикуется** до получения регистрации РКН по пунктам 1 и 2.

**Alternatives considered:**

- **Отложить compliance до post-MVP.** Отвергнуто: штраф 100 000+ ₽ + потенциальная блокировка домена РКН + риск утечки до уведомления = катастрофические последствия для соло-ИП.
- **Не подавать уведомление, ссылаясь на ч. 2 ст. 22.** Отвергнуто: закрытый перечень исключений не содержит B2C-платформы; судебная практика по ч. 10 ст. 13.11 КоАП формируется не в пользу попыток обойти.
- **Подать только уведомление по ст. 22, без ст. 12.** Отвергнуто: ст. 12 — это отдельная обязанность с собственным составом нарушения; уведомление по ст. 22 не покрывает ТППД.

**Consequences:**

- Положительные: легальное основание для запуска; снижение риска штрафов и блокировок; consent records — готовый artifact для запросов субъектов по ст. 14 (право на удаление).
- Отрицательные: 1–4 недели до запуска (срок РКН-регистрации до 30 дней по ч. 4 ст. 22); ежегодный audit на актуальность реестра.
- **Триггеры пересмотра:** изменение состава категорий ПДн (новый verification flow, новые контакт-каналы, новый ТППД-получатель) → подать уточнение в РКН в течение 10 рабочих дней (ч. 7 ст. 22 152-ФЗ); расширение действия 152-ФЗ с марта 2028 [F: sec.ussc.ru] → новый review до этой даты.

### ADR-013 — Notification channel fallback для non-consented users

- **Status:** Accepted (2026-05-24).

**Context.** Использование Telegram Gateway / aiogram + bot API влечёт трансграничную передачу ПДн в Telegram FZ-LLC (ОАЭ; серверы NL/SG) [F: ст. 12 152-ФЗ; ГАРАНТ.РУ «Telegram-канал и ПДн»; CISOCLUB «Хранение ПДн за границей 2025»]. Передача `phone` (через Telegram Gateway OTP) и `telegram_user_id` Telegram-у — это ТППД по п. 11 ст. 3 152-ФЗ. Ст. 12 в редакции ФЗ № 266-ФЗ от 14.07.2022 (действует с 01.03.2023) требует **отдельного** от ст. 22 уведомления РКН до начала ТППД.

Часть пользователей может не дать согласие на ТППД — но мы обязаны предоставить им сервис (ст. 6 152-ФЗ: отказ в обслуживании при отказе от ТППД допустим только если без ТППД сервис невозможен). Наш сервис **возможен без Telegram**: есть SMS.ru, email через UniSender (RU), Web Push, in-app — все domestic-каналы. Поэтому делаем choice architecture.

**Decision.** Все notification-каналы делятся на два уровня по compliance:

- **Domestic-only (не требует ст. 12 consent):** SMS.ru OTP, email через UniSender (RU), Web Push, in-app notifications.
- **Cross-border (требует отдельного consent по ст. 12):** Telegram Bot (aiogram), Telegram Gateway OTP.

На signup пользователь видит:

```
[x] Phone OTP через SMS (РФ) — default checked, обязательно
[ ] Phone OTP через Telegram Gateway — optional, отдельное согласие на ТППД
[ ] Получать напоминания через Telegram Bot — optional, ТППД
```

Если ни одна из ТППД-опций не выбрана — пользователь использует только domestic-каналы. Notifications context при выборе канала проверяет `ConsentRecord(purpose='cross_border_transfer', granted=true)` ДО любого вызова Telegram API.

**Alternatives considered:**

- **Только Telegram-каналы.** Отвергнуто: обязательная ТППД для всех противоречит ст. 6 (минимизация ТППД) и блокирует пользователей, не желающих делиться данными с зарубежными сервисами; нарушение ст. 12.
- **Только domestic-каналы (без Telegram).** Отвергнуто: Telegram — основная mobile-distribution стратегия по ADR-005 и V1.1 (Telegram Mini App + Bot для notifications); полный отказ блокирует половину user journey.
- **Дефолтная opt-in галочка на Telegram.** Отвергнуто: dark pattern, не соответствует «явному согласию» по ст. 9 в ред. ФЗ № 156-ФЗ.

**Consequences:**

- Положительные: ст. 12 compliance закрыт; choice architecture соответствует privacy-by-design (ст. 5 минимизация ТППД); пользователь сохраняет контроль над тем, какие сервисы получают его ПДн.
- Отрицательные: больше каналов в Notifications state machine (ADR-010); UX-сложность при выборе на signup; для users без ТППД-согласия — нет Telegram Mini App push (deferred to email/SMS).
- **Триггеры пересмотра:** (a) РКН меняет статус ОАЭ / Нидерландов / Сингапура в перечне «адекватных стран» по Приказу № 128 от 05.08.2022 → откат на domestic-only за 1 неделю; (b) >30% пользователей не дают cross-border consent → пересмотреть UX onboarding-а; (c) Telegram FZ-LLC меняет регистрацию → revalidate ст. 12.

### ADR-014 — Field-level encryption for PII

- **Status:** Accepted (2026-05-24).

**Context.** Поля `contacts_sharing_channel.channel_value` (телефон, email, Telegram username), `identity_auth_user.phone_e164`, `verification_user_verification.evidence_ref`, `notifications_delivery.delivery_metadata` (содержит адреса) — это PII по 152-ФЗ ст. 3 п. 1. Encryption-at-rest на disk-level обеспечивает Yandex Managed PG, но это не защищает от: (a) compromise Yandex admin / DBA access; (b) дампов БД, утекающих за пределы encrypted volume (backup misconfiguration); (c) разработческого доступа к prod-replica для debug. Нужно field-level encryption — ключ не должен покидать application boundary.

Альтернативы сравнены:

|Подход                                                      |Pros                                                             |Cons                                                                                                                                                                                                                                                      |
|------------------------------------------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|**pgcrypto symmetric (`pgp_sym_encrypt`)**                  |Прозрачно для Django; ключ в env                                 |Ключ передаётся в БД в plain (PostgreSQL docs F.26: «pgcrypto functions run inside the database server — all the data and passwords move between pgcrypto and client applications in clear text»). Yandex admin / pg_stat_activity видят ключ. Отвергнуто.|
|**`django-cryptography` (Fernet AES-128-CBC + HMAC-SHA256)**|App-level; ключ не покидает app; transparent encryption через ORM|Нет SQL-level search/index по encrypted полям; для exact-match нужен HMAC-индекс.                                                                                                                                                                         |
|**HashiCorp Vault / SOPS file-based**                       |Профессиональный KMS                                             |Добавляет компонент вне frozen-стека; нарушает ADR-006 (single source).                                                                                                                                                                                   |

**Decision.** Application-level encryption через `django-cryptography-django5` (fork с поддержкой Django 5.x; см. PyPI) с master-key в **Yandex Lockbox** (Yandex managed KMS, RU jurisdiction — соответствует ст. 18 152-ФЗ). Ключ ротируется ежегодно; старые ключи остаются в keyring для расшифровки исторических данных.

Использование в коде:

```python
# apps/contacts_sharing/models.py
from django_cryptography.fields import encrypt

class UserContactChannel(models.Model):
    channel_value = encrypt(models.TextField())
    channel_value_hash = models.CharField(max_length=64, db_index=True)
    # HMAC-SHA256(secret, channel_value) — для exact-match lookup
    # (UNIQUE constraint на (user_id, channel_type, channel_value_hash))
```

Поиск по encrypted полю (например, find user by phone для merge guest RSVP):

```python
# apps/contacts_sharing/services.py
def find_user_by_phone(*, phone_e164: str) -> UserDTO | None:
    phone_hash = hmac.new(
        settings.PII_HMAC_SECRET.encode(),
        phone_e164.encode(),
        hashlib.sha256,
    ).hexdigest()
    channel = UserContactChannel.objects.filter(
        channel_type='phone',
        channel_value_hash=phone_hash,
    ).first()
    return UserDTO.from_orm(channel.user) if channel else None
```

**Alternatives considered:** см. таблицу выше. pgcrypto отвергнут (key in clear); Vault — лишний компонент. Для соло-ИП баланс простота / безопасность достигается django-cryptography + Yandex Lockbox.

**Consequences:**

- Положительные: PII защищены от Yandex admin / DBA с прямым доступом к dump’ам и snapshots; ключ ротируется централизованно; HMAC-индекс обеспечивает exact-match поиск.
- Отрицательные: невозможен `ILIKE` / partial match по encrypted полям (только exact через HMAC); migration существующих данных при ротации требует backfill task; +5–10ms latency per encrypted field operation.
- **Триггеры пересмотра:** (a) Yandex прекращает Lockbox или поднимает цену > 30% / квартал → migration на SOPS-based encrypted secrets в env; (b) появление quantum-safe требования — переход с AES-128 на PQC algorithm; (c) >5 GET endpoints начинают требовать ILIKE по encrypted полям — пересмотреть field-level encryption на column-level (например, Tink searchable encryption).

### ADR-015 — OG image generation strategy

- **Status:** Accepted (2026-05-24).

**Context.** V1.1 (раздел Shareable Event Cards) требует динамические OG-картинки для events (preview в Telegram / WhatsApp / iMessage share + Open Graph для соцсетей). Каждое событие должно иметь уникальный preview с cover photo (или градиент-fallback), названием, датой+временем, городом, именем+аватаром организатора, badge верификации, watermark.

Vercel deployment не используется (ADR-005), значит `@vercel/og` в managed-режиме недоступен. Нужна self-hosted альтернатива, не нарушающая ADR-001 (modular monolith — никаких новых runtime / микросервисов).

Опции рассмотрены:

|Опция                                |Pros                                                                                                                                                                   |Cons                                                                          |
|-------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
|**`@vercel/og` в Next.js standalone**|Satori (HTML→SVG) + @resvg/resvg-js (SVG→PNG); работает в любом Node.js runtime [F: anasrin.dev «Generate Image From HTML Using Satori and Resvg»; yusufff/satori-node]|Только flexbox, без CSS grid; шрифты ttf/otf/woff; bundle ≤500 KB             |
|**Headless Chrome / Puppeteer**      |Полный CSS + JS render                                                                                                                                                 |50 MB+ bundle, 4+ сек cold start; нарушает ADR-001 (отдельный browser runtime)|
|**Pillow / ImageMagick на Python**   |В рамках Django, без Node                                                                                                                                              |Pixel-perfect text rendering хуже; кастомные шрифты сложнее                   |
|**Bannerbear / Placid (managed)**    |Zero ops                                                                                                                                                               |Stripe billing → ADR-005; нарушает 152-ФЗ ст. 18                              |

**Decision.** Поэтапная стратегия:

- **Phase 1 + Pilot Этап 0 + Soft launch (Месяцы 0–5):** статический placeholder PNG (один на всю платформу — градиент + логотип). Устраняет 90% сложности; OG preview работает технически (заглушка), но не personalized.
- **V1.1 (после PMF, Месяцы 5+):** Next.js API route `/api/og/event/[id]` с `@vercel/og` package в standalone-режиме. Кешируется через Yandex CDN (`cache-control: public, immutable, max-age=31536000` — год; cache-busting через `?v=N` в URL при изменении event).

**Реализация V1.1** (Next.js, без Vercel deployment):

```typescript
// frontend/app/api/og/event/[id]/route.ts
import { ImageResponse } from '@vercel/og';

export const runtime = 'nodejs';  // не edge — нужен Node для satori standalone

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const event = await fetchEventForOG(params.id);  // proxy через Django, RU-localized
  return new ImageResponse(
    <div style={{ display: 'flex', /* ...flexbox only */ }}>
      {/* title, date, city, organizer */}
    </div>,
    {
      width: 1200, height: 630,
      headers: { 'cache-control': 'public, immutable, max-age=31536000' },
    },
  );
}
```

**Alternatives considered:** см. таблицу. Headless Chrome — оверкилл и нарушает ADR-001; Pillow — хуже visual quality; managed-сервисы — billing проблема.

**Consequences:**

- Положительные: дёшево (один Yandex CDN endpoint); в стеке нет нового runtime — Next.js уже там; ADR-001 не нарушен; cache-immutable снижает load на CDN.
- Отрицательные: latency первого render’а ~200–500ms (cold cache); нужен warm-up на новые events; flexbox-only ограничивает дизайн complex layouts.
- **Триггеры пересмотра:** (a) p95 OG generation > 1s даже с warm cache → рассмотреть отдельный микросервис (Cloudflare Worker / Yandex Function); (b) OG traffic > 50% от total bandwidth → отдельный CDN-cluster; (c) дизайн потребует grid или JS-driven layouts → переход на headless Chrome в отдельном sidecar контейнере.

### ADR-016 — Cross-context events via Transactional Outbox

- **Status:** Accepted (2026-05-24).

**Context.** Django signals (built-in event mechanism) не транзакционны. Типичный failure mode: внутри `with transaction.atomic(): event.save(); signals.send('event_created')` — если subscriber упал ПОСЛЕ commit основной транзакции (например, `notifications.enqueue_notification` хочет писать в БД, а её connection drop’нулся), событие потеряно. На MVP это критично: потеря NotificationDelivery means провал ADR-010 NSM (`acknowledged / delivered`).

Industry pattern для модульных монолитов — **Transactional Outbox**. Запись в outbox-таблицу происходит в той же транзакции, что и основной mutation; асинхронный worker читает outbox и доставляет subscribers. Гарантия at-least-once delivery; consumer-side идемпотентность обязательна. Применён в Spring Modulith [F: wim deblauwe «Transactional Outbox pattern with Spring Boot»], Open edX [F: decision 0015 «Outbox pattern and production modes»], Loadsmart Jaiminho [F: engineering.loadsmart.com], Fever Engineering [F: medium.com/fever-engineering «Enhancing Inter-Service Communication»].

**Decision.** Cross-context events публикуются через таблицу `outbox_event` (см. [Outbox infrastructure section](#outbox-cross-cutting-infrastructure)); Procrastinate periodic-task poll-ит и доставляет subscribers. Гарантия at-least-once; consumer-side идемпотентность через event.id как dedupe key. Django signals остаются для intra-context concerns (validation, denormalization внутри одного `apps.<ctx>/`).

**Alternatives considered:**

- **Django signals as-is.** Отвергнуто: loss риск (см. Context).
- **Redis pub/sub.** Отвергнуто: нарушает ADR-006 (single source PostgreSQL); добавляет managed-компонент.
- **Apache Kafka.** Отвергнуто: frozen stack; overkill для соло-ИП объёма (≤1k events/min на год+).
- **Готовый пакет `django-outbox-pattern` / `django-jaiminho`.** Рассмотрены как fallback если ручная реализация (~150 строк) окажется громоздкой. Выбор — после Phase 1.

**Consequences:**

- Положительные: at-least-once delivery; cross-context coupling декларативный (через event_type); audit trail в outbox table (debug + compliance).
- Отрицательные: ~5s latency между publish и delivery (poll-интервал); consumers ОБЯЗАНЫ быть идемпотентны (использовать event.id); outbox table size надо мониторить (retention 30 дней — см. Wave 3 Data Retention Policies).
- **Триггеры пересмотра:** (a) outbox lag > 30s p95 → уменьшить poll-интервал или перейти на LISTEN/NOTIFY; (b) event volume > 10k/min → рассмотреть Kafka или Redis Streams через ADR-update; (c) появление requirement на ordered delivery within aggregate → добавить `sequence_number` partition по `aggregate_id`.

-----

## Источники

Источники сохранены ровно так, как зафиксированы в оригинальных промптах и исследованиях V1.0, V1.1, V1.2, V1.3.

### Iteration 1-5 reconciliation (Wave 1+ audit history)

- Iteration 1 Pre-Development Readiness Audit (6-phase gap report + 12 scaffolding sketches).
- Iteration 2 PDF spotchecks (V1.1 magic links, V1.2 monetization 4 layers, V1.3 Level C identity/events/rsvp).
- Iteration 3 reconciliation report (drift map: PDF V1.0-V1.3 ↔ 4 файла Wave 1/2/3) — закрепляет **0 архитектурных противоречий, только expansion**; критическое renumbering ADR-005 ↔ ADR-007; 18 corrections для 4 главных файлов.
- Iteration 4 scaffolding implementation (13 артефактов: CHANGELOG, pyproject.toml, .env.example, .importlinter, pilot-day-template, 2 SKILL.md, jtbd-bc-mapping, risk-register, identity_auth CLAUDE.md, docker-compose, Makefile, init.sql).
- Iteration 4.5 red-team audit (`docs/iterations/iteration-4.5-audit-report.md`) — 5 fixes applied (2 Critical ADR-005 misattribution + 3 Major).
- Iteration 5 corrections (worklog в `docs/iterations/iteration-5-applied.md`) — 18 точечных diff-коррекций к 4 главным файлам по spec Iteration 3 § 3.1-3.4.
- Iteration 5.5 next-steps roadmap (`docs/iterations/iteration-5.5-roadmap.md`) — repository state snapshot, 8 open founder decisions, 25-step DAG, critical path, 7-day action plan.
- Iteration 6 skills library bootstrap (`docs/iterations/iteration-6-applied.md`) — 8 SKILL.md созданы; полный набор 10/10 в `.claude/skills/`.
- Iteration 7 per-context CLAUDE.md bootstrap (`docs/iterations/iteration-7-applied.md`) — 5 per-context CLAUDE.md (events, rsvp, contacts_sharing, recommendations, localization), полный набор 6/6.
- Iteration 8 docs bootstrap (`docs/iterations/iteration-8-applied.md`) — 8 артефактов: erd.md + openapi.yaml + glossary.md + 3 runbooks + AI-WORKFLOW.md + SECURITY.md root.
- Architecture self-audit (2026-05-27, pre-Phase 1) — 8 рассинхронизаций исправлены: ConsentRecord schema purposes (3→7), header ADR count (13→16), SKILL.md status (2→10/10), Phase 4 ref → Iteration 9, broken cross-ref на 4.5 audit, `cross_border_consent` typo, erd.md missing BC list, iteration history extended.

### Конкуренты

- Luma Pontis 2021: `luma.com/p/zPamspcICt0f3q9`
- Luma help center: `help.luma.com`
- Partiful CTO Joy Tao: `theorg.com/org/partiful`, `wellfound.com/p/joytao`
- Eventbrite migration: `medium.com/@eventbrite/our-strategy-to-migrate-to-django` (2016)
- Eventbrite open-source: `eventbrite.com/open-source` (2025)
- Hipcamp Scout: `hipcamp.com/journal/engineering/scout-our-in-house-ai-agent` (январь 2026)
- Hipcamp Expo upgrade: `expo.dev/blog/how-hipcamp-upgraded-expo-sdk-versions-with-claude-code` (апрель 2026)
- Airbnb reciprocity: Fradkin et al., «Reciprocity and Unveiling in Two-Sided Reputation Systems», Marketing Science, 2021
- Eventbrite Q4 2024 Shareholder Letter, SEC Form 8-K, 27 февраля 2025

### Технологический стек

- Django 5.2 LTS release: `docs.djangoproject.com/en/5.2/releases` (апрель 2025)
- Django 6.0 release: `habr.com/ru/articles/973074` (декабрь 2025)
- SWE-bench Verified: `benchlm.ai/benchmarks/sweVerified` (22.05.2026), `llm-stats.com/benchmarks` (май 2026), `mindstudio.ai` (апрель 2026)
- TS slow vs JS: `dev.to/mame` (март 2026)
- import-linter: `github.com/seddonym/import-linter` (активный 2026)
- Shopify modular monolith: `shopify.engineering/deconstructing-monolith` (2020)
- Kamil Grzybek modular monolith: `github.com/kgrzybek/modular-monolith-with-ddd`
- django-otp-webauthn: `github.com/Stormbase/django-otp-webauthn` (Stable since May 2025)
- pganalyze RLS Django: `pganalyze.com/blog/postgres-row-level-security-django-python`
- Postgres RLS multitenancy: `dev.to/dvoraj75/why-postgresql-row-level-security-is-the-right-approach-to-django-multitenancy-3e1m`

### РФ-инфраструктура

- Yandex Cloud pricing: `yandex.cloud/en/docs/managed-postgresql/pricing` (новые цены с 01.05.2026)
- Selectel: `selectel.ru`, `dieg.info` (август 2025)
- Russia internet restrictions: `en.wikipedia.org/wiki/2025_internet_restrictions_in_Russia`, `en.wikipedia.org/wiki/Wartime_internet_restrictions_in_Russia_(2025-present)`
- SMS.ru: `sms.ru` (май 2026)
- SMSC: `smsc.ru` (май 2026)

### Auth / Identity

- Clerk billing: `clerk.com/docs/guides/billing/overview` (19.05.2026)
- Convex backend: `github.com/get-convex/convex-backend`
- Convex assessment: `srvrlss.io`, `toolradar.com` (2026)
- Telegram Login Widget: `core.telegram.org/widgets/login`
- Telegram Mini Apps: `core.telegram.org/bots/webapps`
- Telegram OIDC: `core.telegram.org/bots/telegram-login`
- Telegram Gateway: `core.telegram.org/gateway`
- FIDO Alliance passkeys 2026: `fidoalliance.org/fido-alliance-reports-accelerating-global-passkey-adoption-on-world-passkey-day-2026` (7 мая 2026)
- Magic link pitfalls: `etodd.io/2026/03/22/magic-link-pitfalls/`
- Supertokens magic links: `supertokens.com/blog/magiclinks`

### iOS / Apple / RuStore

- Apple payment processing off in RU: `macdailynews.com` (02.04.2026), `appleinsider.com` (02.04.2026)
- RuStore self-employed: `rustore.ru/developer/blog/self-employed` (декабрь 2025), `vc.ru/id4657639` (декабрь 2025)

### Claude Code productivity

- Anthropic Claude Code best practices: `anthropic.com/engineering/claude-code-best-practices` (18 апреля 2025, Boris Cherny)
- CLAUDE.md hierarchy: `agentfactory.panaversity.org/docs/General-Agents-Foundations/claude-code-teams-cicd/claude-md-configuration-hierarchy`
- Digital Applied case study: `digitalapplied.com/blog/case-study-claude-code-team-adoption-30-dev-shop-2026` (15 мая 2026)

### 152-ФЗ / Compliance

- 152-ФЗ ст. 9 ред. 156-ФЗ: `consultant.ru` ст. 9 в ред. от 24.06.2025
- 152-ФЗ ст. 18 (локализация): `consultant.ru` ст. 18
- Регистрация оператора РКН: `garant.ru` (2025), `klerk.ru` (2025), `pd.rkn.gov.ru/operators-registry/notification/`

### OG / Frontend

- Vercel OG performance: `vercel.com/blog/introducing-vercel-og-image-generation`, `vercel.com/docs/og-image-generation`
- Open Graph specs: `opengraph.dev`
- Web Share API: `developer.mozilla.org/en-US/docs/Web/API/Web_Share_API`, `caniuse.com/web-share`

### RFC 5545 / Recurrence

- iCalendar RFC 5545: `datatracker.ietf.org/doc/html/rfc5545`
- iCalendar standard: `icalendar.org`

### OWASP

- OWASP Top 10 2025: `fastly.com/blog/new-2025-owasp-top-10-list`, `parasoft.com/blog/owasp-top-10`

### Privacy / Email tracking

- Postmark on Apple MPP: `postmarkapp.com`
- SendGrid docs: `twilio.com/docs/sendgrid`
- Twilio blog on Link Tracking Protection: `twilio.com/en-us/blog` (2025)
- Nylas: `nylas.com`

### Verification vendors

- Sumsub: `sumsub.com`
- Idenfy: `idenfy.com`
- IDX: `idx.ru`
- GuyID on Bumble verification: `guyid.com` (2026)
- Biometric Update on Bumble Veriff: `biometricupdate.com` (март 2025)

### Caveats и проверка соответствия

**Подтверждённые с двумя+ независимыми источниками:**

- Django 5.2 LTS release date and support window (docs.djangoproject.com + habr.com)
- SWE-bench Verified scores Claude Opus 4.7 (benchlm.ai + llm-stats.com + mindstudio.ai)
- Eventbrite на Django (Medium + open-source publications + GitHub org)
- Luma на Next.js + Koa + PostgreSQL/Aurora + AWS (Pontis post + Luma help center)
- Hipcamp + Claude Code + React Native Expo (Hipcamp engineering blog + Expo dev blog)
- 152-ФЗ ст. 18 + ст. 9 в ред. 156-ФЗ (consultant.ru + garant.ru + klerk.ru)
- Apple payment off in RU 01.04.2026 (macdailynews.com + appleinsider.com)
- Cloudflare/AWS edges нестабильны в РФ (Wikipedia)

**Помеченные `[Г]` (одиночные источники, требуют верификации в Этапе 0):**

- Точные цены Yandex Cloud Compute, Managed Postgres.
- Точные цены VK Cloud, Selectel Managed Postgres.
- Email ESP pricing UniSender vs SendPulse.
- Procrastinate как «production-стандарт» для соло Django-проектов.
- aiogram 3.x как production-стандарт RU.
- Coolify зрелость 2024–2026.

**Помеченные `[?]`:**

- Точные версии PostgreSQL у Yandex Managed (14/15/16/17).
- Backup retention VK Cloud Managed Postgres.
- Cache TTL WhatsApp/iMessage для OG-превью.
- Партнёрский tier-list Sumsub vs IDX для photo verification.

-----

> **Финальная позиция:** универсальная горизонтальная площадка для поиска компании реалистична для соло-фаундера на AI-разработке при выполнении всех условий, описанных в Разделе «Конкурентный контекст» документа [`PRODUCT.md`](./PRODUCT.md). Главный риск — не технический и не категорийный, а **поведенческий:** соло-фаундер должен 12+ месяцев держать дисциплину «не расширять раньше времени» при постоянном внешнем давлении расширяться. Архитектура и план работ выше составлены так, чтобы эту дисциплину поддерживать структурно.