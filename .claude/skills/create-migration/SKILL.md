---
name: create-migration
description: Creates a Django migration following expand-contract pattern, RLS table requirements, and PgBouncer compatibility rules. Use when user says "create migration", "add column", "rename column", "drop column", "alter table", "online migration", "zero-downtime migration", "expand-contract", or when modifying schema. NEVER use forbidden online ops (RENAME COLUMN, ADD COLUMN NOT NULL without default, DROP NOT NULL without default).
allowed-tools: [Read, Write, Edit, Bash]
---

# Create Django Migration (zero-downtime expand-contract + RLS + direct PG)

> **NON-NEGOTIABLE #11** [F: `CLAUDE.md` строка 141]: миграции прогоняются прямым подключением к PG, минуя PgBouncer (`CREATE INDEX CONCURRENTLY` и advisory locks не совместимы с transaction-pooling). См. `docs/ARCHITECTURE.md` § DB Migration Strategy + RLS Operational Constraints #6.

## When to use

- Любое изменение schema (ADD/DROP/ALTER column, CREATE INDEX, FK, constraint).
- Создание новой модели в BC (`apps/<ctx>/models.py`).
- Enabling RLS на существующей таблице (см. также skill `write-rls-policy`).
- Backfill больших таблиц (через Procrastinate task в составе expand-contract).

## When NOT to use

- Раннее: использовать `.raw()` queries — запрещено вне `apps.core.rls.*` (NN #11).
- Inline data-migrations внутри schema-migration — атомарные миграции отдельно от data ops [F: `CLAUDE.md` строка 100].
- Запуск миграции через `make up` или Coolify deploy без `PG_BOUNCER_HOST=""` override.

## Expand-Contract Pattern (4 шага)

> [F: Adam Johnson «Boost your Django DX» + `docs/ARCHITECTURE.md` строка 1704]

| Step | Action | Migration | Code change |
|---|---|---|---|
| 1. **Expand** | Add nullable column / new index / new field WITHOUT NOT NULL | One migration | None |
| 2. **Backfill** | Procrastinate periodic-task fills new column from old (batches 1k rows) | None | Task |
| 3. **Switch** | Application code reads from new column | None | Deploy code |
| 4. **Contract** | Drop old column (через 1-2 deploy cycles после Switch) | One migration | Deploy code |

## Шаги для типичной миграции

### 1. Создать миграцию

```bash
# Стандартная (если изменили models.py)
python backend/manage.py makemigrations <ctx>

# Пустая (для RLS / extensions / data ops)
python backend/manage.py makemigrations <ctx> --empty -n <descriptive_name>
```

### 2. Запустить через прямой PG (NN #11)

```bash
# Bypass PgBouncer — transaction-pooling несовместим с CREATE EXTENSION / advisory locks
PG_BOUNCER_HOST="" python backend/manage.py migrate <ctx>

# Или через Makefile target:
make migrate-direct
```

### 3. Coolify pre-deploy hook

В Coolify deploy config:

```yaml
pre_deploy: |
  PG_BOUNCER_HOST="" python manage.py migrate --noinput
```

## Запрещённые операции в online migration

[F: `docs/ARCHITECTURE.md` строка 1713]:

| Запрещено | Почему | Replacement |
|---|---|---|
| `RENAME COLUMN` | Django backend ломается до cutover | add new column + backfill + drop old |
| `DROP NOT NULL` без default | Existing rows валидируются (full scan) | First ADD COLUMN с default, потом DROP NOT NULL |
| `ADD COLUMN NOT NULL` без default | Lock на таблицу + полная переписка | ADD COLUMN NULL → backfill → ALTER SET NOT NULL |
| `ALTER COLUMN TYPE` для большой таблицы | Rewrite таблицы | add new + backfill + drop old |
| `ADD FOREIGN KEY` без `NOT VALID` | Full table scan | ADD FOREIGN KEY ... NOT VALID, потом `VALIDATE CONSTRAINT` отдельно |

## Pattern 1. Add nullable column (safe)

```python
# apps/events/migrations/00XX_add_event_color.py
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('events', '00XX-1_previous')]
    operations = [
        migrations.AddField(
            model_name='event',
            name='color',
            field=models.CharField(max_length=7, null=True, blank=True),
        ),
    ]
```

## Pattern 2. ADD COLUMN NOT NULL — expand-contract way

```python
# Migration A (Expand): add nullable
operations = [
    migrations.AddField(
        model_name='event', name='visibility',
        field=models.CharField(max_length=16, null=True),
    ),
]

# Task (Backfill in Procrastinate, batches 1k):
@app.periodic_task(...)
def backfill_event_visibility():
    Event.objects.filter(visibility__isnull=True).update(visibility='public')

# Migration B (Contract): set NOT NULL
operations = [
    migrations.AlterField(
        model_name='event', name='visibility',
        field=models.CharField(max_length=16, null=False, default='public'),
    ),
]
```

## Pattern 3. CREATE INDEX CONCURRENTLY (через direct PG)

```python
from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models

class Migration(migrations.Migration):
    atomic = False  # ОБЯЗАТЕЛЬНО — CONCURRENTLY не работает в transaction
    dependencies = [('events', '00XX-1_previous')]
    operations = [
        AddIndexConcurrently(
            model_name='event',
            index=models.Index(fields=['city_id', '-starts_at'], name='events_city_starts_idx'),
        ),
    ]
```

## Pattern 4. Enable RLS на существующей таблице

```python
# apps/<ctx>/migrations/00XX_enable_rls_<table>.py
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [('<ctx>', '00XX-1_previous')]
    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE <ctx>_<table> ENABLE ROW LEVEL SECURITY;
                ALTER TABLE <ctx>_<table> FORCE ROW LEVEL SECURITY;
                CREATE POLICY <ctx>_<table>_default_deny ON <ctx>_<table>
                    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
                CREATE POLICY <ctx>_<table>_owner ON <ctx>_<table>
                    USING (user_id = (select current_setting('app.current_user_id'))::uuid);
            """,
            reverse_sql="""
                DROP POLICY IF EXISTS <ctx>_<table>_owner ON <ctx>_<table>;
                DROP POLICY IF EXISTS <ctx>_<table>_default_deny ON <ctx>_<table>;
                ALTER TABLE <ctx>_<table> NO FORCE ROW LEVEL SECURITY;
                ALTER TABLE <ctx>_<table> DISABLE ROW LEVEL SECURITY;
            """,
        ),
    ]
```

См. полный workflow в skill `write-rls-policy`.

## Pattern 5. ADD FOREIGN KEY с NOT VALID

```python
operations = [
    migrations.RunSQL(
        sql="""
            ALTER TABLE events_event ADD CONSTRAINT events_event_owner_fkey
                FOREIGN KEY (owner_id) REFERENCES identity_auth_user(id)
                NOT VALID;
            -- Отдельная migration для VALIDATE (lock не блокирует write):
            -- ALTER TABLE events_event VALIDATE CONSTRAINT events_event_owner_fkey;
        """,
    ),
]
```

## Pitfalls

- **НЕ забывать `PG_BOUNCER_HOST=""`** при migrate — CREATE EXTENSION падает через transaction-pooling.
- **НЕ использовать `atomic = True`** (default) с `AddIndexConcurrently` — CONCURRENTLY требует отдельной транзакции.
- **НЕ rename column в одной миграции** — Django backend ломается между «миграция применена» и «новый код задеплоен».
- **НЕ ADD COLUMN NOT NULL без default** на большой таблице — lock + full table rewrite.
- **НЕ забывать `reverse_sql`** для `RunSQL` — нужно для `migrate --rollback`.
- **НЕ data-migrations внутри schema-migration** — separate Procrastinate task; schema migrations должны быть idempotent + быстрые.
- **НЕ забывать RLS** на новой user-attributed таблице (NN #11). Используй skill `write-rls-policy`.
- **НЕ забывать `lint-imports`** после миграции — может выявиться cross-context импорт, который раньше работал implicitly.
- **НЕ забывать VALIDATE CONSTRAINT** для FK с NOT VALID — без VALIDATE таблица остаётся в «inconsistent» состоянии.
- **НЕ забывать тесты** — pytest fixture с RLS + миграция + assertion на schema.

## Cost guard

- Большие миграции (rewrite таблицы > 1M rows) — запускать в maintenance window.
- Для backfill — Procrastinate task с rate limit (1k rows/min) чтобы не вешать PG.
- Yandex Managed PG имеет CPU autoscaling alerts — monitor MTD ≤ 5000 ₽ (см. Cost Monitoring).

## После применения миграции

1. `make migrate-direct` (или `PG_BOUNCER_HOST="" python manage.py migrate`).
2. `python manage.py showmigrations <ctx>` — verify applied.
3. `lint-imports` — boundaries сохранены.
4. `pytest -m rls` — RLS изоляция работает.
5. `pytest -m slow` — backfill task выполнен (если применимо).
6. Записать в `docs/CHANGELOG.md` § Unreleased → Added/Changed.
