# prompts/ — Reusable AI prompts for Claude Code

> Переиспользуемые промты для Claude.ai сессий и Claude Code. Каждый промт — отдельная iteration с чёткой целью.
> [F: `CLAUDE.md` строка 25: «prompts/ — переиспользуемые промты для Claude Code»].

## Содержимое

### Docs / scaffolding iterations (Claude.ai sessions с Project Knowledge)

| Файл | Назначение | Когда использовать |
|---|---|---|
| `iteration-0-bootstrap.md` | Repo bootstrap (Phase 0): 4 main docs + 13 scaffolding artifacts + skeleton tree | Один раз, до git init |
| `iteration-4.5-audit.md` | Red-team audit 13 артефактов Iteration 4 | После любой scaffolding-итерации перед коммитом |
| `iteration-5-corrections.md` | Apply 18 коррекций к 4 главным файлам | Запускать в новой Claude.ai сессии Opus 4.7 после Iteration 4 commit |

### Code-generation iterations (Claude Code сессии на ветке от main)

| Файл | Назначение | Когда использовать |
|---|---|---|
| `phase-1.4-django-skeleton.md` | Django 5.2 LTS skeleton: layered settings + RLS middleware + 3 BC scaffolds (identity_auth/events/rsvp) + healthz | **Сейчас (после merge PR #3 audit-fixes).** Запускать в новой Claude Code сессии Opus 4.7 на свежей ветке от main. ETA: 6-8h AI. |

## Как использовать промт

1. Открыть новую Claude.ai сессию в Project «Act» с моделью **Claude Opus 4.7**.
2. Включить tools: `view`, `str_replace`, `create_file`, `present_files`, `project_knowledge_search`, `conversation_search`.
3. Прикрепить relevant файлы из репо (через /mnt/project/ если auto-mount, или вручную).
4. Скопировать содержимое нужного промта целиком в первое сообщение.
5. Дождаться completion + applied artifacts.

## Iteration roadmap

- ✅ Iteration 0 — Bootstrap repo (Phase 0 deliverable).
- ✅ Iteration 1-3 — Pre-development research (audit + reconciliation).
- ✅ Iteration 4 — Scaffolding implementation (13 артефактов).
- ✅ Iteration 4.5 — Audit + 5 fixes applied.
- ✅ Iteration 5 — Corrections to 4 main files (16 applied / 2 skipped / 3 verified).
- ✅ Iteration 5.5 — Next-Steps Roadmap (planning-only: DAG / critical path / 7-day plan).
- ✅ Iteration 6 — Skills library bootstrap (8 new SKILL.md → 10/10 total).
- ✅ Iteration 7 — Per-context CLAUDE.md bootstrap (5 new → 6/6 total с identity_auth).
- ✅ Iteration 8 — Docs bootstrap (erd.md, openapi.yaml stub, glossary.md, runbooks/×3, AI-WORKFLOW.md, SECURITY.md root).
- ✅ Architecture self-audit (PR #3, 2026-05-27) — 9 рассинхронизаций исправлены до Phase 1 старта.
- ⏳ **Phase 1.4 (next)** — Django skeleton via `phase-1.4-django-skeleton.md`. Первый PR с реальным кодом.
- ⏳ Phase 1.4.bis — PG extensions migration via direct PG (founder-bound, требует Phase 1.1 Yandex Cloud setup).
- ⏳ Phase 1.5 — Next.js skeleton (App Router + next-intl). Промпт создаётся после успешного 1.4 merge.
- ⏳ Phase 1.6 — import-linter в CI. Промпт создаётся после Phase 1.2 (GitHub branch protection + secrets).
- ⏳ Phase 1.7 — Procrastinate periodic-task stub. После Phase 1.4 + 1.4.bis.
- ⏳ Iteration 10 (planned, post-Pilot) — 10 missing Level C drafts (бывший Iter 9 в roadmap; renumbered after Phase 1.4 took the 9-slot semantically).

После Phase 1 bootstrap (Phase 1.1–1.9) → Pilot Этап 0 (5-7 дней) → ADR-007 gate → MVP-спринты W1-W10 → Soft launch (50-100 тренеров вручную). Параллельный compliance трек: Pre-Phase 0.1+0.2 РКН (до 30 дней проверки).

## Anthropic Boltzmann pattern

Промты — это **portable long-term memory** для AI. Сохраняя их в репо, мы гарантируем что future Claude Code сессии могут восстановить контекст прошлых итераций. См. `docs/CHANGELOG.md` секция «Failed approaches» для antipatterns которые мы уже отвергли.
