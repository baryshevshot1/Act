# Changelog — Act documentation

> Все существенные изменения документации проекта Act фиксируются здесь.
> Формат — адаптированный [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/); SemVer-семантика для версий документации.
> Эпистемика: `[F:]` факт со ссылкой; `[В]` вывод; `[Г]` гипотеза; `[?]` неизвестное.

## [Unreleased]

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

### TODO (Iteration 8+)

- `docs/erd.md` (Mermaid), `docs/api/openapi.yaml` (stub), `docs/AI-WORKFLOW.md`, `docs/glossary.md`, `docs/runbooks/*` (Iteration 8).
- `SECURITY.md`, `.github/workflows/ci.yml`, `tests/conftest.py` — отложены до Phase 1 bootstrap.
- 10 missing Level C (User Profile, Verification, Groups, Ratings, Discovery, Notifications, Moderation, Analytics, Admin Console) — пост-Pilot (Iteration 9).

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
