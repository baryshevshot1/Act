# Act

> Универсальная host-first платформа для поиска компании на совместные мероприятия — от спонтанной прогулки до регулярной групповой тренировки с тренером, от культурного похода до платной экспертной консультации.

|Параметр       |Значение                                                                    |
|---------------|----------------------------------------------------------------------------|
|**Статус**     |Pre-Phase 0 (Compliance baseline pending) — Wave 1 + Wave 2 + Wave 3 applied|
|**Команда**    |Соло-фаундер-ИП (резидент РФ)                                               |
|**Стек**       |Frozen V1.2 (Django 5.2 LTS + Next.js 16 + PostgreSQL 17 + Yandex Cloud)    |
|**Архитектура**|Modular monolith, 16 bounded contexts                                       |
|**Compliance** |152-ФЗ ст. 18 + ст. 12 + ст. 22, OWASP Top 10:2025                          |
|**Обновлено**  |2026-05-24 (после P0 Wave 1 + P1 Wave 2 + P2 Wave 3 review)                 |


> **TODO (домен):** в исходных материалах фигурирует `findacomp.app` и Telegram-бот `findacomp_bot`. После переименования в Act планируется `act.app` / `act_bot`, но доступность не проверена. Проверить через `whois act.app` и Telegram BotFather до конца Phase 0; альтернативы — `act.events` / `joinact.app` / `act-app.ru`.

-----

## Что это и для кого

Act — modular monolith с i18n (RU+EN с дня 1), гео-aware каталогом, двусторонней рейтинговой системой и опциональным обменом контактами. Архитектурно похож на Luma, но локализован под РФ-инфраструктуру и санкционные ограничения для соло-ИП.

**Стартовый wedge:** тренеры регулярных групп (бег, йога, силовые) в Москве. Запуск в одной географии × одной категории — обязательное условие выживания горизонтальной площадки.

**Ключевой UX-differentiator vs Luma/Meetup:** серия с автогенерацией экземпляров + per-instance RSVP-подтверждение (см. JTBD-2 в [`docs/PRODUCT.md`](./docs/PRODUCT.md#jtbd-jobs-to-be-done)).

-----

## Структура документации

Порядок чтения для нового участника команды или AI-ассистента:

|#|Файл                                            |Зачем                                                                                                                                                                      |Когда читать                                  |
|-|------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------|
|1|[`CLAUDE.md`](./CLAUDE.md)                      |Стек (frozen), конвенции, 11 NON-NEGOTIABLE, глоссарий, anti-patterns. ~100 строк.                                                                                         |**Всегда первым.** Перед любой задачей.       |
|2|[`docs/PRODUCT.md`](./docs/PRODUCT.md)          |Стратегия, JTBD, конкуренты, монетизация, V1.1 (shareable cards / onboarding / security), детальный UX для Recurrence / Contacts / Ratings / Verification / Notifications. |Перед продуктовыми решениями.                 |
|3|[`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)|16 bounded contexts, 6 готовых Level C, полный стек (Уровень B), RLS Operational Constraints, 13 ADR, Bootstrap, Pilot Этап 0, Migration paths, Risk register. ~1900 строк.|Перед кодом, миграциями БД, выбором паттернов.|

**Доп. промты в** [`prompts/`](./prompts/) — переиспользуемые промты для Claude Code:

- `level-c-light-and-design-adrs.md` — Level C light для 3 контекстов + 4 design ADR.
- `architecture-review-application.md` — применение архитектурного ревью по трём волнам (P0 + P1 + P2 + gaps).
- `claude-md-consistency-audit.md` — проверка согласованности 4 docs-файлов и применение Anthropic best practices.

**Иерархия `CLAUDE.md`** (по рекомендации Anthropic Claude Code): root `CLAUDE.md` зафиксирует project-wide контекст; после Phase 1 bootstrap появятся **per-context** `backend/apps/<context>/CLAUDE.md` с local-scope правилами (например, `apps/events/CLAUDE.md` фиксирует RFC 5545 терминологию и Recurrence-специфичные patterns).

-----

## Стек одной строкой

Django 5.2 LTS · Python 3.12 · Next.js 16 App Router · next-intl · PostgreSQL 17 (Yandex Managed) · Django ORM + RLS (FORCE + default_deny) · Procrastinate (Postgres-backed) · in-Postgres cache/session · PostgreSQL FTS · pgcrypto · Yandex Object Storage · Yandex CDN · UniSender/SendPulse · SMS.ru · aiogram 3.x · Telegram Gateway · django-allauth + django-otp + django-otp-webauthn · django-cryptography + Yandex Lockbox · PostHog self-hosted · Sentry/GlitchTip self-host · LGTM-стек · Yandex Cloud + Coolify · GitHub Actions · import-linter · PWA + Telegram Mini App · pytest + Playwright.

Полное обоснование с альтернативами, migration paths и required extensions — в [`docs/ARCHITECTURE.md#стек-уровень-b`](./docs/ARCHITECTURE.md#стек-уровень-b) и [ADR-006 → Required PostgreSQL extensions](./docs/ARCHITECTURE.md#adr-006--postgresql-как-single-source-of-truth).

-----

## Compliance baseline (БЛОКЕР для production)

> **Запуск production-сайта без выполнения этого чек-листа = штраф 100 000–300 000 ₽ для ИП** по ч. 10 ст. 13.11 КоАП РФ (с 30 мая 2025, ФЗ № 420-ФЗ от 30.11.2024). 50%-скидка по ст. 4.1.1 КоАП НЕ применяется.

Перед публикацией production-сайта обязательны:

|#  |Действие                                                                                   |Срок               |Подробнее                                                                                       |
|---|-------------------------------------------------------------------------------------------|-------------------|------------------------------------------------------------------------------------------------|
|0.1|Уведомление РКН по **ст. 22** 152-ФЗ через `pd.rkn.gov.ru/operators-registry/notification/`|До 30 дней проверки|[ADR-012](./docs/ARCHITECTURE.md#adr-012--compliance-baseline-ркн--согласие--локализация)       |
|0.2|Уведомление РКН по **ст. 12** (трансграничная передача в Telegram) — ОТДЕЛЬНОЕ от 0.1      |Параллельно с 0.1  |[ADR-013](./docs/ARCHITECTURE.md#adr-013--notification-channel-fallback-для-non-consented-users)|
|0.3|Privacy Policy на `/privacy` (ст. 18.1)                                                    |1 день             |—                                                                                               |
|0.4|Отдельный документ согласия по ст. 9 ред. ФЗ № 156-ФЗ от 24.06.2025                        |1 день             |—                                                                                               |
|0.5|Cookie consent UI (Essential / Analytics / Marketing)                                      |1–2 дня            |Wave 3 (планируется)                                                                            |

Эти задачи запускаются **параллельно с Phase 1 (Bootstrap)** — срок проверки РКН до 30 дней, поэтому начинать сразу.

-----

## Quick start для founder’а

День 1 (после ИП открыт и расчётный счёт получен):

1. **Подать оба РКН-уведомления** (см. таблицу выше). До получения регистрации — никаких production-релизов.
1. **Прочитать `CLAUDE.md`** — фиксированный стек, конвенции, NON-NEGOTIABLE.
1. **Прочитать `docs/ARCHITECTURE.md` → Bootstrap Phase 0 + Phase 1.**
1. **Запустить Phase 1 → 1.1 (Yandex Cloud setup)** — folder structure, IAM, Managed PostgreSQL 17, Object Storage.

Неделя 1 (Phase 1 — Bootstrap, 3–7 дней):

1. GitHub monorepo + branch protection.
1. Django skeleton + 3 контекста (`identity_auth`, `events`, `rsvp`).
1. **`apps/core/migrations/0001_extensions.py`** (`pgcrypto`, `btree_gist`, `pg_trgm`, `unaccent`) — прогон через прямой PG, **минуя PgBouncer**.
1. Next.js skeleton + next-intl proxy.
1. `import-linter` контракты, включая запрет `.raw()` вне `apps.core.rls`.
1. Procrastinate periodic-task заглушка.
1. Coolify на Yandex Compute.

Phase 2 (Pilot Этап 0, 5–7 дней) — единственная процедура, превращающая теоретический выбор стека в эмпирический commit. KPI: Accept-Rate ≥ 60% на core-flow (см. [Pilot Этап 0](./docs/ARCHITECTURE.md#pilot-этап-0)).

-----

## Эпистемическая разметка

Используется единая разметка во всех документах:

- `[F: источник]` — факт со ссылкой
- `[В]` — вывод автора на основании совокупности фактов
- `[Г]` — гипотеза, требующая проверки
- `[?]` — неизвестное

AI-ассистент **не должен** интерпретировать `[Г]` и `[?]` как факты при принятии архитектурных решений.

-----

## Что зафиксировано / что открыто

**Зафиксировано (V1.0 → V1.2 → P0 Wave 1 → P1 Wave 2):**

- Концепция, JTBD-1..6, wedge, монетизационная модель (4 слоя).
- 16 bounded contexts modular monolith + Outbox cross-cutting infrastructure.
- Полный технологический стек (Уровень B), включая `django-cryptography` + Yandex Lockbox для PII encryption (ADR-014).
- **6 готовых Level C:** Identity & Auth, Events (с Recurrence), RSVP & Attendance, Contacts Sharing, Recommendations, Localization.
- **16 ADR:** ADR-001..011 (Wave 0–2) + ADR-012 (Compliance Baseline) + ADR-013 (Notification fallback) + ADR-014 (Field encryption) + ADR-015 (OG strategy) + ADR-016 (Transactional Outbox). Полный список с triggers пересмотра — [`docs/ARCHITECTURE.md#adr-architecture-decision-records`](./docs/ARCHITECTURE.md#adr-architecture-decision-records).
- **RLS Operational Constraints:** middleware с `transaction.atomic()`, FORCE ROW LEVEL SECURITY + RESTRICTIVE default_deny, отдельная BYPASSRLS-роль для Django Admin, запрет `.raw()` вне `apps.core.rls`, performance patterns ((SELECT) wrap + partial indexes).
- **UUID Strategy:** UUIDv7 для PK write-heavy таблиц, UUIDv4/CSPRNG для tokens.
- **Translation strategy:** UI-строки в `messages/{locale}.json`; справочники в JSONB с expression indexes; пользовательский контент — `events_event_translation`.
- **Discovery ranking (ADR-008):** hybrid blend transition + per-weight PostHog feature flags; 14d half-life помечен `[Г]`.
- Risk register с 7 рисками.

**Открыто (требует Pilot и далее):**

- **Pilot Этап 0** не выполнен — стек подлежит эмпирической проверке (Accept-Rate ≥ 60% target hypothesis, см. [Pilot Этап 0](./docs/ARCHITECTURE.md#pilot-этап-0)).
- **Level C для 10 оставшихся контекстов** (Verification, Groups, Notifications, Moderation, и др.) — после успешного пилота.
- **Дизайн-language и UI-kit** — отложено до Pilot.
- **Точные цены провайдеров** (Yandex Cloud, Yandex Lockbox, UniSender) — верифицируются в Phase 0.
- **Yandex Managed PG 18 availability** — `[?]`; если только PG 17, используется `pg_uuidv7` extension (см. ADR-006).
- **Per-context `apps/<ctx>/CLAUDE.md`** — создаются в Phase 1 bootstrap (см. Anthropic Claude Code иерархия).

-----

## Источники документации

Документация консолидирована из трёх рабочих документов и одного ревью:

- **V1.0 (Уровень A)** — стратегия, видение, архитектура (16 bounded contexts).
- **V1.1 (Addendum, 23 мая 2026)** — shareable event cards, frictionless onboarding, безопасность.
- **V1.2 + V1.3 (24 мая 2026)** — Tech Stack (Уровень B), Pilot Этап 0, Bootstrap, Level C для трёх критичных контекстов. **Stack commit decision: ADR-005 в V1.3 → переименован в ADR-007 в Wave 1** (см. `docs/CHANGELOG.md` renumber note). PDF-черновики могут ссылаться на «ADR-005» как stack commit — это устаревшая нумерация.
- **Architectural Review + P0 Wave 1** (после 24 мая 2026) — добавлены 3 Level C (Contacts Sharing, Recommendations, Localization), 4 design ADR (008–011), 2 compliance ADR (012–013), RLS Operational Constraints, Pre-pilot Compliance baseline, обновлённый Risk register.

Все цитаты сохранены в формате `[F: источник, дата]` внутри документов. Сводный список источников — в [`docs/ARCHITECTURE.md#источники`](./docs/ARCHITECTURE.md#источники).