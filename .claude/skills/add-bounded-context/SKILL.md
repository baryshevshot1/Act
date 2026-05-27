---
name: add-bounded-context
description: Scaffolds a new Bounded Context in apps/<ctx>/ following Act modular monolith conventions — contracts.py (DTOs), services.py (ORM-only here), models.py, .importlinter contract, optional CLAUDE.md. Use when adding a 17th BC beyond the original 16, when user says "add bounded context", "new BC", "create context", "new domain module". Cross-context calls go through contracts.py only (ADR-001 + import-linter).
allowed-tools: [Read, Write, Edit, Bash]
---

# Add Bounded Context (modular monolith scaffolding)

> **ADR-001** [F: `docs/ARCHITECTURE.md` § ADR-001]: modular monolith с 16 bounded contexts; cross-context calls — только через `apps.<ctx>.contracts`; enforcement через `import-linter`. Если добавляется 17-й BC — он встраивается в эту дисциплину.

## When to use

- Появилась новая domain concern, которая не помещается в существующие 16 BC.
- Спин-офф из существующего BC (e.g. `events` → `events` + `recurrence_engine` — пример уже сделан).
- Pre-Pilot / pre-Phase 1 проектирование добавки BC (ADR пишется ДО кода, см. skill `write-adr`).

## When NOT to use

- Просто новый model в существующем BC — это не новый BC, добавь в `apps/<existing_ctx>/models.py`.
- Helper / utility которая нужна нескольким BC — это `apps.core.*` (shared infrastructure), не отдельный BC.
- «Микро-сервис» желание — отвергнуто в ADR-001; modular monolith — final.

## Prerequisites (gate перед началом)

1. **ADR написан** (skill `write-adr`) с обоснованием почему новый BC нужен.
2. **Level C сделан** в `docs/ARCHITECTURE.md` (или хотя бы Level C light: aggregates + services signatures + cross-context dependencies + RLS-tables list).
3. **JTBD mapping** обновлён в `docs/jtbd-bc-mapping.md`.
4. **Wave 3 risk register** обновлён если новый BC обрабатывает PII или новых ТППД-получателей.

## Шаги создания

### 1. Создать директорию-каркас

```bash
mkdir -p backend/apps/<ctx>/{migrations,tests,management/commands}
touch backend/apps/<ctx>/__init__.py
touch backend/apps/<ctx>/{apps.py,models.py,services.py,contracts.py,subscribers.py,signals.py,admin.py,urls.py,views.py}
touch backend/apps/<ctx>/migrations/__init__.py
touch backend/apps/<ctx>/tests/__init__.py
```

### 2. `apps.py` — Django app config

```python
# backend/apps/<ctx>/apps.py
from django.apps import AppConfig

class <Ctx>Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # UUIDv7 на explicit fields
    name = 'apps.<ctx>'
    label = '<ctx>'  # Django app label (без apps. prefix)
```

### 3. `contracts.py` — public DTOs + service signatures (single source for cross-context)

```python
# backend/apps/<ctx>/contracts.py
"""
Public API of <Ctx> bounded context.
Other BCs import ONLY from this module (enforced via import-linter).
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True, slots=True)
class <Entity>DTO:
    id: UUID
    # ... only safe-to-expose fields, no PII raw values ...
    created_at: datetime

# Service signatures (real impl в services.py — cross-context импорт ТОЛЬКО этих names)
def get_<entity>_by_id(*, <entity>_id: UUID) -> <Entity>DTO | None: ...
def create_<entity>(*, ...) -> <Entity>DTO: ...
```

### 4. `services.py` — единственное место ORM-доступа

```python
# backend/apps/<ctx>/services.py
"""
ORM-доступ ТОЛЬКО здесь. Views / handlers / templates НЕ обращаются к ORM напрямую.
"""
from uuid import UUID
from django.db import transaction
from apps.<ctx>.models import <Entity>
from apps.<ctx>.contracts import <Entity>DTO
from apps.core.outbox.services import publish_event

def get_<entity>_by_id(*, <entity>_id: UUID) -> <Entity>DTO | None:
    try:
        instance = <Entity>.objects.get(id=<entity>_id)
        return <Entity>DTO(id=instance.id, ..., created_at=instance.created_at)
    except <Entity>.DoesNotExist:
        return None

def create_<entity>(*, user_id: UUID, ...) -> <Entity>DTO:
    with transaction.atomic():
        instance = <Entity>.objects.create(owner_id=user_id, ...)
        publish_event(
            event_type='<Entity>Created',
            aggregate_type='<Entity>',
            aggregate_id=instance.id,
            payload={...},
        )
        return <Entity>DTO(...)
```

### 5. `models.py` — Django ORM models

```python
# backend/apps/<ctx>/models.py
import uuid
from django.db import models

def uuidv7():
    """PG-side через uuidv7() extension; fallback на server-side для tests."""
    from psycopg2.extras import execute_values  # placeholder
    return uuid.uuid4()  # in tests; production uses PG function

class <Entity>(models.Model):
    id = models.UUIDField(primary_key=True, default=uuidv7, editable=False)
    owner_id = models.UUIDField(db_index=True)  # FK к identity_auth_user (не CASCADE — RESTRICT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = '<ctx>_<entity>'
        indexes = [
            models.Index(fields=['owner_id', '-created_at']),  # под RLS policy
        ]
```

### 6. Добавить в `INSTALLED_APPS` (Phase 1+)

```python
# backend/act/settings/base.py
INSTALLED_APPS = [
    ...,
    'apps.<ctx>',
]
```

### 7. Добавить контракт в `.importlinter`

```ini
# backend/.importlinter — добавить новый контракт isolation
[importlinter:contract:<ctx>-isolation]
name = <Ctx> isolation (ADR-001)
type = forbidden
source_modules =
    apps.<ctx>
forbidden_modules =
    apps.identity_auth.models
    apps.identity_auth.services
    apps.events.models
    apps.events.services
    # ... все 15 других BC по models и services (НЕ contracts) ...
```

И добавить новый BC в **CONTRACT 0** (no-raw-sql-outside-core-rls) `source_modules` блок.

### 8. (Опционально) Создать per-context `CLAUDE.md`

```bash
touch backend/apps/<ctx>/CLAUDE.md
```

См. шаблон в `backend/apps/identity_auth/CLAUDE.md`: ≤100 строк, секции «Context · Entities · Conventions · Cross-context dependencies · Common pitfalls». Загружается Claude Code on-demand при работе с этим BC.

### 9. Создать первую миграцию

```bash
PG_BOUNCER_HOST="" python backend/manage.py makemigrations <ctx>
PG_BOUNCER_HOST="" python backend/manage.py migrate <ctx>
```

### 10. Если есть user-attributed данные — Enable RLS

См. skill `write-rls-policy` (FORCE + RESTRICTIVE default_deny).

## Verbatim — структура существующего BC

```
backend/apps/identity_auth/
├── __init__.py
├── apps.py              # AppConfig
├── CLAUDE.md            # per-context AI hints (опционально, recommended)
├── admin.py             # Django admin views (под act_admin BYPASSRLS)
├── contracts.py         # public DTOs + service signatures
├── models.py            # Django ORM models
├── services.py          # ORM-доступ ТОЛЬКО здесь
├── signals.py           # intra-context only (не cross-context — ADR-016)
├── subscribers.py       # Outbox subscribers (на events других BC)
├── urls.py              # routing
├── views.py             # API handlers — НЕ ORM, только services
├── migrations/
└── tests/
```

## Pitfalls

- **НЕ импортировать `apps.<other_ctx>.models`** — только `apps.<other_ctx>.contracts`. `.importlinter` отловит, но лучше не давать ему шансов.
- **НЕ использовать `prefetch_related` / `select_related` за пределами services.py** — размывает границы; всё ORM-доступ в services.py.
- **НЕ обращаться в БД из views/handlers** напрямую — только через services.py.
- **НЕ забывать `default_auto_field`** — Django 5.2 default = BigAutoField, но мы используем UUIDField explicit. Явный `db_table` тоже recommended.
- **НЕ забывать RLS** на любой user-attributed таблице (NN #11). Используй skill `write-rls-policy`.
- **НЕ забывать `signals.py` vs `subscribers.py`** — `signals.py` для intra-context (`post_save` validation); `subscribers.py` для cross-context Outbox events (skill `outbox-event`).
- **НЕ забывать обновить** `docs/ARCHITECTURE.md` § 16 bounded contexts (теперь 17), `docs/jtbd-bc-mapping.md`, `docs/CHANGELOG.md` § Added.
- **НЕ забывать обновить `apps/identity_auth/CLAUDE.md` Cross-context dependencies секцию** если новый BC consumes user data.

## Cross-context эффекты

- Любой BC может subscribe-нуться на events нового BC через `subscribers.py` + skill `outbox-event`.
- Новый BC может consume contracts существующих BC — но НЕ их `models.py` или `services.py`.
- Если BC обрабатывает PII (phone, email, geo, photo) — обязательны ADR-014 encryption и `audit_log_pii_access` (Wave 3).

## После создания

1. `lint-imports` — все контракты pass.
2. `pytest backend/apps/<ctx>/tests/` — basic smoke tests на services.
3. Обновить `docs/ARCHITECTURE.md` секцию «16 bounded contexts» (теперь 17, или указать что 17-й BC появился в Wave N).
4. Обновить `docs/jtbd-bc-mapping.md` с привязкой к JTBD.
5. Создать ADR (skill `write-adr`) если ещё не создан.
6. Записать в `docs/CHANGELOG.md` § Added — «New BC: <Ctx> — purpose, JTBD served, dependencies».
