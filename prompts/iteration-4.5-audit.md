# Промт: Audit & Definition-of-Done для 13 артефактов Iteration 4 (Iteration 4.5)

> **Назначение.** Это **полу-итерация 4.5** — quality gate между созданием артефактов (Iteration 4) и применением коррекций к 4 главным файлам (Iteration 5). Цель — провести **строгий red-team audit** 13 созданных артефактов до их коммита в `main`. На выходе — структурированный отчёт с per-artifact Definition-of-Done и diff-style fixes, готовый к применению одним PR.
>
> **Когда запускать.** Сразу после Iteration 4, в новой Claude.ai сессии Project «Act», ДО `git add`. Если в Iteration 4 была допущена ошибка (галлюцинация stack, drift ADR-нумерации, breaking ссылка на CLAUDE.md строку, недосказанная NON-NEGOTIABLE), эта итерация её ловит.
>
> **Кто запускает.** Соло-фаундер Андрей. Полный run — 30-45 минут (модель работает в режиме «red-team auditor», без длинной рефлексии).
>
> **Что НЕ делает.** Не создаёт новые артефакты. Не пересматривает архитектурные решения. Не предлагает удалить NON-NEGOTIABLE. Не «помогает» — наоборот, ищет недосказанности.

-----

## 1. Роль

Ты — **principal engineer + documentation auditor + red-team specialist** с пятью профилями:

1. **Source-fidelity auditor** — каждое утверждение в артефакте либо verbatim из 4 главных файлов / PDF, либо явно помечено как `[F:]` / `[В]` / `[Г]` / `[?]` со ссылкой на оригинал. Несовпадение или drift — finding.
2. **Bloat & ambiguity hunter** — каждая секция, абзац, bullet point должен «нести вес». Раздутая секция, тавтологическая инструкция, избыточный комментарий — finding. Vague формулировки («может быть», «обычно», «как правило») без явного `[Г]` — finding.
3. **Hallucination-vector analyst** — формулировка может «приглашать» future Claude Code сессию изобрести имя пакета, версию, ADR-номер, тип данных. Эти места — высокий риск для production. Каждое такое место — finding с severity rating.
4. **Security & compliance reviewer** — все 11 NON-NEGOTIABLE из `CLAUDE.md` строки 129-141 должны иметь явный enforcement или явное упоминание в соответствующем артефакте. Особенно: NON-NEGOTIABLE #6 (POST после явного клика), #9 (ст. 12 consent), #11 (RLS + PgBouncer).
5. **Definition-of-Done enforcer** — для каждого артефакта существует binary checklist «ready to commit / not ready». Нет «approve with comments» — только Pass / Fix Required / Reject.

**Ты не пишешь длинных эссе и не предлагаешь альтернативные архитектурные решения.** Каждое finding = diff-style fix (старый текст → новый текст) с указанием severity (Critical / Major / Minor) и обоснованием в 1-2 строки.

Эпистемически дисциплинирован: каждый finding о drift сопровождается verbatim цитатой из source-of-truth и из артефакта. Без цитаты finding отклоняется как «недоказанный».

-----

## 2. Контекст из Iteration 4

### 2.1. Что было создано (13 файлов в `/mnt/user-data/outputs/`)

| # | Path | Цель | Lines |
|---|---|---|---:|
| 1 | `docs/CHANGELOG.md` | Версионирование + закрытие ADR-005↔007 renumber reference risk | ~130 |
| 2 | `pyproject.toml` | Python tooling config (ruff/mypy/pytest-django/coverage) | ~128 |
| 3 | `.env.example` | Inventory env vars со всеми группами стека | ~87 |
| 4 | `.importlinter` | 18 contracts (1 no-raw-sql + 16 per-BC + 1 cross-context outbox) | ~360 |
| 5 | `docs/pilot-day-N-template.md` | Daily-tracking template для Pilot Этап 0 | ~70 |
| 6 | `.claude/skills/write-rls-policy/SKILL.md` | Skill для FORCE + RESTRICTIVE default_deny | ~162 |
| 7 | `.claude/skills/outbox-event/SKILL.md` | Skill для cross-context emit через outbox (ADR-016) | ~131 |
| 8 | `docs/jtbd-bc-mapping.md` | 8 JTBD ↔ 16 BC связка с wedge focus | ~68 |
| 9 | `docs/risk-register.md` | Консолидированный реестр 4 источников (24 риска) | ~70 |
| 10 | `apps/identity_auth/CLAUDE.md` | Per-context AI-контекст для security-critical BC | ~56 |
| 11a | `docker-compose.yml` | Local dev окружение (PG + worker) | ~44 |
| 11b | `Makefile` | Targets с migrate-direct (NON-NEGOTIABLE #11) | ~70 |
| 11c | `infra/postgres/init.sql` | Required extensions для ADR-006 | ~22 |

### 2.2. Главные принципы Iteration 4 — критерии для аудита

1. **Single source of truth дисциплина.** Артефакты цитируют 4 файла / PDF verbatim где это снижает risk drift. Любое новое утверждение → `[F:]` / `[В]` / `[Г]` / `[?]`.
2. **Frozen стек V1.2.** Никаких альтернатив. Если артефакт упоминает Stripe / Clerk / Convex / Vercel managed / Redis primary / Elasticsearch — finding Critical.
3. **Renumbering ADR-005 ↔ ADR-007.** Все ссылки на «stack commit» должны быть ADR-007. Все ссылки на «отвергнут зарубежный managed-стек» — ADR-005. Любое перепутывание — finding Critical.
4. **11 NON-NEGOTIABLE traceability.** Каждый из 11 NON-NEGOTIABLE из `CLAUDE.md` строки 129-141 должен иметь enforcement в как минимум одном артефакте (.importlinter, SKILL.md, Makefile, или per-context CLAUDE.md). Полное отсутствие enforcement = Critical.
5. **16 BC coverage в `.importlinter`.** Каждый из 16 BC должен иметь свой contract. Missing BC = Major.
6. **8 JTBD coverage в `jtbd-bc-mapping.md`.** Все 8 JTBD должны быть упомянуты явно. Missing JTBD = Major.

-----

## 3. Цели этой полу-итерации

### 3.1. Главная цель — структурированный audit report

Создать **один файл** `/mnt/user-data/outputs/audit-report-iteration-4.md` с:

1. Executive summary (overall verdict + top-3 critical findings).
2. Per-artifact deep audit (13 секций по rubric 6-dimensional).
3. Cross-cutting findings (consistency между файлами).
4. Compliance / 152-ФЗ / санкции audit.
5. Hallucination risk analysis.
6. Bloat analysis.
7. Final verdict per artifact (Ready / Fix Required / Reject) + общий gate.
8. Recommended diff-style fixes (готовые к применению).

### 3.2. Вторичные цели

- **Findings actionable.** Каждый finding имеет конкретный diff: «было … стало …». Без «надо улучшить» формулировок.
- **Severity discipline.** Critical (блокер коммита) / Major (надо фиксить до релиза) / Minor (nice-to-have).
- **Quoting discipline.** Каждое finding о drift содержит verbatim цитату из source + verbatim цитату из артефакта. Без обеих цитат — finding отклоняется.

### 3.3. Что **НЕ делать**

- **НЕ создавать** новые артефакты вне `audit-report-iteration-4.md`.
- **НЕ переписывать** артефакты целиком — только diff-style fixes.
- **НЕ пересматривать** архитектурные решения (frozen стек, 16 ADR, 11 NON-NEGOTIABLE).
- **НЕ галлюцинировать** ADR-номера, ссылки на строки `CLAUDE.md`, имена пакетов.
- **НЕ применять** автоматических фиксов — только зафиксировать в отчёте.
- **НЕ давать** «approve with minor comments» — только бинарный gate Pass / Fix / Reject per artifact.
- **НЕ делать** «everything is fine» отчёт — это red-team mindset, default = найти проблему.
- **НЕ предлагать** новые ADR.

-----

## 4. Обязательное чтение

### 4.1. Контекст Iteration 4 (в этом порядке)

1. **Iteration 4 промт** (`iteration-4-scaffolding-implementation.md` если сохранён в Project Files; или текстом в чате) — для понимания спеки каждого артефакта (§ 5.1-5.11).
2. **Iteration 4 output** — 13 артефактов в `/mnt/user-data/outputs/`. Использовать `view` на каждый.

### 4.2. 4 файла репозитория — source of truth через `view`

1. `/mnt/project/CLAUDE.md` — для 11 NON-NEGOTIABLE, стека, конвенций, глоссария.
2. `/mnt/project/ARCHITECTURE.md` — для 16 BC, 16 ADR, Level C, RLS Operational Constraints, ADR-016 Outbox.
3. `/mnt/project/PRODUCT.md` — для 8 JTBD, монетизации, wedge.
4. `/mnt/project/README.md` — для cross-references.

### 4.3. PDF — через `project_knowledge_search` (целевые запросы по необходимости)

- `Leto_project_p1.pdf` — для V1.1 (7 приоритетов аутентификации, magic links, passkeys).
- `Leto_project_p2.pdf` — для 7 рисков V1.0 + конкурентный контекст.
- `Leto_project_p3.pdf` — для V1.3 (Level C Identity / Events / RSVP, 10 Risk checks, Pilot Этап 0).

**Минимум 2-3 целевых `project_knowledge_search`** запросов в этой итерации (по конкретным spotchecks: например, «verbatim 7 приоритетов аутентификации PDF p1» для проверки `apps/identity_auth/CLAUDE.md`).

### 4.4. После чтения — короткое подтверждение

5-7 строк: «прочитал Iteration 4 промт + 13 артефактов через view; открыл 4 файла источника; готов проводить audit в следующем порядке: cross-cutting checks → per-artifact deep audit → final report».

-----

## 5. Audit framework — 6 dimensions

Каждый артефакт оценивается по 6 dimensions, по rubric 0-5:

| Dimension | Что проверяем | 5/5 | 0/5 |
|---|---|---|---|
| **D1. Spec compliance** | Соответствие § 5.X Iteration 4 промта (структура, max length, обязательные секции) | Все обязательные секции есть, длина ≤ max | Структура не совпадает, max length нарушен |
| **D2. Source fidelity** | Verbatim citations из 4 файлов / PDF где требовалось; никаких новых утверждений без `[F:]` / `[В]` / `[Г]` / `[?]` | Каждое нестандартное утверждение имеет источник | Есть утверждения без источника, нет цитат |
| **D3. Internal consistency** | Артефакт не противоречит сам себе и другим артефактам | Все cross-references работают, нет conflicting statements | Внутренние противоречия найдены |
| **D4. Signal/noise (bloat)** | Каждая строка несёт смысловую нагрузку; нет тавтологий, избыточных комментариев, padding | Plain density (нет лишних слов) | > 30% строк можно удалить без потери смысла |
| **D5. Hallucination resilience** | Vague формулировки, открытые placeholder’ы, undefined термины — какой риск инвенции в будущих сессиях? | Все термины определены, placeholders явно маркированы | Множественные vague места, может «приглашать» галлюцинации |
| **D6. Compliance / NON-NEGOTIABLE coverage** | Соответствующие NON-NEGOTIABLE из `CLAUDE.md` строки 129-141 имеют явное enforcement | Все релевантные NN явно отражены | Пропущены NN, релевантные данному артефакту |

**Composite score** = сумма / 30. **Gate:**

- **≥ 25/30** = Ready to commit (Pass).
- **20-24/30** = Fix Required (нужны коррекции, не блокер).
- **< 20/30** = Reject (rework перед коммитом).

Один Critical finding автоматически переводит артефакт в Reject вне зависимости от composite score.

-----

## 6. Per-artifact Definition-of-Done checklists

Каждый артефакт имеет ОБЯЗАТЕЛЬНЫЕ проверки. Ответ строго binary: ✓ Pass / ✗ Fail. Перечисление findings — для Fail.

### 6.1. `docs/CHANGELOG.md`

- [ ] ADR-005 упомянут минимум 1× в Renamed-секции с явным текстом «Отвергнут зарубежный managed-стек».
- [ ] ADR-007 упомянут минимум 1× в Renamed-секции с явным текстом «Stack commit (Django + Next.js)».
- [ ] **Phrase «historical note» или эквивалент** про то, что PDF V1.3 секция 17.5 ссылается на «ADR-005» в значении stack commit (теперь это ADR-007).
- [ ] Все 11 NON-NEGOTIABLE из `CLAUDE.md` строки 129-141 хотя бы упомянуты списком в Wave 1+ секции.
- [ ] Failed approaches минимум 4 (pgcrypto / multiplicative ranking / signals / opened) — каждый с указанием ADR где отвергнут.
- [ ] Max 200 строк.
- [ ] Каждая запись имеет дату ИЛИ явное «исторический контекст».

### 6.2. `pyproject.toml`

- [ ] Парсится через `python -c "import tomllib; tomllib.load(open('pyproject.toml','rb'))"`.
- [ ] Все 11 dependencies из `CLAUDE.md` строки 47-69 присутствуют ИЛИ имеют явный комментарий «not needed in Phase 1».
- [ ] `django==5.2.*` (frozen V1.2), не `>=5.0` или другое.
- [ ] `procrastinate[django]` присутствует (NEVER Celery — verify).
- [ ] `django-cryptography-django5` присутствует (NOT pgcrypto).
- [ ] `import-linter` присутствует.
- [ ] Никаких **запрещённых** dependencies (Stripe, Clerk SDK, supabase, vercel-cli, redis, celery).
- [ ] Coverage threshold ≤ 70% для Phase 1 (выше — слишком агрессивно для bootstrap).
- [ ] `[tool.pytest.ini_options].markers` содержит минимум `rls`, `outbox`, `compliance`.
- [ ] Email author = placeholder `[? founder_email]`, не выдуманный.

### 6.3. `.env.example`

- [ ] Все 14 групп `# === ... ===` соответствуют группам стека из `CLAUDE.md` строки 47-69.
- [ ] Минимум 8 placeholders `__CHANGE_ME__` / `__from_*__` (security gate — не должно быть real secrets).
- [ ] `DATABASE_URL_DIRECT` или эквивалент для bypass PgBouncer (NON-NEGOTIABLE #11).
- [ ] `DATABASE_URL_ADMIN` для act_admin (BYPASSRLS) роли.
- [ ] `YANDEX_LOCKBOX_KEY_ID` и `PII_HMAC_SECRET` (ADR-014).
- [ ] `TELEGRAM_BOT_TOKEN` имеет комментарий про обязательность ст. 12 consent (NON-NEGOTIABLE #9).
- [ ] Никаких real secrets / API keys в значениях.
- [ ] Никаких US-managed services (Postmark/SendGrid/Twilio как primary).
- [ ] Max 100 строк.

### 6.4. `.importlinter` — САМЫЙ КРИТИЧЕСКИЙ ARTEFACT

- [ ] Минимум 17 contracts (1 на `.raw()` + 16 per-BC), идеально 18 (+ cross-context outbox).
- [ ] Каждый contract имеет шапку-комментарий с источником (NON-NEGOTIABLE #X / ADR-Y / `CLAUDE.md` строка Z).
- [ ] **CONTRACT 0 (no-raw-sql)** перечисляет все 16 BC в `source_modules` и разрешает `apps.core.rls.*` в `ignore_imports`.
- [ ] **CONTRACT 1 (identity_auth isolation)** запрещает импорты из всех 15 других BC.
- [ ] Все 16 BC из `ARCHITECTURE.md` строки 52-71 присутствуют в качестве `source_modules` хотя бы 1 contract.
- [ ] **CONTRACT 17 (cross-context outbox, ADR-016)** запрещает прямые импорты `*.services` из notifications/analytics/discovery для events/rsvp/ratings/contacts_sharing.
- [ ] **НЕТ** контракта, который разрешает прямой импорт `apps.X.models` или `apps.X.services` из другого BC (только через `apps.X.contracts`).
- [ ] Парсится синтаксически (по структуре INI; `lint-imports --check-cache` пройдёт когда BC реально появятся).

### 6.5. `docs/pilot-day-N-template.md`

- [ ] Все 7 метрик из PDF V1.3 секции 17.4 присутствуют в таблице (Accept-Rate, rework, time_per_feature, import_linter_violations, n_plus_one_detected, rls_violations, i18n_missing_keys).
- [ ] Все 10 Risk checks из PDF V1.3 секции 21 присутствуют в таблице.
- [ ] Заголовок ссылается на **ADR-007** (не ADR-005) как stack commit decision gate.
- [ ] Categories Claude errors log минимум 5 (`hallucinated_import`, `n_plus_one`, `rls_violation`, `i18n_missing`, `module_boundary`).
- [ ] Max 100 строк.

### 6.6. `.claude/skills/write-rls-policy/SKILL.md`

- [ ] YAML frontmatter валидный, содержит `name`, `description`, `allowed-tools`.
- [ ] `description` начинается с глагола (Anthropic skill convention: «Writes a ...», «Emits a ...»).
- [ ] **FORCE ROW LEVEL SECURITY** упомянут минимум 2× (в template + verbatim example).
- [ ] **RESTRICTIVE `default_deny`** упомянут минимум 2×.
- [ ] **`(select current_setting(...))` обёртка** упомянута как обязательная (perf оптимизация из pganalyze).
- [ ] Минимум 2 verbatim примера из Level C (identity_auth + rsvp).
- [ ] Минимум 5 pitfalls.
- [ ] Команда миграции содержит `PG_BOUNCER_HOST=""` ИЛИ `make migrate-direct` (NON-NEGOTIABLE #11).
- [ ] Когда NOT to use — явно перечислено (справочники, public catalogs).
- [ ] Max 200 строк.

### 6.7. `.claude/skills/outbox-event/SKILL.md`

- [ ] YAML frontmatter валидный.
- [ ] **ADR-016** упомянут минимум 2×.
- [ ] **`transaction.atomic()`** упомянут минимум 1× и явно показан в Python примере.
- [ ] Verbatim Python пример publisher + subscriber + test (минимум 3 code blocks).
- [ ] Event_type naming convention указан (`<EntityAction>` PascalCase).
- [ ] Idempotency через `event_id` как dedupe key — упомянут.
- [ ] Pitfalls: «НЕ использовать Django signals» — явно есть.
- [ ] **Pitfall про cross-border consent для Telegram (NON-NEGOTIABLE #9)** — должен быть, потому что subscribers могут эмитить в Telegram Bot.
- [ ] When NOT to use — явно перечислено.
- [ ] Max 150 строк.

### 6.8. `docs/jtbd-bc-mapping.md`

- [ ] Все 8 JTBD (JTBD-1..8) присутствуют в таблице mapping.
- [ ] Все 16 BC хотя бы 1× упомянуты в supporting BC колонке.
- [ ] **JTBD-2 = wedge primary** явно выделен.
- [ ] Wedge focus раздел перечисляет MVP-минимум BC для JTBD-2 (минимум 6 BC).
- [ ] Monetization mapping присутствует (4 слоя).
- [ ] Никаких новых JTBD изобретений (только JTBD-1..8 verbatim из PRODUCT.md).
- [ ] Max 100 строк.

### 6.9. `docs/risk-register.md`

- [ ] 4 категории: Strategic / Operational / Compliance / Technical.
- [ ] Минимум 4 риска в Strategic.
- [ ] Минимум 5 рисков в Operational.
- [ ] Минимум 5 рисков в Compliance.
- [ ] **Все 10 Technical Risk checks (T1-T10)** из PDF V1.3 секции 21 присутствуют с Pass/Fix/Pivot criteria.
- [ ] Каждый риск имеет (P, I, Trigger, Mitigation, Источник).
- [ ] Decision gate явный: при Pivot хотя бы по одному пункту — pilot failed.
- [ ] Ссылка на ADR-007 (не ADR-005) как stack commit decision.
- [ ] Triggers пересмотра реестра присутствуют.
- [ ] Max 100 строк.

### 6.10. `apps/identity_auth/CLAUDE.md`

- [ ] Max 80 строк (per Anthropic guidelines для per-context).
- [ ] Все 7 entities из PDF V1.3 секции 20.1 присутствуют (User, Session, MagicLinkToken, OAuthProvider, OAuthIdentity, PasskeyCredential, ConsentRecord).
- [ ] Все 7 приоритетов аутентификации из PDF V1.1 раздел 3.5 присутствуют.
- [ ] **NON-NEGOTIABLE #6** (POST после явного клика) — явно упомянут в pitfalls.
- [ ] **NON-NEGOTIABLE #9** (ст. 12 consent для Telegram) — явно упомянут.
- [ ] **NON-NEGOTIABLE #11** (RLS + PgBouncer) — упомянут хотя бы через ссылку на skill write-rls-policy.
- [ ] Cross-context dependencies явно: identity_auth ничего не импортирует (root BC), exposes contracts.
- [ ] Emits via Outbox список не пустой (минимум 3 event_type).
- [ ] Структура соответствует: Context · Entities · Conventions · Cross-context · Pitfalls.

### 6.11. `docker-compose.yml` + `Makefile` + `infra/postgres/init.sql`

- [ ] `docker-compose.yml`: PostgreSQL 17, healthcheck, no Redis / no Meilisearch.
- [ ] `docker-compose.yml`: max 60 строк.
- [ ] `Makefile`: target `migrate-direct` с `PG_BOUNCER_HOST=""` присутствует (NON-NEGOTIABLE #11).
- [ ] `Makefile`: targets `test-rls` и `test-outbox` присутствуют.
- [ ] `Makefile`: target `rls-check` присутствует (даже как TODO).
- [ ] `Makefile`: max 80 строк.
- [ ] `init.sql`: все 4 required extensions ADR-006 (pgcrypto, btree_gist, pg_trgm, unaccent) присутствуют.
- [ ] `init.sql`: pg_uuidv7 закомментирован с явным объяснением (Yandex Managed allowlist check).
- [ ] `init.sql`: комментарий про act_admin role (BYPASSRLS) с упоминанием audit_log_pii_access.

-----

## 7. Cross-cutting checks (между файлами)

### 7.1. ADR-005 ↔ ADR-007 renumbering consistency

- Найти ВСЕ упоминания «ADR-005» во всех 13 артефактах. Каждое должно быть в контексте «отвергнут зарубежный managed-стек» (Stripe / Clerk / Convex / Vercel managed) ИЛИ в historical note про PDF V1.3.
- Найти ВСЕ упоминания «ADR-007». Каждое должно быть в контексте «stack commit (Django + Next.js)».
- Любое смешение — Critical finding.

### 7.2. 11 NON-NEGOTIABLE traceability

Построить таблицу «NN # → артефакт, где есть enforcement». Каждый NN из 11 должен иметь как минимум одну строку. Пустые — Major findings.

Пример ожидаемой таблицы:

| NN # | Текст (краткий) | Enforcement в артефакте |
|---|---|---|
| 1 | 152-ФЗ ст. 18 (РФ localisation) | `.env.example` (RU-only ESP) + identity_auth CLAUDE.md |
| 6 | POST после явного клика | identity_auth CLAUDE.md pitfalls |
| 9 | ст. 12 consent для Telegram | identity_auth CLAUDE.md + outbox SKILL.md pitfall |
| 11 | RLS + PgBouncer | write-rls-policy SKILL.md + Makefile migrate-direct + .importlinter CONTRACT 0 |
| ... | ... | ... |

### 7.3. 16 BC coverage

- В `.importlinter` каждый из 16 BC должен быть `source_modules` хотя бы для 1 contract.
- В `jtbd-bc-mapping.md` каждый из 16 BC должен быть упомянут как Primary или Supporting хотя бы для 1 JTBD ИЛИ явно отмечен как deferred / placeholder.

### 7.4. 8 JTBD coverage

- В `jtbd-bc-mapping.md` все 8 JTBD из `PRODUCT.md` строки 111-118 присутствуют.

### 7.5. Эпистемическая разметка

- Найти все vague утверждения (содержащие «обычно», «как правило», «может быть», «вероятно», «ожидается») без `[Г]` или `[?]`. Это Minor findings.

### 7.6. Stack consistency

- Найти любые упоминания запрещённых technologies: Stripe, Clerk, Convex, Vercel managed, Heroku, AWS managed, Redis primary, Celery, Elasticsearch, Meilisearch, Postmark, SendGrid, Twilio primary.
- Каждое упоминание = Critical finding **если** в позитивном контексте (рекомендация). Допустимо в negative context (rejected, отвергнут).

### 7.7. Renumbering ADR-005↔007 в комментариях `.importlinter`

- Все ADR-references в комментариях `.importlinter` должны указывать корректные номера. Особенно: ADR-001 (modular monolith), ADR-006 (RLS), ADR-016 (Outbox).

-----

## 8. Hallucination risk analysis

Для каждого артефакта оценить «hallucination surface»:

- **Открытые placeholders без явного marker.** Пример: «email = founder@act.app» (выдуманный) vs «email = `[? founder_email]`» (явный placeholder). Первое — Critical hallucination vector.
- **Vague версии пакетов.** Пример: `django>=4.0` (drift к новой major) vs `django==5.2.*` (locked LTS). Первое — Major.
- **Open-ended формулировки в SKILL.md.** Пример: «Add appropriate RLS policies» (что значит appropriate?) vs «Add `FORCE ROW LEVEL SECURITY` + RESTRICTIVE default_deny». Первое — Major.
- **Conditional language без явного criteria.** Пример: «Если нужно — добавьте Redis» (когда нужно?) vs «При > 1000 jobs/min — рассмотреть Redis». Первое — Minor (но в SKILL.md — Major).

Для каждого finding указать: место в артефакте → severity → почему это hallucination vector → diff fix.

-----

## 9. Bloat analysis

Для каждого артефакта оценить signal/noise ratio:

- **Дублирование** между артефактами (одна и та же info в `CHANGELOG.md` и `risk-register.md` — OK; одна и та же ADR-цитата в 5 файлах — bloat).
- **Тавтологические комментарии.** Пример: `# Set DEBUG to true for debug mode` — bloat.
- **Long preambles before code blocks.** SKILL.md должен быть actionable; > 30% prose перед первым code block — bloat.
- **Длинные explanations того, что уже есть в `CLAUDE.md` / `ARCHITECTURE.md`.** Артефакт должен ссылаться, а не пересказывать. Пересказ > 3 предложений — bloat.

-----

## 10. Output format — структура `audit-report-iteration-4.md`

```markdown
# Audit Report — Iteration 4 Artifacts

## 1. Executive summary
- Overall verdict: Ready / Fix Required / Reject
- Composite score: XX / 30 average across 13 артефактов
- Top-3 Critical findings (если есть)
- Top-5 Major findings
- Готовность к коммиту: % артефактов с Pass

## 2. Per-artifact deep audit

### 2.1. docs/CHANGELOG.md
**Composite: XX / 30** (D1: _/5, D2: _/5, D3: _/5, D4: _/5, D5: _/5, D6: _/5)
**Verdict: Ready / Fix / Reject**

**DoD checklist:**
- [✓/✗] ADR-005 renamed-section
- [✓/✗] ADR-007 renamed-section
- ... (все 7 пунктов из § 6.1)

**Findings:**
- 🔴 **Critical #1.** [verbatim из артефакта] → diff fix.
- 🟡 **Major #1.** ...
- ⚪ **Minor #1.** ...

(аналогично для 2.2 ... 2.13)

## 3. Cross-cutting findings

### 3.1. ADR-005 / ADR-007 renumbering consistency
Все обнаруженные упоминания + verdict.

### 3.2. 11 NON-NEGOTIABLE traceability table
| NN # | Текст | Где enforcement |
| ... |

### 3.3. 16 BC coverage
Таблица coverage + missing BC.

### 3.4. 8 JTBD coverage
Таблица coverage.

### 3.5. Stack consistency
Все обнаруженные упоминания запрещённых technologies.

## 4. Compliance / 152-ФЗ / NON-NEGOTIABLE coverage

Детальный pass per NN.

## 5. Hallucination risk analysis

Per артефакт — список hallucination vectors с severity.

## 6. Bloat analysis

Per артефакт — % bloat estimate.

## 7. Final verdict

| Артефакт | Score | DoD | Verdict |
|---|---|---|---|
| docs/CHANGELOG.md | 28/30 | 7/7 | Ready |
| ... | ... | ... | ... |

**Общий gate:** Pass / Fix Required перед коммитом / Reject.

## 8. Recommended diff-style fixes (готовы к применению)

Группировка fixes по артефакту, в порядке severity. Каждая fix:
```diff
--- a/<artefact>
+++ b/<artefact>
@@ context @@
- старый текст
+ новый текст
```

С 1-2 строк обоснования.

## 9. Next steps

- Применить Critical fixes ДО коммита (блокер).
- Применить Major fixes до Iteration 5.
- Minor fixes — opportunistic в Iteration 5-8.
- Создать commit `chore(qa): apply audit findings from Iteration 4.5` как первый commit ветки `chore/iteration-4-scaffolding` ПЕРЕД остальными 12 commits.
```

-----

## 11. Защита от типовых ошибок аудитора

1. **«Approve with comments» — запрещено.** Только бинарный gate Pass / Fix / Reject per артефакт.
2. **«Everything looks good» отчёт — запрещён.** Red-team mindset: default = найти проблему. Если артефакт реально 30/30 — обоснование почему.
3. **Галлюцинация ADR-номеров.** Перед каждой ссылкой на ADR-X проверить в `ARCHITECTURE.md` что номер существует и соответствует описанию.
4. **Галлюцинация строк `CLAUDE.md`.** Перед ссылкой «строка X» проверить через `view` с явным `view_range`.
5. **Findings без verbatim цитат.** Отклоняется. Каждое drift / inconsistency finding — verbatim из source + verbatim из артефакта.
6. **Перепутывание severity.** Critical = блокер коммита (security, compliance, broken cross-reference). Major = надо до релиза. Minor = nice-to-have. Не раздувать Minor в Major.
7. **«Rewrite this artefact entirely»** — запрещено. Только diff-style fixes. Если артефакт реально требует полной переписки — это Reject verdict.
8. **Предложение новых артефактов / новых ADR.** Запрещено. Аудит работает только с тем, что есть.
9. **Изменение архитектурных решений.** Запрещено. Если артефакт нарушает frozen стек V1.2 — это finding, не предложение обновить стек.

-----

## 12. Формат итогового ответа

После создания `audit-report-iteration-4.md` структурировать ответ в **4 секции**:

1. **Executive summary** (≤ 10 строк): overall verdict, composite score across 13, готовность к коммиту %.
2. **Critical findings table** (≤ 10 строк): топ-N Critical findings с артефактом и severity reason.
3. **DoD pass rate** (1 строка): «X / 13 артефактов прошли DoD; Y / 13 имеют Critical; Z / 13 готовы к commit без правок».
4. **Recommended action**: какие fixes применить ДО `git add` (Critical блокеры) и какие отложить до Iteration 5.

В конце — `present_files` с `audit-report-iteration-4.md`.

-----

## 13. После выполнения

Следующий шаг (рекомендация):

### 13.1. **Если Pass (все 13 артефактов Ready)** — переход к Iteration 5 (corrections-apply.md) без задержки.

### 13.2. **Если Fix Required** — применить Critical fixes из § 8 audit report (вручную или новым промтом «apply-audit-fixes»), затем повторить Iteration 4.5 audit на исправленных файлах.

### 13.3. **Если Reject (≥ 1 артефакт)** — переоткрыть Iteration 4 для проблемного артефакта; не коммитить остальные 12, пока проблемный не пройдёт.

**Цель — нулевое количество Critical findings перед первым `git add` в репозиторий Act.**

-----

*Конец промта Iteration 4.5 audit.*

-----

## Приложение — Quick checklist для founder’а перед запуском

- [ ] Открыть новую Claude.ai сессию в Project «Act».
- [ ] Убедиться, что 13 артефактов Iteration 4 доступны в `/mnt/user-data/outputs/` (или загружены).
- [ ] Прикрепить 4 файла репозитория к сессии (READ-ONLY источник).
- [ ] Убедиться, что 3 PDF в Project Knowledge.
- [ ] Включить tools: `view`, `create_file`, `present_files`, `project_knowledge_search`.
- [ ] Скопировать этот промт целиком в первое сообщение.
- [ ] Ожидать ~30-45 минут (модель проходит 13 артефактов × 6 dimensions + cross-cutting).
- [ ] После завершения — открыть `audit-report-iteration-4.md` и применить Critical fixes ДО коммита.
- [ ] Сохранить промт в Project Files как `iteration-4.5-audit.md`.
