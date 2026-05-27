# Changelog — Act documentation

> Все существенные изменения документации проекта Act фиксируются здесь.
> Формат — адаптированный [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); SemVer-семантика для версий документации.
> Эпистемика: `[F:]` факт со ссылкой; `[В]` вывод; `[Г]` гипотеза; `[?]` неизвестное.

## [Unreleased]

### Added (Phase 1.4 — Django skeleton)

Первая итерация **реального кода** в репозитории. Skeleton с 3 BC (identity_auth / events / rsvp) + apps.core (RLS middleware, CSP middleware, outbox stub).

- `backend/manage.py` + `backend/act/{wsgi,asgi,urls}.py` — Django CLI entry-points.
- `backend/act/settings/{base,dev,test,prod}.py` — layered settings.
    - Prod fail-fast при отсутствии `DATABASE_URL`, `DATABASE_URL_ADMIN` (act_admin BYPASSRLS — RLS Operational Constraint #4), `DATABASE_URL_DIRECT` (миграции минуя PgBouncer — NN #11), `PII_HMAC_SECRET`.
    - 16 BC apps + django-allauth + corsheaders + drf-spectacular в `INSTALLED_APPS`; middleware order зафиксирован (Auth → RLS → CSP).
    - `AUTH_USER_MODEL = 'identity_auth.User'`; Argon2id default hasher; secure cookies в base (overridden dev).
- `backend/apps/core/rls/middleware.py` — `RLSContextMiddleware` (`set_config('app.current_user_id', user_id, true)` внутри `transaction.atomic()`); no-op на не-PG backends; PgBouncer-safe.
- `backend/apps/core/middleware/csp.py` — hand-rolled CSP middleware (django-csp не в pyproject).
- `backend/apps/core/outbox/{models,services}.py` — `OutboxEvent` модель + `publish_event()` service (ADR-016).
- `backend/apps/core/views.py` — `healthz` (200 OK, без DB check; heavy readiness — W10).
- `backend/apps/identity_auth/{models,services,contracts,admin,apps}.py` — 7 entities (User, Session, MagicLinkToken, OAuthProvider, OAuthIdentity, PasskeyCredential placeholder, ConsentRecord, AuthEvent); все user-attributed таблицы готовы под RLS policies (FORCE + default_deny — Phase 1.4.bis migration).
- `backend/apps/events/{models,services,contracts,admin,apps}.py` — Event + EventSeries + EXDate + RecurrenceOverride + EventCoverImage (RFC 5545 verbatim).
- `backend/apps/rsvp/{models,services,contracts,admin,apps}.py` — EventParticipant + GuestRSVP + WaitlistEntry.
- All `services.py` methods — signatures с `raise NotImplementedError("W{N} sprint")`. Реальная реализация — в MVP-спринтах W1 (auth), W3 (events), W5 (recurrence), W6 (RSVP).
- `.gitignore` обновлён: `/.venv`, `backend/dev.sqlite3`, `backend/.import_linter_cache/`.

### Changed (Phase 1.4 — import-linter contracts pragmatics)

- `backend/.importlinter`:
    - `django` добавлен в `root_packages` — иначе `django.db.backends.utils` в `forbidden_modules` invalid для внешнего пакета.
    - CONTRACT 0 получил `allow_indirect_imports = True` — без этого любая модель ловится transitive chain `django.db.models → django.db.backends.utils`; реальный bypass-вектор (raw SQL) — только прямой import.
    - 16 контрактов с `ignore_imports` получили per-contract `unmatched_ignore_imports_alerting = warn` — Phase 1.4 имеет 13 пустых BC, для которых ignore_imports формально без matches. После наполнения BC в W1+ — переключить обратно на default 'error'.

### TODO (Phase 1.4.bis — PG extensions migration)

- `backend/apps/core/migrations/0001_extensions.py` — `pgcrypto`, `btree_gist`, `pg_trgm`, `unaccent`, `pg_uuidv7` через прямой PG (NN #11).
- `backend/apps/<ctx>/migrations/0001_initial.py` — после extensions, через `PG_BOUNCER_HOST=""`.
- RLS policies (FORCE + RESTRICTIVE `default_deny` + PERMISSIVE per-table) — через skill `write-rls-policy` в RunSQL миграциях.
- `infra/postgres/init.sql` обновить — добавить `app.current_user_id` GUC setup для RLS.
- Реальный Telegram OIDC adapter (~100 строк, W1 spirit) — НЕ Phase 1.4 scope.

### Added (Iteration 4 — scaffolding implementation)

- `docs/CHANGELOG.md` — этот файл; закрывает Iteration 3 reference risk (ADR-005↔007 renumber).
- `backend/pyproject.toml` — единая Python-конфигурация (ruff, mypy, pytest-django, coverage 70%).
- `.env.example` — inventory environment variables со всеми группами стека [F: `CLAUDE.md` строки 47-69].
- `backend/.importlinter` — 18 contracts: 1 на запрет `.raw()` вне `apps.core.rls.*` (NON-NEGOTIABLE #11) + 16 per-BC изоляции (ADR-001) + 1 cross-context outbox (ADR-016).
- `docs/pilot/day-template.md` — daily-tracking template для Pilot Этап 0 [F: PDF V1.3 секция 17.4].
- `.claude/skills/write-rls-policy/SKILL.md` — skill с FORCE + RESTRICTIVE `default_deny` template.
- `.claude/skills/outbox-event/SKILL.md` — skill для cross-context emit через `outbox_event` (ADR-016).
- `docs/jtbd-bc-mapping.md` — связка 8 JTBD ↔ 16 BC с wedge focus на JTBD-2.
- `docs/risk-register.md` — консолидированный реестр 4 источников (PDF p2, PDF p3 секции 16 и 21, ARCHITECTURE.md Risk register).
- `backend/apps/identity_auth/CLAUDE.md` — per-context AI-контекст для security-critical BC.
- `docker-compose.yml` + `Makefile` + `infra/postgres/init.sql` — local-dev окружение с extensions ADR-006.

### Changed (Iteration 4.5 — red-team audit fixes)

- `.env.example`, `backend/pyproject.toml`, `docs/jtbd-bc-mapping.md` — исправлена misattribution ADR-005 к выбору django-allauth (ADR-005 фиксирует **отказ** от Stripe/Clerk/Convex/Vercel, не выбор django-allauth).
- `backend/apps/identity_auth/CLAUDE.md` — header «PDF V1.3 секция 20.1 verbatim» уточнён до «7 verbatim + AuthEvent — Wave 1+ дополнение для `audit_log_pii_access`»; добавлены явные cross-ref на skill `write-rls-policy` (NON-NEGOTIABLE #11) + bullet про NON-NEGOTIABLE #2 (ст. 9 ред. 156-ФЗ — отдельный документ согласия).

### Changed (Iteration 5 — corrections to 4 main files)

- `README.md` — добавлены fallback домены (R2); cross-ref на полный ADR-список (R4); explicit ADR-005↔007 renumbering note в источниках (R5).
- `CLAUDE.md` — добавлена строка «Версионирование» → CHANGELOG (C1); ADR-источники к NON-NEGOTIABLE #3, #6, #7, #11 (C2-C5); industry source refs к default_deny в глоссарии (C6).
- `docs/PRODUCT.md` — добавлена BC composition к JTBD-3 (P3); cross-ref на jtbd-bc-mapping.md для 4 слоёв монетизации (P4). P1, P2 verified — already present (Skipped).
- `docs/ARCHITECTURE.md` — **CRITICAL**: Historical note про ADR-005↔ADR-007 в самом ADR-007 (A1); Triggers пересмотра для ADR-003 (единственного ADR без явных triggers, A2); Level C status note для ADR-010 (A4); новый bucket «Iteration 1-5 reconciliation» в Источниках (A5); cross-refs на текущие SKILL.md в разделе «CLAUDE.md иерархия» (A6).

### Added (Iteration 5 — supporting files)

- `docs/iterations/iteration-5-applied.md` — worklog 21 items с verdict Applied/Skipped/Verified.

### Added (Iteration 5.5 — Next-Steps Roadmap)

- `docs/iterations/iteration-5.5-roadmap.md` — strategic planning документ: repository state snapshot, 8 open founder decisions, 25-step roadmap DAG, critical path с параллельным compliance треком, 7-day action plan, открытые вопросы за горизонтом, triggers пересмотра.

### Added (Iteration 6 — Skills library bootstrap)

- `.claude/skills/recurrence-rrule/SKILL.md` — RFC 5545 RRULE / EXDATE / RECURRENCE-ID для EventSeries (146 строк).
- `.claude/skills/guest-rsvp-merge/SKILL.md` — `merge_guest_on_signup` pattern (PDF V1.3 sec 20.4, 162 строки).
- `.claude/skills/auth-flow/SKILL.md` — Telegram OIDC + magic-link POST (NN #6) + 7 приоритетов аутентификации (169 строк).
- `.claude/skills/add-translation/SKILL.md` — UI strings (messages/*.json) + JSONB expression indexes + Russian four plurals (191 строка).
- `.claude/skills/create-migration/SKILL.md` — expand-contract + direct PG (NN #11) + запрещённые online ops (209 строк).
- `.claude/skills/add-bounded-context/SKILL.md` — 17-й BC scaffolding (ADR-001 modular monolith + import-linter) (225 строк).
- `.claude/skills/write-adr/SKILL.md` — MADR 4.0 template + status lifecycle + ADR-005↔007 renumbering warning (159 строк).
- `.claude/skills/deploy-check/SKILL.md` — pre-deploy checklist (5 compliance gates + 10 technical gates + OWASP map) (232 строки).
- `docs/iterations/iteration-6-applied.md` — worklog per skill DoD.

### Added (Iteration 7 — Per-context CLAUDE.md bootstrap)

- `backend/apps/events/CLAUDE.md` — Events + Recurrence Engine context (RFC 5545 patterns, generation horizon 21 days, owner-only writes) (73 строки).
- `backend/apps/rsvp/CLAUDE.md` — RSVP & Attendance context (guest-merge invariants, capacity/waitlist, encrypted PII lookup) (95 строк).
- `backend/apps/contacts_sharing/CLAUDE.md` — Contacts Sharing context (bilateral consent invariant, encrypted channel_value, time-gating в service-layer) (114 строк).
- `backend/apps/recommendations/CLAUDE.md` — Recommendations context (stable API contract для ML migration, NO multiplicative ranking) (111 строк).
- `backend/apps/localization/CLAUDE.md` — Localization context (three translation strategies, Russian four plurals, next-intl 4.x patterns) (107 строк).
- `docs/iterations/iteration-7-applied.md` — worklog per CLAUDE.md DoD.

### Added (Iteration 8 — Docs bootstrap)

- `docs/erd.md` — Mermaid ERD: BC dependency overview + per-BC detailed ERDs (identity_auth, events, rsvp, contacts_sharing, ratings, groups, outbox, audit, localization). 345 строк, 7 mermaid diagrams.
- `docs/api/openapi.yaml` — OpenAPI 3.1 stub: 12 endpoints (/healthz, /api/v1/version, /api/v1/auth/{telegram-oidc,magic-link}/*, /api/v1/me, /api/v1/events*, /api/v1/events/{id}/rsvp{,/guest}); 6 schemas (UserDTO, EventDTO, ParticipantDTO, GuestRSVPDTO, ConsentInput, ErrorResponse); 4 response refs; bearer + CSRF + cookie security. 563 строки.
- `docs/glossary.md` — 40+ терминов alphabetically (Domain · Architecture · Compliance · Metrics · Stack · Process categories). 178 строк.
- `docs/AI-WORKFLOW.md` — 3-level CLAUDE.md иерархия + skills library + Boltzmann prompts/ pattern + guard rails (import-linter, RLS Operational Constraints, 11 NN); skill triggers cheatsheet. 213 строк.
- `docs/runbooks/deploy.md` — Coolify deploy workflow: pre-deploy gates → staging → smoke → production → post-verify; migration zero-downtime; hotfix; Phase 1 pilot deploys. 176 строк.
- `docs/runbooks/rollback.md` — when to rollback (trigger matrix P0/P1/P2); Coolify image rollback (UI + CLI); DB rollback (code-only vs migration reverse vs RLS leak P0); communication; incident reports. 132 строки.
- `docs/runbooks/db-restore.md` — Yandex Managed PG backup (auto + manual snapshot + Selectel cross-region Plan B); 4 restore scenarios (PITR, full backup, Selectel sanctions-fallback, single-table); monthly drill mandatory; RTO/RPO targets. 209 строк.
- `SECURITY.md` (root) — responsible disclosure email; severity tiers + response SLA; scope in/out; security posture (152-ФЗ + OWASP Top 10:2025 mapping); 20+ security controls table; hall of fame placeholder. 149 строк.
- `docs/iterations/iteration-8-applied.md` — worklog per artifact DoD.

### Fixed (Architecture self-audit — pre-Phase 1, 2026-05-27)

Pre-Phase 1 self-audit `docs/ARCHITECTURE.md` (2670 строк) + cross-doc consistency check. Найдено и исправлено 8 рассинхронизаций (1 affecting code, 2 outdated meta, 5 cosmetic cross-refs):

- **M1** `docs/ARCHITECTURE.md:870` — `ConsentRecord` schema purposes расширен с 3 (`core_processing`, `marketing`, `contact_sharing`) до 7 в соответствии с `CLAUDE.md` глоссарием + `apps/identity_auth/CLAUDE.md` + `docs/erd.md` (добавлены `cross_border_transfer`, `cookies_essential`, `cookies_analytics`, `cookies_marketing`). **Affects code** — Phase 1.4 Django skeleton генерит `ConsentRecord` model по этому DDL.
- **M2** `docs/ARCHITECTURE.md:3` (header summary) — «13 ADR-решений» → «16 ADR-решений» (line 8 уже правильно фиксирует 001–016).
- **M3** `docs/ARCHITECTURE.md:1863` — «Текущие skills (Iteration 4): write-rls-policy + outbox-event; оставшиеся 8 SKILL.md планируются в Iteration 6» → актуальное «10/10 после Iteration 6» с перечислением всех skills и ссылкой на `docs/AI-WORKFLOW.md`.
- **m4** `docs/ARCHITECTURE.md:2287` — broken cross-ref «§ 16 BC ↔ Level C status в iteration-4.5-audit-report.md» (раздела нет) → ссылка на `iteration-5.5-roadmap.md` step 24.
- **m5** `docs/ARCHITECTURE.md:570` — «Phase 4 в roadmap» (Phase 4 нигде не определена) → «Iteration 9 в `docs/iterations/iteration-5.5-roadmap.md` step 24».
- **m6** `docs/ARCHITECTURE.md:1969` — typo `cross_border_consent` → `cross_border_transfer` (актуальное имя purpose).
- **m7** `docs/ARCHITECTURE.md:2543-2545` — § Источники → Iteration 1-5 reconciliation расширен записями Iter 5.5/6/7/8 + audit note.
- **m8** `docs/erd.md:339` — «10 missing BCs» перечисление расширено с 8 до 10 (добавлены `user_profile` + `recurrence_engine standalone`).
- **m9** `CLAUDE.md:25` + `README.md:37` — два дополнительных упоминания «13 ADR» в навигационных артефактах (структурное дерево + таблица документации) → «16 ADR»; README.md уточнён размер ARCHITECTURE.md с «~1900 строк» до «~2700 строк» (фактический wc -l = 2680).

### TODO (Iteration 9+)

- `tests/conftest.py` + `.github/workflows/ci.yml` — отложены до Phase 1 bootstrap (Phase 1.2 GitHub branch protection + 1.6 import-linter в CI).
- 10 missing Level C (User Profile, Verification, Groups, Ratings, Discovery, Notifications, Moderation, Analytics, Admin Console, Recurrence Engine standalone) — пост-Pilot (Iteration 9, ~3-4 недели parallel с MVP).

-----

## [Wave 3] — 2026-05-24

### Added

- **ADR-016** — Cross-context events via Transactional Outbox (см. `ARCHITECTURE.md` строки ADR-016 verbatim).
- Cookie consent UI (3 уровня: `cookies_essential` / `cookies_analytics` / `cookies_marketing`) с записями в `identity_auth_consent`.
- `audit_log_pii_access` (planned) — централизованный лог чтений PII-полей admin / moderator / service, retention 1 год.
- 13 gaps закрыты после P2 review.
- Operational sections: Disaster Recovery · DB Migration Strategy · Feature Flags · Rate Limiting · Data Retention Policies · Cost Monitoring · OWASP Top 10:2025 mapping.

-----

## [Wave 2 / P1] — 2026-05-24

### Added

- **ADR-014** — Field-level encryption (django-cryptography + Yandex Lockbox). Отвергнут `pgcrypto` (ключ в plain в БД).
- **ADR-015** — OG image generation strategy (статический PNG на MVP → `@vercel/og` Satori standalone в Next.js v1.1).
- UUIDv7 strategy для PK write-heavy таблиц (Events, RSVP, Notifications, AuditLog, Outbox).

-----

## [Wave 1 / P0] — 2026-05-24

### Added

- **ADR-008** — Discovery ranking (weighted sum заменил multiplicative `rep × act × rec × prox`).
- **ADR-009** — Group publishing (`owner_only` / `members_moderated` / `members_open`).
- **ADR-010** — NotificationDelivery FSM (`acknowledged` как NSM ground truth, не `opened` из-за Apple MPP).
- **ADR-011** — Admin Console hybrid (Django admin + бизнес-views).
- **ADR-012** — Compliance Baseline (РКН ст. 22 + ст. 12 + Privacy Policy + cookie consent UI; блокер Phase 1).
- **ADR-013** — Notification fallback для non-consented пользователей (Telegram только при ст. 12 consent).
- **RLS Operational Constraints** — `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy + `act_app` (без BYPASSRLS) / `act_admin` (с BYPASSRLS) + `transaction.atomic()` + `SET LOCAL app.current_user_id`.
- 6 Level C готовы: Identity & Auth, Events (с Recurrence), RSVP & Attendance, Contacts Sharing, Recommendations, Localization.
- 11 NON-NEGOTIABLE в `CLAUDE.md` строки 129-141 (verbatim).

### Renamed

- **ADR-005 ↔ ADR-007 renumbering** (КРИТИЧЕСКИЙ — закрывает reference risk на 12+ месяцев вперёд):
  - **V1.3** (PDF `Leto_project_p3.pdf` секция 17.5): «ADR-005 — Stack commit (Django + Next.js)», Proposed после Pilot Этап 0.
  - **Wave 1+** (`ARCHITECTURE.md` ADR section): **ADR-005** = «Отвергнут зарубежный managed-стек (Stripe / Clerk / Convex / Vercel managed)»; **stack commit перенумерован в ADR-007** (Proposed, pending Pilot).
  - **Импакт:** исторические промты и PDF могут ссылаться на «ADR-005» как stack commit. Для актуальной семантики использовать **ADR-007**.

-----

## [V1.3] — 2026-05-24 (исторический контекст, `Leto_project_p3.pdf`)

### Added

- Pilot Этап 0 (5-7 рабочих дней, KPI Accept-Rate ≥ 60% на core-flow).
- Bootstrap inventory (Phase 0 legal + tooling × 10 пунктов; Phase 1 bootstrap × 8 групп).
- Level C × 3: Identity & Auth, Events с Recurrence, RSVP & Attendance.
- Root CLAUDE.md template (4 NON-NEGOTIABLE; расширен до 11 в Wave 1+).
- 10 Risk checks перед stack commit (Pass / Fix / Pivot criteria — см. PDF секция 21).

-----

## [V1.2] — 2026-05-23 (исторический контекст, `Leto_project_p3.pdf`)

### Added

- Технологический стек Уровень B (~17 layers).
- Risk register × 5 рисков.

-----

## [V1.1] — 2026-05-23 (исторический контекст, `Leto_project_p1.pdf`)

### Added

- Shareable Event Cards (OG-теги по платформам, динамические OG-изображения).
- Frictionless Onboarding (guest RSVP, magic links, passkeys, social login).
- Безопасность упрощённых флоу (OWASP Top 10:2025, 152-ФЗ ст. 9 + ст. 18, Apple Mail Privacy Protection).
- Recurrence Engine детальный UX (RRULE / EXDATE / RECURRENCE-ID / RANGE=THISANDFUTURE).

-----

## [V1.0] — 2026 (исторический контекст, `Leto_project_p2.pdf`)

### Added

- Концепция «Find a Company» (переименована в **Act** в Wave 1).
- 16 bounded contexts.
- 8 JTBD (JTBD-1..6 primary + JTBD-7 networking, JTBD-8 культурные — отложены).
- 4 слоя монетизации.
- Стартовый wedge — тренеры регулярных групп в Москве.

-----

## Failed approaches (Anthropic Boltzmann pattern)

> Здесь фиксируются tried-and-rejected approaches, чтобы Claude Code не возвращался к ним в новых сессиях.

- **`pgcrypto` symmetric encryption** (отвергнут в Wave 2 / ADR-014): ключ передаётся в БД в plain; Yandex admin и `pg_stat_activity` видят ключ. Заменён на django-cryptography + Yandex Lockbox.
- **Multiplicative discovery ranking** `(rep × act × rec × prox)` (отвергнут в Wave 1 / ADR-008): обнуляет любое новое событие до первого RSVP, ломает cold-start. Заменён на weighted sum.
- **Django signals для cross-context** (отвергнуты в Wave 2 / ADR-016): не транзакционны — при падении subscriber после commit event теряется. Заменены на Transactional Outbox через `outbox_event`.
- **`pixel-tracking opened` как NSM ground truth** (отвергнут в Wave 1 / ADR-010): Apple MPP даёт ~100% open rate независимо от реального открытия; iOS 18 режет UTM. Заменён на `acknowledged` (явное действие пользователя).
- **Stripe / Clerk / Convex Pro / Vercel managed** (отвергнуты в V1.2 / ADR-005): Stripe не оперирует в РФ с 2022; Clerk/Convex billing через Stripe; Vercel не соответствует 152-ФЗ ст. 18 (первичная запись ПДн вне РФ).
