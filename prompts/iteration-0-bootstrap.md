# Промт: Iteration 0 — Bootstrap Repository (Phase 0)

> **Назначение.** Финальная сборка скелета репозитория Act из 4 главных файлов + 13 артефактов Iteration 4 (после audit-fixes Iteration 4.5) + supporting infrastructure files + skeleton folders для будущей разработки backend / frontend / design. Результат — готовый к `git init && git push` репозиторий на локальной машине.
>
> **Когда запускать.** Один раз — для перехода от рабочих сессий Claude.ai к локальному репозиторию. После завершения Iteration 4 + 4.5 audit.
>
> **Кто запускает.** Соло-фаундер Андрей в Claude.ai сессии Project «Act» с моделью **Claude Opus 4.7** (выполняется в той же сессии, где была Iteration 4 — для сохранения контекста).
>
> **Что НЕ делает.** Не пересматривает архитектуру. Не создаёт новые ADR. Не пишет Django / Next.js код (это Phase 1). Не делает `git init` локально (это шаг founder'а после получения ZIP).

-----

## 1. Роль

Ты — **prompt engineer + founder Claude Code + full-stack architect** в одном лице. Цель — собрать репозиторий по best practices одновременно для:

1. **Соло-разработчика на AI-stack** (Claude Code primary executor).
2. **Modular monolith DDD** (16 bounded contexts с enforced boundaries).
3. **Russian compliance project** (152-ФЗ + санкционные ограничения).
4. **Phase 0 → Phase 1 готовности** (одна команда `make migrate-direct` после `git clone`).

Источники только официальные: Anthropic Claude Code docs, Anthropic skills convention, PEP 621 (Python), Next.js docs, Django docs, conventional commits, semver, Keep a Changelog.

-----

## 2. Вход

### 2.1. Существующие файлы (готовы к копированию)

- **4 главных файла** в `/mnt/project/`:
  - `README.md`, `CLAUDE.md`, `PRODUCT.md`, `ARCHITECTURE.md`.
- **13 артефактов Iteration 4** в `/mnt/user-data/outputs/` (после fixes Iteration 4.5):
  - `docs/CHANGELOG.md`, `pyproject.toml`, `.env.example`, `.importlinter`, `docs/pilot/day-template.md`, 2 SKILL.md, `docs/jtbd-bc-mapping.md`, `docs/risk-register.md`, `apps/identity_auth/CLAUDE.md`, `docker-compose.yml`, `Makefile`, `infra/postgres/init.sql`.
- **3 memory-файла**:
  - `audit-report-iteration-4.md`, `iteration-4.5-audit-prompt.md`, `iteration-5-corrections-prompt.md`.

### 2.2. Структура из CLAUDE.md (FROZEN, не менять)

`backend/` — Django: содержит `pyproject.toml`, `.importlinter`, `manage.py`, `apps/<16 BC>/`.
`frontend/` — Next.js (создаётся в Phase 1).
`docs/` — `PRODUCT.md`, `ARCHITECTURE.md`, + scaffolding artifacts.
`.claude/` — `skills/<name>/SKILL.md`.
`infra/` — Coolify + GitHub Actions configs.
`prompts/` — переиспользуемые промты.

-----

## 3. Цели

### 3.1. Главная — собрать `act-phase-0.zip`

Готовый к разархивации на macOS, который после `cd act && git init && git remote add origin <url> && git push -u origin main` даёт работающий репозиторий.

### 3.2. Вторичные

- **Корректировки путей** в `pyproject.toml` — после переноса в `backend/`: `source = ["apps"]`, `testpaths = ["tests", "apps"]` (убираем префикс `backend/`).
- **Skeleton директорий** для всех 16 BC с пустыми `__init__.py`.
- **Frontend skeleton** с `messages/{ru,en}.json` (пустые catalogs) + `components/<ui-bc>/`.
- **Supporting files**: `.gitignore` (Python+Node+macOS), `.gitattributes`, `.editorconfig`, `LICENSE` (Proprietary), `backend/Dockerfile.dev` (для docker-compose worker profile).
- **Documentation scaffolding**: `docs/design/principles.md` (UI principles до Pilot), `design/` папка для бинарных ассетов, `prompts/README.md`, `docs/iterations/README.md`.

### 3.3. Что НЕ делать

- НЕ создавать real Django код (`settings.py`, `urls.py` — это Phase 1).
- НЕ создавать real Next.js код (`app/page.tsx` — это Phase 1).
- НЕ финализировать UI/UX (отложено до Pilot Этап 0, см. `CLAUDE.md` строка 153).
- НЕ добавлять GitHub Actions workflows (Iteration 4 § 3.3 deferred).
- НЕ создавать тесты (`tests/conftest.py` deferred до Phase 1).
- НЕ инициализировать git локально (это шаг founder'а).
- НЕ менять содержимое 4 главных файлов (Iteration 5 это сделает).

-----

## 4. Workflow

### 4.1. Создать tree через `mkdir -p`

Полный list директорий (см. § 5 финальная структура).

### 4.2. Скопировать 4 главных файла из `/mnt/project/`

Точно в paths из CLAUDE.md: `README.md`, `CLAUDE.md` — root; `PRODUCT.md`, `ARCHITECTURE.md` — `docs/`.

### 4.3. Скопировать 13 артефактов + поправить paths

- 8 unchanged → точно в spec-paths.
- 5 fixed → перезаписать audit-fixed версии.
- `pyproject.toml` → `backend/pyproject.toml` + `str_replace` paths.
- `.importlinter` → `backend/.importlinter`.
- `apps/identity_auth/CLAUDE.md` → `backend/apps/identity_auth/CLAUDE.md`.

### 4.4. Создать skeleton

- 16 пустых `__init__.py` для BC + `backend/act/__init__.py` + `backend/act/settings/__init__.py`.
- `frontend/messages/{ru,en}.json` с минимальным `{}` + `_comment` field.
- `.gitkeep` для пустых директорий (app/, public/, styles/, components/<bc>/, tests/, design/wireframes/, design/journeys/, infra/coolify/, infra/github-actions/, scripts/, .github/workflows/, docs/design/decisions/).

### 4.5. Создать supporting файлы

- `.gitignore` — Python + Node + macOS + tooling caches + secrets.
- `.gitattributes` — LF normalization + binary file marks.
- `.editorconfig` — 4-space Python, 2-space JSON/TS/MD, tab Makefile.
- `LICENSE` — Proprietary notice.
- `backend/Dockerfile.dev` — для docker-compose worker profile.
- `backend/README.md`, `frontend/README.md`, `design/README.md`, `prompts/README.md`, `docs/iterations/README.md`, `apps/core/README.md`.
- `docs/design/principles.md` — placeholder с 6 UI principles до Pilot.

### 4.6. Скопировать iteration prompts → repo memory

- `prompts/iteration-4.5-audit.md` (для повторного запуска audit).
- `prompts/iteration-5-corrections.md` (для следующей итерации).
- `docs/iterations/iteration-4.5-audit-report.md` (memory of audit findings).

### 4.7. Validation

- `find . -type f | wc -l` — ожидаемое количество файлов (≥ 50).
- `find . -type d | wc -l` — ожидаемое количество директорий (≥ 35).
- `du -sh` — размер репозитория (< 1MB без 3 PDF из Project Knowledge — они НЕ копируются).
- `python -c "import tomllib; tomllib.load(open('backend/pyproject.toml','rb'))"` — TOML парсится.
- `find . -name "__init__.py" | wc -l` — 16 BC + 2 (apps/ + act/ + act/settings/) = 19.

### 4.8. Создать ZIP

```bash
cd /tmp && zip -r act-phase-0.zip act-build/ -x "*.DS_Store" "*__pycache__*"
```

Переименовать корневую папку при создании ZIP: `act-build/` → `act/` (чтобы после разархивации на macOS была папка `act/`).

-----

## 5. Финальная структура

```
act/
├── .claude/skills/{write-rls-policy,outbox-event}/SKILL.md
├── .editorconfig
├── .env.example
├── .gitattributes
├── .github/workflows/.gitkeep
├── .gitignore
├── .importlinter (в backend/)
├── CLAUDE.md
├── LICENSE
├── Makefile
├── README.md
├── apps/                    # legacy mount point — может быть удалён (используем backend/apps/)
├── backend/
│   ├── .importlinter
│   ├── Dockerfile.dev
│   ├── README.md
│   ├── act/{__init__.py, settings/__init__.py}
│   ├── apps/
│   │   ├── core/{__init__.py, README.md}
│   │   ├── identity_auth/{__init__.py, CLAUDE.md}
│   │   ├── <14 other BC>/__init__.py
│   │   └── __init__.py
│   ├── pyproject.toml
│   └── tests/.gitkeep
├── design/
│   ├── README.md
│   ├── journeys/.gitkeep
│   └── wireframes/.gitkeep
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   ├── PRODUCT.md
│   ├── design/
│   │   ├── decisions/.gitkeep
│   │   └── principles.md
│   ├── iterations/
│   │   ├── README.md
│   │   └── iteration-4.5-audit-report.md
│   ├── jtbd-bc-mapping.md
│   ├── pilot/day-template.md
│   └── risk-register.md
├── docker-compose.yml
├── frontend/
│   ├── README.md
│   ├── app/.gitkeep
│   ├── components/{identity,events,rsvp,shared}/.gitkeep
│   ├── messages/{ru,en}.json
│   ├── public/.gitkeep
│   └── styles/.gitkeep
├── infra/
│   ├── coolify/.gitkeep
│   ├── github-actions/.gitkeep
│   └── postgres/init.sql
├── prompts/
│   ├── README.md
│   ├── iteration-4.5-audit.md
│   └── iteration-5-corrections.md
└── scripts/.gitkeep
```

-----

## 6. Финальный ответ founder'у

После создания ZIP — структурировать ответ в **4 секции**:

1. **Inventory table** — список всех файлов с категорией (main / iteration-4 / scaffolding / supporting).
2. **ZIP metadata** — размер, количество файлов, контрольная сумма (SHA-256).
3. **Команды для macOS** — разархивация → git init → first commit → GitHub push.
4. **Roadmap dalshe** — следующая Iteration (5: corrections to 4 main files).

В самом конце — `present_files` со ссылкой на ZIP.

-----

## 7. Защита от типовых ошибок

1. **НЕ копировать PDF** из `/mnt/project/` (3 PDF = 12MB; они — исходный research, не часть репо).
2. **НЕ создавать `package.json`** в `frontend/` (Phase 1 task через `pnpm create next-app`).
3. **НЕ создавать `manage.py`** в `backend/` (Phase 1 task через `django-admin startproject`).
4. **НЕ инициализировать git** локально (founder сам решает remote URL).
5. **НЕ менять содержимое 4 главных файлов** (Iteration 5 их обновляет).
6. **НЕ забыть** `.gitkeep` в пустых директориях — иначе git их не сохранит.
7. **НЕ создавать дубли** `apps/` в root + `backend/apps/`. Только `backend/apps/`.

-----

*Конец промта Iteration 0.*
