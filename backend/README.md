# backend/ — Django 5.2 (создаётся в Phase 1 Bootstrap)

> Скелет Python-части Act. На текущем этапе (Phase 0) — только конфигурация tooling и каркас директорий. Django-проект и 16 bounded contexts инициализируются в Phase 1.

## Структура

```
backend/
├── pyproject.toml          # PEP 621 + ruff + mypy + pytest-django config
├── .importlinter           # 18 contracts для DDD module boundaries
├── manage.py               # создаётся в Phase 1: `django-admin startproject act .`
├── Dockerfile.dev          # local dev image (referenced by docker-compose.yml)
├── act/                    # Django project root (settings, urls, wsgi/asgi)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py         # Phase 1
│   │   ├── dev.py          # Phase 1
│   │   ├── test.py         # Phase 1 — DJANGO_SETTINGS_MODULE для pytest
│   │   └── production.py   # Phase 1
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/                   # 16 bounded contexts
│   ├── core/               # RLS middleware, outbox, shared utils (ADR-006, ADR-016)
│   ├── identity_auth/      # Level C готов (см. apps/identity_auth/CLAUDE.md)
│   ├── user_profile/       # Level C — после Pilot
│   ├── verification/       # Level C — после Pilot
│   ├── groups/             # Level C — после Pilot
│   ├── events/             # Level C готов
│   ├── recurrence_engine/  # Level C готов (внутри Events)
│   ├── rsvp/               # Level C готов
│   ├── contacts_sharing/   # Level C готов
│   ├── ratings/            # Level C — после Pilot
│   ├── discovery/          # Level C — после Pilot
│   ├── recommendations/    # Level C готов (stub на MVP)
│   ├── notifications/      # Level C — после Pilot (но ADR-010 FSM зафиксирован)
│   ├── moderation/         # Level C — после Pilot
│   ├── localization/       # Level C готов
│   ├── analytics/          # Level C — после Pilot
│   └── admin_console/      # Level C — после Pilot
└── tests/                  # integration tests (per-app unit tests — в apps/<ctx>/tests/)
```

## Phase 1 Bootstrap commands (для будущей сессии)

```bash
# Из backend/
cd backend
python -m venv .venv && source .venv/bin/activate
pip install uv
uv pip install -e .[dev]
django-admin startproject act .
# Затем — split settings, скопировать pyproject.toml markers, etc.
# Полный план — в docs/ARCHITECTURE.md секция «Bootstrap: Phase 0 + Phase 1»
```

## Конвенции

- **ORM ТОЛЬКО в `services.py`** [F: CLAUDE.md строка 100].
- **Cross-context — через `contracts.py`** (DTOs), enforced `.importlinter` CONTRACT 1-16.
- **RLS обязательна** для user-attributed таблиц (см. `.claude/skills/write-rls-policy/SKILL.md`).
- **Cross-context side-effects** — только через `outbox_event` (ADR-016, см. `.claude/skills/outbox-event/SKILL.md`).
- **Миграции — через прямой PG, минуя PgBouncer** (NON-NEGOTIABLE #11): `make migrate-direct`.
