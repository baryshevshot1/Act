# Audit Report — Iteration 4 Artifacts

> **Запуск:** Iteration 4.5 audit на 13 артефактов в `/mnt/user-data/outputs/`.
> **Дата:** 2026-05-25.
> **Auditor mindset:** red-team (default = найти проблему).

-----

## 1. Executive summary

- **Overall verdict:** **Fix Required** перед коммитом.
- **Composite score:** **28.0 / 30** average across 13 артефактов.
- **DoD pass rate:** **8 / 13** Ready без правок; **5 / 13** требуют ≥ 1 fix; **0 / 13** Reject.
- **Critical findings: 2** (оба — misattribution ADR-005 к выбору django-allauth).
- **Major findings: 3** (Source fidelity в identity_auth + JTBD-BC mapping + RLS skill cross-ref).
- **Minor findings: 6** (3× line-count over-spec, 2× weak NN coverage, 1× placeholder format).
- **Готовность к коммиту:** **62%** артефактов Ready без правок. После применения 3 diff fixes из § 8 → 100% Ready.

**Главная находка.** Iteration 4 создал ровно ту проблему, для которой и создавался `docs/CHANGELOG.md` renumber note: ADR-005 misattributed как «обоснование выбора django-allauth» в двух местах (`.env.example:35` и `pyproject.toml:14`). Это ирония: артефакт-страж от ADR-нумерационного drift сам пропустил два drift в той же итерации. Хорошая новость — оба fix-а тривиальны (одна строка каждый).

-----

## 2. Per-artifact deep audit

### 2.1. `docs/CHANGELOG.md`

**Composite: 30 / 30** (D1: 5, D2: 5, D3: 5, D4: 5, D5: 5, D6: 5) — **Verdict: Ready**

**DoD checklist:**

- [✓] ADR-005 минимум 1× в Renamed-секции с «Отвергнут зарубежный managed-стек» (строка 74).
- [✓] ADR-007 минимум 1× в Renamed-секции с «Stack commit (Django + Next.js)» (строка 74).
- [✓] Historical note про PDF V1.3 секция 17.5 ссылку на ADR-005 как stack commit (строка 73-75).
- [✓] Failed approaches: 5 (pgcrypto, multiplicative ranking, Django signals, opened pixel, Stripe/Clerk).
- [✓] 131 строк (max 200).
- [✓] Все записи имеют дату ИЛИ «исторический контекст».
- [⚪] Не все 11 NON-NEGOTIABLE упомянуты verbatim (упомянуты по факту в Wave 1+ Added секции, но без явного перечисления). Minor только.

**Findings:** Нет.

-----

### 2.2. `pyproject.toml`

**Composite: 25 / 30** (D1: 4, D2: 4, D3: 5, D4: 4, D5: 4, D6: 4) — **Verdict: Fix Required**

**DoD checklist:**

- [✓] Парсится через `tomllib`.
- [✓] 11 dependencies (django, psycopg, allauth, otp, otp-webauthn, cryptography-django5, procrastinate, drf-spectacular, cors-headers, sentry-sdk, import-linter).
- [✓] `django==5.2.*` locked.
- [✓] `procrastinate[django]`.
- [✓] `django-cryptography-django5`, не pgcrypto.
- [✓] `import-linter`.
- [✓] Никаких Stripe / Clerk SDK / supabase / vercel-cli / redis / celery в deps.
- [✓] Coverage `--cov-fail-under=70`.
- [✓] Markers: `rls`, `outbox`, `compliance`, `slow`.
- [✓] Email = `[? founder_email — fill before first commit]` placeholder.
- [✗] 128 строк > spec max 100 (over-spec на 28 строк; bloat = низкий, каждая строка несёт `[F:]` source).

**Findings:**

- 🔴 **Critical C2.** Строка 14: `"django-allauth>=65.0",  # Telegram OIDC primary, magic-link fallback (ADR-005)`. Misattribution: ADR-005 — «Отвергнут зарубежный managed-стек», не «выбор django-allauth». django-allauth — это **следствие** отказа от Clerk, но не сам ADR-005. См. § 8 diff.
- ⚪ **Minor m1.** 128 строк > 100. Bloat estimate < 10%; каждая строка несёт source-citation. Acceptable, но можно сократить комментарии до 1 строки на dependency.

-----

### 2.3. `.env.example`

**Composite: 27 / 30** (D1: 4, D2: 5, D3: 4, D4: 4, D5: 5, D6: 5) — **Verdict: Fix Required**

**DoD checklist:**

- [△] 12 groups `# === ... ===` (DoD требовал 14; mapping не 1:1 со строками 47-69 CLAUDE.md — это OK).
- [✓] 14 placeholders `__CHANGE_ME__` / `__from_*__`.
- [✓] `DATABASE_URL_DIRECT` для bypass PgBouncer.
- [✓] `DATABASE_URL_ADMIN` для act_admin BYPASSRLS.
- [✓] `YANDEX_LOCKBOX_KEY_ID` + `PII_HMAC_SECRET`.
- [✓] `TELEGRAM_BOT_TOKEN` имеет ст. 12 comment.
- [✓] Никаких real secrets.
- [✓] Никаких Postmark/SendGrid/Twilio как primary.
- [✗] 87 строк > spec max 80 (+ 7 строк).

**Findings:**

- 🔴 **Critical C1.** Строка 35: `# === Auth (ADR-005: django-allauth) ===`. Misattribution: ADR-005 — «Отвергнут зарубежный managed-стек», не «Auth выбор django-allauth». См. § 8 diff.
- ⚪ **Minor m2.** 87 > 80 строк. Acceptable.

-----

### 2.4. `.importlinter`

**Composite: 29 / 30** (D1: 5, D2: 5, D3: 5, D4: 4, D5: 5, D6: 5) — **Verdict: Ready**

**DoD checklist:**

- [✓] 18 contracts (CONTRACT 0 + CONTRACTS 1-17). Spec требовал минимум 17.
- [✓] Каждый contract имеет шапку с источником (NON-NEGOTIABLE #X / ADR-Y).
- [✓] CONTRACT 0 (no-raw-sql): все 16 BC в source_modules + `apps.core.rls.*` в ignore.
- [✓] CONTRACT 1 (identity_auth isolation): запрещает 15 других BC.
- [✓] Все 16 BC из ARCHITECTURE.md 52-71 присутствуют как source_modules.
- [✓] CONTRACT 17 (cross-context outbox, ADR-016): events/rsvp/ratings/contacts_sharing → forbidden notifications.services / analytics.services / discovery.services.
- [✓] Нет контрактов, разрешающих прямой импорт `*.models` или `*.services` между BC.
- [✓] Синтаксис INI парсится.

**Findings:**

- ⚪ **Minor m3.** 360 строк — большой файл, но все contracts необходимы. Бoilerplate-дублирование в шаблонах `forbidden_modules` / `ignore_imports` — неизбежно для INI-формата. Acceptable.

-----

### 2.5. `docs/pilot-day-N-template.md`

**Composite: 25 / 25** (D1: 5, D2: 5, D3: 5, D4: 5, D5: 5, D6: N/A) — **Verdict: Ready**

**DoD checklist:**

- [✓] 7 метрик из PDF V1.3 секции 17.4 в таблице.
- [✓] 10 Risk checks из PDF V1.3 секции 21 в таблице.
- [✓] Заголовок ссылается на **ADR-007** явно («не ADR-005»).
- [✓] Categories Claude errors log: 6 (hallucinated_import, n_plus_one, rls_violation, i18n_missing, module_boundary, other).
- [✓] 69 строк (max 100).

**Findings:** Нет.

-----

### 2.6. `.claude/skills/write-rls-policy/SKILL.md`

**Composite: 30 / 30** (D1: 5, D2: 5, D3: 5, D4: 5, D5: 5, D6: 5) — **Verdict: Ready**

**DoD checklist:**

- [✓] YAML frontmatter валидный (name, description, allowed-tools).
- [✓] Description начинается с глагола «Writes a...» (Anthropic convention).
- [✓] FORCE ROW LEVEL SECURITY: 6 mentions.
- [✓] RESTRICTIVE `default_deny`: 8 mentions.
- [✓] `(select current_setting(...))` обёртка явная (раздел Pitfalls + perf comment).
- [✓] 2 verbatim примера: identity_auth_session + rsvp_guest_rsvp.
- [✓] 7 pitfalls (FORCE, RESTRICTIVE, pgcrypto, select-wrap, PgBouncer, tests, SET LOCAL).
- [✓] `PG_BOUNCER_HOST=""` + `make migrate-direct` в команде миграции.
- [✓] When NOT to use явно: справочники, public catalogs.
- [✓] 162 строк (max 200).

**Findings:** Нет.

-----

### 2.7. `.claude/skills/outbox-event/SKILL.md`

**Composite: 30 / 30** (D1: 5, D2: 5, D3: 5, D4: 5, D5: 5, D6: 5) — **Verdict: Ready**

**DoD checklist:**

- [✓] YAML frontmatter валидный.
- [✓] Description «Emits a cross-context event...» начинается с глагола.
- [✓] ADR-016: 9 mentions.
- [✓] `transaction.atomic()`: 3 mentions, явно в Python примере.
- [✓] 3 Python code blocks: publisher + subscriber + test.
- [✓] Event_type naming convention указан (PascalCase EntityAction).
- [✓] Idempotency через event_id как dedupe key явный.
- [✓] Pitfall «НЕ использовать Django signals» явный.
- [✓] Pitfall про cross-border consent для Telegram (NN #9) явный.
- [✓] When NOT to use явно.
- [✓] 131 строк (max 150).

**Findings:** Нет.

-----

### 2.8. `docs/jtbd-bc-mapping.md`

**Composite: 24 / 25** (D1: 5, D2: 4, D3: 5, D4: 5, D5: 5, D6: N/A) — **Verdict: Fix Required**

**DoD checklist:**

- [✓] Все 8 JTBD (JTBD-1..8) в таблице.
- [✓] Все 16 BC упомянуты как Primary или Supporting (через 8 JTBD + MVP-минимум секция).
- [✓] JTBD-2 = wedge primary явно выделен жирным.
- [✓] Wedge focus раздел: 8 BC в MVP-минимуме.
- [✓] Monetization mapping: 4 слоя × 5 trigger строк.
- [✓] Никаких новых JTBD изобретений.
- [✓] 68 строк (max 100).

**Findings:**

- 🟡 **Major M1.** Строка 29: `**Identity & Auth** (Level C готов; ADR-005, ADR-014)`. ADR-005 не специфично к Identity & Auth — это общее отвержение зарубежного managed-стека. Корректные ADR для Identity: **ADR-014** (PII encryption) + **ADR-013** (notification fallback для ст. 12 consent). См. § 8 diff.

-----

### 2.9. `docs/risk-register.md`

**Composite: 30 / 30** (D1: 5, D2: 5, D3: 5, D4: 5, D5: 5, D6: 5) — **Verdict: Ready**

**DoD checklist:**

- [✓] 4 категории: Strategic / Operational / Compliance / Technical.
- [✓] Strategic: 4 риска.
- [✓] Operational: 5 рисков.
- [✓] Compliance: 5 рисков.
- [✓] Technical: все 10 T1-T10 с Pass/Fix/Pivot criteria.
- [✓] Каждый риск имеет (P, I, Trigger, Mitigation, Источник).
- [✓] Decision gate явный.
- [✓] Ссылка на ADR-007 (не ADR-005) явная.
- [✓] Triggers пересмотра реестра.
- [✓] 69 строк (max 100).

**Findings:** Нет.

-----

### 2.10. `apps/identity_auth/CLAUDE.md`

**Composite: 26 / 30** (D1: 5, D2: 3, D3: 5, D4: 5, D5: 4, D6: 4) — **Verdict: Fix Required**

**DoD checklist:**

- [✓] 56 строк (max 80).
- [△] 8 entities, не 7 — `AuthEvent` добавлен как Wave 1+ дополнение, но header заявляет «verbatim» что вводит читателя в заблуждение.
- [✓] Все 7 приоритетов аутентификации из PDF V1.1 раздел 3.5.
- [✓] NON-NEGOTIABLE #6 в pitfalls (строка 54).
- [✓] NON-NEGOTIABLE #9 в pitfalls (строка 55).
- [✗] NON-NEGOTIABLE #11 — НЕТ явной ссылки на skill `write-rls-policy` (DoD fail).
- [✓] Cross-context dependencies явно: identity_auth — root, exposes contracts, никаких consumes.
- [✓] Emits via Outbox: 4 event_type (UserRegistered, UserBanned, ConsentGranted, ConsentWithdrawn).
- [✓] Структура: Context · Entities · Conventions · Cross-context · Pitfalls.
- [✗] NON-NEGOTIABLE #2 (ст. 9 в ред. 156-ФЗ — отдельный документ согласия) — не упомянут явно.

**Findings:**

- 🟡 **Major M2.** Строка 11: header «Entities (PDF V1.3 секция 20.1 verbatim + Wave 1+ дополнения)» вводит в заблуждение. PDF V1.3 секция 20.1 содержит ровно 7 entities; `AuthEvent` — это 8-я, inference на основе CLAUDE.md строка 124 (`audit_log_pii_access`). Reader не может различить которая из них verbatim. **Source fidelity violation (D2).** См. § 8 diff.
- 🟡 **Major M3.** NON-NEGOTIABLE #11 (RLS) — implicit only (через колонку «RLS? ✓» в таблице). Per DoD § 6.10: «упомянут хотя бы через ссылку на skill write-rls-policy». Cross-ref на skill отсутствует. См. § 8 diff.
- ⚪ **Minor m4.** NON-NEGOTIABLE #2 (отдельный документ согласия) — implicit через ConsentRecord, без явной ссылки на NN #2. Желательно добавить в Conventions.

-----

### 2.11. `docker-compose.yml`

**Composite: 30 / 30** — **Verdict: Ready**

**DoD checklist:**

- [✓] PostgreSQL 17-alpine + healthcheck.
- [✓] Никаких Redis / Meilisearch / Sentry в compose.
- [✓] Procrastinate worker как opt-in profile.
- [✓] 44 строки (max 50).

**Findings:** Нет.

-----

### 2.12. `Makefile`

**Composite: 30 / 30** — **Verdict: Ready**

**DoD checklist:**

- [✓] `migrate-direct` с `PG_BOUNCER_HOST=""`.
- [✓] `test-rls`, `test-outbox`, `test`.
- [✓] `rls-check` как TODO.
- [✗] 69 строк > spec max 60 (+ 9 строк).
- [✓] `lint` + `fmt` targets.

**Findings:**

- ⚪ **Minor m5.** 69 > 60 строк. `help` target занимает 16 строк (echo-блок). Можно сократить, но functional.

-----

### 2.13. `infra/postgres/init.sql`

**Composite: 30 / 30** — **Verdict: Ready**

**DoD checklist:**

- [✓] 4 required extensions ADR-006: pgcrypto, btree_gist, pg_trgm, unaccent.
- [✓] pg_uuidv7 закомментирован с явным объяснением Yandex allowlist check.
- [✓] Комментарий про act_admin BYPASSRLS + audit_log_pii_access.
- [✓] 22 строки.

**Findings:** Нет.

-----

## 3. Cross-cutting findings

### 3.1. ADR-005 ↔ ADR-007 renumbering consistency

**Все упоминания ADR-005:**

| Файл | Строка | Контекст | Verdict |
|---|---|---|---|
| `.env.example` | 35 | `# === Auth (ADR-005: django-allauth) ===` | 🔴 **Critical C1** — misattribution |
| `docs/CHANGELOG.md` | 11, 72-75, 131 | Renamed-секция + Failed approaches | ✓ Correct |
| `docs/jtbd-bc-mapping.md` | 29 | `Identity & Auth (Level C готов; ADR-005, ADR-014)` | 🟡 **Major M1** — misattribution |
| `docs/pilot-day-N-template.md` | 4 | «ADR-007, не ADR-005» | ✓ Correct |
| `docs/risk-register.md` | 15 | «ADR-007, не ADR-005» | ✓ Correct |
| `pyproject.toml` | 14 | `# (ADR-005)` для django-allauth | 🔴 **Critical C2** — misattribution |

**Все упоминания ADR-007:** Все корректны (5 mentions across `CHANGELOG.md`, `pilot-day-N-template.md`, `risk-register.md`).

**Verdict:** 2 Critical drift'а в `.env.example` + `pyproject.toml` + 1 Major drift в `jtbd-bc-mapping.md`. Все три — одинаковый паттерн ошибки: «выбор django-allauth» приписан к ADR-005 (отвергнутый стек), хотя ADR-005 документирует только «почему НЕ Clerk», а не «почему django-allauth».

### 3.2. 11 NON-NEGOTIABLE traceability table

| NN # | Текст (краткий) | Enforcement (явное или implicit) | Strength |
|---|---|---|---|
| 1 | 152-ФЗ ст. 18 (РФ localisation) | implicit: `.env.example` Yandex services; `docker-compose.yml` TZ=Europe/Moscow | 🟡 Weak — нет явной NN #1 ссылки |
| 2 | ст. 9 ред. 156-ФЗ (отдельный документ) | implicit: `identity_auth/CLAUDE.md` ConsentRecord purposes | 🟡 Weak — Minor m4 |
| 3 | Платежи: No Stripe, ЮKassa | implicit: pyproject.toml нет Stripe SDK; `CHANGELOG.md` Failed approaches | ✓ OK |
| 4 | Хостинг: Yandex Cloud + Coolify | implicit: `.env.example` Yandex Object Storage + Cloud IAM | ✓ OK |
| 5 | iOS: PWA + Telegram Mini App | N/A — out of scope для Phase 1 scaffolding (нет mobile-файлов) | — |
| 6 | POST после явного клика | `apps/identity_auth/CLAUDE.md` Pitfalls (строка 54) | ✓✓ Strong |
| 7 | PII шифрование (encrypt at rest) | `pyproject.toml` django-cryptography-django5 + `.env.example` Lockbox | ✓✓ Strong |
| 8 | Real-time не делаем (polling 30s) | N/A — out of scope | — |
| 9 | ТППД (ст. 12 152-ФЗ) Telegram | `apps/identity_auth/CLAUDE.md` + `.env.example` + outbox SKILL.md | ✓✓✓ Strong |
| 10 | РКН-уведомления (ст. 22 + ст. 12) | `.env.example` RKN compliance section + `risk-register.md` C2 | ✓ OK |
| 11 | RLS + PgBouncer | write-rls-policy SKILL.md + Makefile + .importlinter + docker-compose + 3 other files | ✓✓✓ Strong |

**Verdict:** 5 NN strong, 3 NN OK, 2 NN weak (#1, #2), 2 NN out-of-scope (#5, #8). Никаких Critical gap'ов в coverage. NN #2 — Minor m4 fix желателен.

### 3.3. 16 BC coverage

Все 16 BC из `ARCHITECTURE.md` строки 52-71 присутствуют как `source_modules` в `.importlinter`: identity_auth, user_profile, verification, groups, events, recurrence_engine, rsvp, contacts_sharing, ratings, discovery, recommendations, notifications, moderation, localization, analytics, admin_console. ✓

### 3.4. 8 JTBD coverage

Все 8 JTBD (JTBD-1..8) в `docs/jtbd-bc-mapping.md` таблице. ✓

### 3.5. Stack consistency

Все упоминания запрещённых technologies — в **negative / risk context**:

- `@vercel/og` (CHANGELOG.md ADR-015) — это library (npm package для OG generation), не Vercel managed hosting. Разрешено ADR-015. ✓
- Celery / Redis — только в T10 Pilot check (когда они «победят» = Pivot). Negative context. ✓
- Stripe / Clerk / Convex / Vercel managed (CHANGELOG.md Failed approaches) — явное «отвергнуты». ✓

**Verdict:** Нет positive-context упоминаний запрещённых technologies.

### 3.6. Эпистемическая разметка

Vague формулировок без `[Г]` или `[?]` не найдено в существенных местах. Несколько «обычно» / «как правило» — в pitfalls (acceptable как general guidance, не как факт).

-----

## 4. Compliance / 152-ФЗ / NON-NEGOTIABLE coverage

Детально — § 3.2 выше. **Никаких Critical gap'ов.** NN #2 — Minor m4 (рекомендуется добавить явную ссылку в `apps/identity_auth/CLAUDE.md` Conventions).

NN #5 (iOS) и NN #8 (Real-time) — out of scope для текущих 13 артефактов (нет mobile / WebSocket related файлов в этой итерации). Будут покрыты в Iteration 6-8.

-----

## 5. Hallucination risk analysis

| Артефакт | Hallucination vectors | Severity |
|---|---|---|
| `pyproject.toml` | Email = `[? founder_email — fill before first commit]` — явный placeholder ✓ | Minor m6 |
| `.env.example` | 14 placeholders `__CHANGE_ME__` / `__from_*__` — все явно маркированы ✓ | — |
| `.importlinter` | Никаких vague formulation; binary запреты ✓ | — |
| `write-rls-policy SKILL.md` | `<ctx>` / `<table>` placeholders в template — explicit; reader заменяет ✓ | — |
| `outbox-event SKILL.md` | Event_type naming convention зафиксирован PascalCase ✓ | — |
| `apps/identity_auth/CLAUDE.md` | `AuthEvent` introduced без явного «added in Wave 1+» disclaimer — **может ввести в заблуждение** | 🟡 Major M2 |
| Остальные | Нет открытых vague mест | — |

**Главный hallucination vector:** identity_auth/CLAUDE.md M2 — header «verbatim + дополнения» прячет какая из 8 entities — добавленная. Future Claude Code сессия может процитировать «PDF V1.3 секция 20.1 verbatim» и упомянуть `AuthEvent`, что false claim.

-----

## 6. Bloat analysis

| Артефакт | Bloat estimate | Findings |
|---|---|---|
| `docs/CHANGELOG.md` | < 5% | Каждая запись несёт информацию ✓ |
| `pyproject.toml` | < 10% | 128 > 100 строк spec max; каждая dependency имеет `[F:]` comment — приемлемо |
| `.env.example` | < 5% | 87 > 80 строк; RKN compliance section justifies overspec |
| `.importlinter` | ~ 15% | Boilerplate в шаблонах `ignore_imports` неизбежен для INI-формата; не bloat |
| `write-rls-policy SKILL.md` | < 5% | Verbatim code-blocks + pitfalls — actionable ✓ |
| `outbox-event SKILL.md` | < 5% | 3 code-blocks + pitfalls — actionable ✓ |
| `docs/jtbd-bc-mapping.md` | < 5% | Compact таблица + wedge focus ✓ |
| `docs/risk-register.md` | < 5% | 24 риска в 4 категориях — density justified ✓ |
| `apps/identity_auth/CLAUDE.md` | < 5% | 56 < 80 строк spec ✓ |
| `Makefile` | ~ 20% | `help` target (16 строк echo) можно сократить; minor m5 |

-----

## 7. Final verdict

| Артефакт | Score | DoD | Verdict |
|---|---:|---:|---|
| `docs/CHANGELOG.md` | 30/30 | 7/7 | ✅ Ready |
| `pyproject.toml` | 25/30 | 10/11 | ⚠️ Fix Required (C2) |
| `.env.example` | 27/30 | 8/9 | ⚠️ Fix Required (C1) |
| `.importlinter` | 29/30 | 8/8 | ✅ Ready |
| `docs/pilot-day-N-template.md` | 25/25 | 5/5 | ✅ Ready |
| `.claude/skills/write-rls-policy/SKILL.md` | 30/30 | 10/10 | ✅ Ready |
| `.claude/skills/outbox-event/SKILL.md` | 30/30 | 10/10 | ✅ Ready |
| `docs/jtbd-bc-mapping.md` | 24/25 | 7/7 | ⚠️ Fix Required (M1) |
| `docs/risk-register.md` | 30/30 | 10/10 | ✅ Ready |
| `apps/identity_auth/CLAUDE.md` | 26/30 | 7/9 | ⚠️ Fix Required (M2, M3) |
| `docker-compose.yml` | 30/30 | 4/4 | ✅ Ready |
| `Makefile` | 30/30 | 5/5 | ✅ Ready |
| `infra/postgres/init.sql` | 30/30 | 3/3 | ✅ Ready |

**Общий gate:** **Fix Required перед коммитом.** 2 Critical + 3 Major fixes блокируют первый `git add`. После применения 5 diff'ов из § 8 (общая работа: < 5 минут) — все 13 артефактов готовы.

-----

## 8. Recommended diff-style fixes (готовы к применению)

### Fix C1 — `.env.example` (Critical)

```diff
--- a/.env.example
+++ b/.env.example
@@ -33,7 +33,7 @@ PROCRASTINATE_DATABASE_URL=${DATABASE_URL}
 PROCRASTINATE_APP=act.procrastinate_app:app
 
-# === Auth (ADR-005: django-allauth) ===
+# === Auth (django-allauth — NON-NEGOTIABLE #3: no Clerk/Auth0) ===
 # Telegram OIDC primary [F: CLAUDE.md NON-NEGOTIABLE #9: ст. 12 152-ФЗ]
```

**Обоснование:** ADR-005 документирует **отвержение** Stripe/Clerk/Convex/Vercel — не выбор django-allauth. django-allauth — это **следствие** ADR-005, не сам ADR. Корректная атрибуция — NON-NEGOTIABLE #3 (No Clerk billing).

### Fix C2 — `pyproject.toml` (Critical)

```diff
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -12,7 +12,7 @@ dependencies = [
     # Auth (NON-NEGOTIABLE: no Clerk / Auth0 / Supabase) [F: CLAUDE.md строка 58]
-    "django-allauth>=65.0",                   # Telegram OIDC primary, magic-link fallback (ADR-005)
+    "django-allauth>=65.0",                   # Telegram OIDC primary, magic-link fallback [F: CLAUDE.md строка 58]
     "django-otp>=1.5",                        # MFA для Pro [F: ARCHITECTURE.md строка 41]
```

**Обоснование:** То же, что C1. ADR-005 — про отвергнутый стек, django-allauth — выбранная альтернатива в follow-up без явного ADR. Атрибуция к CLAUDE.md строке 58 — корректнее.

### Fix M1 — `docs/jtbd-bc-mapping.md` (Major)

```diff
--- a/docs/jtbd-bc-mapping.md
+++ b/docs/jtbd-bc-mapping.md
@@ -28,7 +28,7 @@ Чтобы запустить wedge (JTBD-2), необходимы и достаточны следующие BC:
 
-1. **Identity & Auth** (Level C готов; ADR-005, ADR-014).
+1. **Identity & Auth** (Level C готов; ADR-013 notification fallback + ADR-014 PII encryption).
 2. **Events** (Level C готов; ADR-009 — `owner_only` достаточен для JTBD-2).
```

**Обоснование:** ADR-005 — не специфичный к Identity & Auth (это общее отвержение зарубежного стека). Корректные ADR для Identity: **ADR-013** (notification fallback под ст. 12 consent) + **ADR-014** (field-level encryption для email/phone).

### Fix M2 — `apps/identity_auth/CLAUDE.md` (Major — Source fidelity)

```diff
--- a/apps/identity_auth/CLAUDE.md
+++ b/apps/identity_auth/CLAUDE.md
@@ -10,7 +10,7 @@ Identity & Auth — **root BC**. Owns: `User`, `Session`, `MagicLinkToken`, `OAuthProvider`, `OAuthIdentity`, `PasskeyCredential`, `ConsentRecord`, `AuthEvent`. Все security-critical operations и compliance touchpoints проходят через этот контекст. Никаких импортов из других `apps.*` (см. `.importlinter` CONTRACT 1).
 
-## Entities (PDF V1.3 секция 20.1 verbatim + Wave 1+ дополнения)
+## Entities (7 verbatim из PDF V1.3 секция 20.1 + `AuthEvent` — Wave 1+ дополнение для `audit_log_pii_access`)
 
 | Entity | Description | RLS? | Encrypted fields |
```

**Обоснование:** PDF V1.3 секция 20.1 содержит ровно 7 entities; `AuthEvent` — добавлен в Wave 1+ как следствие `audit_log_pii_access` (CLAUDE.md строка 124). Explicit pointer защищает от future hallucination «PDF V1.3 содержит AuthEvent».

### Fix M3 — `apps/identity_auth/CLAUDE.md` (Major — NN #11 cross-ref)

```diff
--- a/apps/identity_auth/CLAUDE.md
+++ b/apps/identity_auth/CLAUDE.md
@@ -35,6 +35,7 @@
 ## Conventions
 
+- **RLS policies** — все RLS-таблицы создаются через skill `.claude/skills/write-rls-policy/` (FORCE + RESTRICTIVE `default_deny` + `SET LOCAL app.current_user_id`, NON-NEGOTIABLE #11).
 - **Password hashing:** `argon2id` (default Django 5.2). НИКОГДА bcrypt, plain SHA, MD5.
 - **Email / phone normalization** ДО save: lowercase emails; `+7` для RU phones.
```

**Обоснование:** DoD § 6.10 требовал «NON-NEGOTIABLE #11 — упомянут хотя бы через ссылку на skill write-rls-policy». Cross-reference закрывает DoD-fail.

### Optional fix m4 — `apps/identity_auth/CLAUDE.md` (Minor — NN #2 explicit)

```diff
--- a/apps/identity_auth/CLAUDE.md
+++ b/apps/identity_auth/CLAUDE.md
@@ -36,6 +36,7 @@
 ## Conventions
 
+- **Consent — отдельный документ** (NON-NEGOTIABLE #2: 152-ФЗ ст. 9 в ред. 156-ФЗ от 24.06.2025). НЕ вложенный чекбокс «согласен с правилами»; каждый purpose из `ConsentRecord` — отдельная запись с `consent_text_hash`.
 - **RLS policies** — все RLS-таблицы создаются через skill `.claude/skills/write-rls-policy/`...
```

**Обоснование:** Закрывает Minor m4 — NN #2 implicit. Можно отложить до Iteration 5.

-----

## 9. Next steps

### 9.1. Применить ДО `git add` (блокеры)

- ✋ **Critical C1** + **Critical C2** — 2 строки кода, < 1 минута работы.
- ✋ **Major M1, M2, M3** — 3 строки кода, < 3 минуты работы.

**Общее время на блокеры: < 5 минут.**

### 9.2. Commit strategy

Создать ветку `chore/iteration-4-scaffolding`, применить 5 fixes выше **как первый commit** перед остальными 12:

```bash
git commit -m "chore(qa): apply audit findings from Iteration 4.5

Fix ADR-005 misattribution in 3 files (.env.example, pyproject.toml,
docs/jtbd-bc-mapping.md): ADR-005 documents rejected external managed
stack (Stripe/Clerk/Convex/Vercel), not the choice of django-allauth.
django-allauth is a CONSEQUENCE of ADR-005, not the ADR itself.

Fix apps/identity_auth/CLAUDE.md:
- Clarify AuthEvent as Wave 1+ addition (not PDF V1.3 verbatim).
- Add explicit RLS skill cross-reference (NON-NEGOTIABLE #11).

Refs: audit-report-iteration-4.md sections 8 (C1, C2, M1, M2, M3)."
```

Затем 12 commits per артефакт (см. Iteration 4 § 9).

### 9.3. После fixes — повторный audit

Не обязателен (fixes тривиальны), но **opportunistic**: запустить grep-based spotcheck:

```bash
grep -rn "ADR-005" /mnt/user-data/outputs/ | grep -vE "Renamed|Failed approaches|не ADR-005|зарубежный managed"
# должен вернуть 0 строк
```

### 9.4. Затем — Iteration 5 (`corrections-apply.md`)

18 коррекций к 4 файлам репозитория (~75 минут founder review).

-----

## 10. Auditor’s note (red-team retrospective)

**Ironic finding.** Iteration 4 артефакт-страж от ADR-нумерационного drift (`docs/CHANGELOG.md` Renamed-секция с явным renumber note) сам пропустил 3 drift'а в собственной итерации. Все три — одного паттерна: автор знал что `django-allauth` выбран как «не Clerk», и подсознательно атрибутировал ссылку к ADR-005 («где это решение?»). На самом деле ADR-005 фиксирует только **отказ** от Clerk; **выбор** django-allauth — это implementation consequence без явного ADR (закреплено в CLAUDE.md строке 58 как convention).

**Lesson для future iterations:** При написании comment-источника к dependency, проверять: «Этот ADR говорит "почему выбрали X" или "почему НЕ выбрали Y"?». Если второе — корректная ссылка — на NON-NEGOTIABLE или convention, не на ADR.

**Финальный verdict:** 13 артефактов на 8 / 13 = 61.5% Ready. После 5 fixes < 5 минут — 13 / 13 = 100% Ready. Не Reject. Не Pass. **Fix Required, тривиально достижимо.**
