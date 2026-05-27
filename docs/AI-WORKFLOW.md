# AI-WORKFLOW.md — Как использовать Claude Code в репозитории Act

> Operational guide для founder + любых AI-ассистентов, которые работают с этим репо. Описывает 3-уровневую CLAUDE.md иерархию, skills library, prompts/ memory pattern, iteration discipline, guard rails (import-linter, RLS, NN).
> Источники: `CLAUDE.md` § Workflow при появлении задачи; Anthropic best practices [F: anthropic.com/engineering/claude-code-best-practices]; `prompts/README.md` § Anthropic Boltzmann pattern.

## Краткая модель (TL;DR)

Act — modular monolith с 16 BC, разрабатывается соло-фаундером через Claude Code (Opus 4.7 + Sonnet 4.6). AI-ассистент имеет **три уровня контекста + skills library + memory in prompts/**:

```
┌────────────────────────────────────────────────────────────────┐
│ Level 1 (always): CLAUDE.md root — stack frozen, 11 NN, conventions │
│                                                                │
│ Level 2 (on-demand per BC): backend/apps/<ctx>/CLAUDE.md      │
│   — context-specific entities, conventions, pitfalls           │
│                                                                │
│ Level 3 (matched by description): .claude/skills/<name>/SKILL.md │
│   — how-to recipes for specific operations                     │
│                                                                │
│ Memory: prompts/iteration-N-*.md — replayable iteration specs  │
│         docs/iterations/iteration-N-applied.md — what was done │
└────────────────────────────────────────────────────────────────┘
```

## 1. Три уровня CLAUDE.md иерархии

Adaptation of Anthropic Claude Code best practices [F: anthropic.com/engineering/claude-code-best-practices, April 2025, Boris Cherny].

### Level 1: Root `CLAUDE.md`

**Always loaded.** ~200 строк. Содержит:
- Frozen стек V1.2 (Django 5.2 + Next.js 16 + PostgreSQL 17 + Yandex Cloud)
- 11 NON-NEGOTIABLE (compliance + санкции + RLS + magic link POST + ...)
- Глоссарий ubiquitous language
- «Что НЕ делать» (anti-patterns)
- Workflow при появлении задачи

**Когда читать:** AI всегда читает root CLAUDE.md в начале сессии. Founder читает перед каждой новой задачей.

### Level 2: Per-context `backend/apps/<ctx>/CLAUDE.md`

**Loaded on-demand** при работе с конкретным BC. ~100 строк. Содержит:
- Context (назначение BC + scope MVP)
- Entities (verbatim из Level C)
- Conventions (NN / ADR references)
- Cross-context dependencies (Exposes / Consumes / Emits / Subscribes)
- Common pitfalls (минимум 7 «НЕ ...»)
- Skills relevant to this BC (cross-refs на `.claude/skills/`)

**Покрытие сейчас:** 6/6 для BC с готовым Level C — identity_auth, events, rsvp, contacts_sharing, recommendations, localization.

**Когда расширяется:** 10 missing BCs (verification, groups, ratings, discovery, notifications, moderation, analytics, admin_console) → Iteration 9 (post-Pilot).

### Level 3: `.claude/skills/<name>/SKILL.md`

**Matched by description** при триггер-фразах в задаче. Anthropic skills format: frontmatter (`name`, `description`, `allowed-tools`) + markdown body.

| Skill | Когда триггерится |
|---|---|
| `write-rls-policy` | «add RLS», «row level security», «tenant isolation»; создание model с user_id |
| `outbox-event` | «publish event», «emit event», «trigger downstream», cross-context side-effect |
| `recurrence-rrule` | «RRULE», «recurrence», «weekly event», «series override» |
| `guest-rsvp-merge` | «merge guest», «claim RSVP», «guest signup conversion» |
| `auth-flow` | «magic link», «Telegram OIDC», «add auth»; новый signup/login route |
| `add-translation` | «add translation», «i18n», «Russian plurals»; новая UI-строка |
| `create-migration` | «migration», «alter table», «expand-contract»; schema changes |
| `add-bounded-context` | «new BC»; добавление 17-го BC (с ADR) |
| `write-adr` | «write ADR», «new ADR», архитектурное решение |
| `deploy-check` | «pre-deploy», «release checklist», «production gate» |

10/10 skills в `.claude/skills/`.

## 2. Prompts/ — portable AI memory (Boltzmann pattern)

> [F: `prompts/README.md`]: «Промты — это portable long-term memory для AI. Сохраняя их в репо, мы гарантируем что future Claude Code сессии могут восстановить контекст прошлых итераций.»

Каждая нетривиальная iteration имеет:

1. **`prompts/iteration-N-<name>.md`** — spec/prompt, который можно replay в новой сессии для idempotent выполнения.
2. **`docs/iterations/iteration-N-applied.md`** — worklog с verdict (Applied / Skipped / Verified) per item.

**Когда писать новый prompt:**
- Нетривиальная iteration (> 30 min работы AI).
- Iteration с заметной разработческой дисциплиной (DoD per artifact).
- Iteration, которая может потребовать re-run при изменении upstream докуме нтов.

**Когда НЕ нужен prompt:**
- Bugfix или typo (commit message достаточно).
- Iteration < 30 min (worklog не нужен).

## 3. Guard rails — automated dispатчеры дисциплины

### 3.1 `import-linter` (18 контрактов в `backend/.importlinter`)

| Contract | Назначение |
|---|---|
| `CONTRACT 0` | `.raw()` / `connection.cursor()` ТОЛЬКО в `apps.core.rls.*` (NN #11) |
| `CONTRACTS 1-16` | Per-BC isolation: identity_auth, events, rsvp, ... не импортируют друг друга (только через contracts.py) |
| `CONTRACT 17` | Cross-context only через `apps.<ctx>.contracts` (ADR-001) |
| `CONTRACT 18` | Cross-context events ТОЛЬКО через `apps.core.outbox.*` (ADR-016) |

Запускается в pre-commit + GitHub Actions CI. Failing import = blocking merge.

### 3.2 `RLS Operational Constraints` (7 правил)

1. **Middleware-pattern с `transaction.atomic()` + `SET LOCAL`** (NN #11).
2. **`FORCE ROW LEVEL SECURITY`** на каждой RLS-таблице.
3. **RESTRICTIVE `default_deny`** policy на каждой RLS-таблице (fail-closed).
4. **`act_admin` BYPASSRLS-роль** отдельно от `act_app`; всё mutations → `audit_log_pii_access`.
5. **Запрет `.raw()`** вне `apps.core.rls.*` (enforced через import-linter CONTRACT 0).
6. **Миграции через прямой PG** (PgBouncer transaction-pooling несовместим с CREATE EXTENSION).
7. **Performance patterns**: `(SELECT)` wrap для `current_setting` + partial indexes под policy fields.

### 3.3 11 NON-NEGOTIABLE (compliance + санкции)

См. `CLAUDE.md` § NON-NEGOTIABLE. Каждый имеет explicit basis в законе / ADR / industry pattern. AI **не должен** обходить эти правила, даже если задача формально просит.

## 4. Workflow при появлении задачи

[F: `CLAUDE.md` § Workflow при появлении задачи]:

```
1. Прочитать релевантный раздел docs/:
   - Продуктовая задача → docs/PRODUCT.md
   - Архитектурная / код → docs/ARCHITECTURE.md соответствующий Level C
   - Compliance → docs/risk-register.md + ADR-012/013/014

2. Сверить со стеком V1.2 frozen и 11 NN в CLAUDE.md.
   Если задача предлагает что-то из «NEVER» → стоп, обсудить с founder.

3. Compliance check (если задача касается ПДн):
   - Ведёт ли изменение к расширению категорий ПДн в реестре РКН?
     (ст. 22 ч. 7 — уточнение в течение 10 рабочих дней)
   - Появляется ли новый зарубежный получатель → ст. 12 consent?
   - Создаётся ли новое PII-поле → ENCRYPT_AT_REST + audit_log_pii_access?

4. Один PR = один bounded context (контекст помещается в один промт).
   Cross-context изменения дробить.

5. Перед коммитом:
   - lint-imports (skill deploy-check)
   - pytest
   - django-silk (N+1 check)
   - RLS-policy review (FORCE + default_deny на новых таблицах)

6. Эпистемическая дисциплина:
   - Факты → со ссылкой [F: source].
   - Гипотезы → пометка [Г].
   - Неизвестное → пометка [?].
```

## 5. Когда использовать какой инструмент

| Situation | Tool |
|---|---|
| Создание новой модели в существующем BC | Edit + skill `create-migration` + skill `write-rls-policy` (если PII) |
| Cross-context side-effect | Skill `outbox-event` (НЕ Django signals!) |
| Новая auth-route | Skill `auth-flow` + per-context CLAUDE.md (identity_auth) |
| Новая UI-строка | Skill `add-translation` |
| Новый recurring event UX | Skill `recurrence-rrule` |
| Новое архитектурное решение | Skill `write-adr` |
| Добавление 17-го BC | Skill `add-bounded-context` + skill `write-adr` |
| Перед deploy на production | Skill `deploy-check` |
| Strategic planning / re-plan | Read `docs/iterations/iteration-5.5-roadmap.md` для context |
| Iteration N execution | Read `prompts/iteration-N-*.md` (если существует) либо создать новый |

## 6. Когда НЕ нужен Claude Code

- Compliance-actions (РКН-уведомления, ИП регистрация, подписание оферт) — **founder-bound**, не AI-task.
- Domain registration (whois check, BotFather) — founder через браузер.
- Manual outreach 50-100 тренерам в Soft launch — founder вручную (этап cold-start).
- Financial decisions (выбор тарифа Yandex, ESP контракт) — founder.

## 7. Forbidden patterns (Claude Code blacklist)

> [F: `CLAUDE.md` § «Что Claude НЕ должен делать»]:

- НЕ предлагать миграцию на микросервисы (ADR-001).
- НЕ предлагать Stripe / Clerk / Convex / Supabase / Vercel managed / AWS managed.
- НЕ использовать ORM в views/handlers (только через `services.py`).
- НЕ делать cross-context прямых импортов (только через `contracts.py`).
- НЕ использовать `prefetch_related` за пределами сервисного слоя.
- НЕ предлагать Elasticsearch / Meilisearch до p95 > 500ms.
- НЕ предлагать Celery / Redis до >1000 jobs/min.
- НЕ использовать `[Г]` / `[?]` пометки как факты при принятии решений.
- НЕ предлагать UI-kit до Pilot (design отложен).
- НЕ предлагать ML-персонализацию discovery до >10K MAU.

## 8. Iteration discipline

| Iteration | Type | Output |
|---|---|---|
| 0-3 | Bootstrap + research | 4 main files + scaffolding |
| 4 | Scaffolding implementation | 13 артефактов |
| 4.5 | Red-team audit | 5 fixes applied |
| 5 | Corrections to 4 main files | 16 applied + worklog |
| 5.5 | Strategic planning | DAG + critical path + 7-day plan |
| **6** | **Skills library bootstrap** | **10/10 SKILL.md** |
| **7** | **Per-context CLAUDE.md** | **6/6 для BC с Level C** |
| **8** | **Docs bootstrap (this)** | **erd + openapi + glossary + runbooks + workflow + security** |
| 9 (planned) | 10 missing Level C | Post-Pilot |

После Iteration 8 → **Phase 1 Bootstrap** (3-7 дней) → **Pilot Этап 0** (5-7 дней) → **ADR-007 decision gate** → MVP W1-W10 → Soft launch.

## Cross-refs

- Stack frozen + NN → `CLAUDE.md`.
- Strategic plan → `docs/iterations/iteration-5.5-roadmap.md`.
- ERD → `docs/erd.md`.
- API stub → `docs/api/openapi.yaml`.
- Glossary → `docs/glossary.md`.
- Runbooks → `docs/runbooks/{deploy,rollback,db-restore}.md`.
- Security policy → `SECURITY.md` (root).
