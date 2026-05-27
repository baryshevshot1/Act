# prompts/ — Reusable AI prompts for Claude Code

> Переиспользуемые промты для Claude.ai сессий и Claude Code. Каждый промт — отдельная iteration с чёткой целью.
> [F: `CLAUDE.md` строка 25: «prompts/ — переиспользуемые промты для Claude Code»].

## Содержимое

| Файл | Назначение | Когда использовать |
|---|---|---|
| `iteration-4.5-audit.md` | Red-team audit 13 артефактов Iteration 4 | После любой scaffolding-итерации перед коммитом |
| `iteration-5-corrections.md` | Apply 18 коррекций к 4 главным файлам | Запускать в новой Claude.ai сессии Opus 4.7 после Iteration 4 commit |

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
- ⏳ Iteration 9 (planned, post-Pilot) — 10 missing Level C drafts.

После Iteration 8 — Phase 1 Bootstrap (3-7 дней) → Pilot Этап 0 (5-7 дней) → ADR-007 gate → MVP-спринты W1-W10 → Soft launch (50-100 тренеров вручную). Параллельный compliance трек: Pre-Phase 0.1+0.2 РКН (до 30 дней проверки).

## Anthropic Boltzmann pattern

Промты — это **portable long-term memory** для AI. Сохраняя их в репо, мы гарантируем что future Claude Code сессии могут восстановить контекст прошлых итераций. См. `docs/CHANGELOG.md` секция «Failed approaches» для antipatterns которые мы уже отвергли.
