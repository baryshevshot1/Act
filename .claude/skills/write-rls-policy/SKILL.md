---
name: write-rls-policy
description: Writes a PostgreSQL Row-Level Security policy with FORCE + RESTRICTIVE default_deny for a Django model. Use when adding multi-tenant tables, when user says "add RLS", "enable row level security", "tenant isolation policy", or when creating models in apps that handle PII or user-attributed data (identity_auth, rsvp, contacts_sharing, verification, notifications, ratings).
allowed-tools: [Read, Write, Edit, Bash]
---

# Write RLS Policy (FORCE + RESTRICTIVE default_deny)

> **NON-NEGOTIABLE #11** [F: `CLAUDE.md` строка 141]: `SET LOCAL app.current_user_id` внутри `transaction.atomic()`; каждая RLS-таблица обязана иметь `FORCE ROW LEVEL SECURITY` + RESTRICTIVE `default_deny` policy.

## When to use

- Новая модель в BC, где хранятся user-attributed данные: identity_auth (`User`, `Session`, `Passkey`, `ConsentRecord`), rsvp (`EventParticipant`, `GuestRSVP`), contacts_sharing (`UserContactChannel`, `ContactShare`), verification (`VerificationDocument`), notifications (`NotificationDelivery`), ratings (`Rating`), recommendations (`RecommendationsScoreCache`).
- Существующая модель приобретает поле `user_id` или `owner_id`.
- Модель находится в перечне `CLAUDE.md` строка 101.

## When NOT to use

- Справочники без user-binding: `Country`, `City`, `Locale`, `Category`, `Tag` — RLS не нужна.
- Read-only public каталог (Discovery feed) — RLS не нужна, защита на app-level через explicit filtering.

## Шаги

### 1. Проверить модель

Открыть `apps/<ctx>/models.py`; убедиться, что поле для isolation существует и имеет правильный тип:

- `user_id UUID` — FK to `identity_auth_user` (UUIDv7 PK reference per `CLAUDE.md` строка 104).
- ИЛИ `owner_id UUID` — то же.
- ИЛИ через event_id → `events_event.owner_id` (паттерн для RSVP, см. PDF V1.3 секция 20.5).

### 2. Создать пустую миграцию

```bash
python backend/manage.py makemigrations <ctx> --empty -n enable_rls_<model_name>
```

### 3. Заполнить миграцию по шаблону

> **Verbatim шаблон** (адаптирован из `ARCHITECTURE.md` Level C Identity & Auth):

```python
# apps/<ctx>/migrations/00XX_enable_rls_<model>.py
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('<ctx>', '00XX-1_previous_migration'),
    ]
    operations = [
        migrations.RunSQL(
            sql="""
                -- 1. Enable RLS
                ALTER TABLE <ctx>_<table> ENABLE ROW LEVEL SECURITY;

                -- 2. FORCE: даже owner таблицы подчиняется RLS (NON-NEGOTIABLE #11)
                ALTER TABLE <ctx>_<table> FORCE ROW LEVEL SECURITY;

                -- 3. RESTRICTIVE default_deny: fail-closed default
                CREATE POLICY <ctx>_<table>_default_deny ON <ctx>_<table>
                    AS RESTRICTIVE
                    FOR ALL TO PUBLIC
                    USING (false);

                -- 4. PERMISSIVE policy: открывает доступ для owner
                -- ВАЖНО: (select ...) обёртка кеширует initPlan на весь запрос
                -- (~10-100x speedup vs прямой current_setting — pganalyze.com).
                CREATE POLICY <ctx>_<table>_owner ON <ctx>_<table>
                    AS PERMISSIVE
                    FOR ALL
                    USING (
                        user_id = (select current_setting('app.current_user_id'))::uuid
                    );
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

### 4. Запустить миграцию **через прямой PG, минуя PgBouncer** (NON-NEGOTIABLE #11)

```bash
PG_BOUNCER_HOST="" python backend/manage.py migrate <ctx>
# или через Makefile:
make migrate-direct
```

### 5. Написать тест RLS изоляции

В `apps/<ctx>/tests/test_<model>_rls.py`:

```python
import pytest
from django.db import connection


@pytest.mark.rls
def test_<model>_rls_two_tenants_isolated(db, two_tenants_with_<model>):
    """Tenant A не видит данные tenant B и наоборот."""
    user_a, user_b, obj_a, obj_b = two_tenants_with_<model>

    # As tenant A
    with connection.cursor() as cur:
        cur.execute("SELECT set_config('app.current_user_id', %s, true)", [str(user_a.id)])
        cur.execute("SELECT id FROM <ctx>_<table>")
        rows = cur.fetchall()

    assert obj_a.id in [r[0] for r in rows]
    assert obj_b.id not in [r[0] for r in rows]
```

## Verbatim examples из Level C

### Identity & Auth — session (`ARCHITECTURE.md` Level C + PDF V1.3 секция 20.2)

```sql
ALTER TABLE identity_auth_session ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_auth_session FORCE ROW LEVEL SECURITY;
CREATE POLICY identity_auth_session_default_deny ON identity_auth_session
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY session_owner ON identity_auth_session
    USING (user_id = (select current_setting('app.current_user_id'))::uuid);
```

### RSVP — guest visible to event owner (PDF V1.3 секция 20.5)

```sql
ALTER TABLE rsvp_guest_rsvp ENABLE ROW LEVEL SECURITY;
ALTER TABLE rsvp_guest_rsvp FORCE ROW LEVEL SECURITY;
CREATE POLICY rsvp_guest_rsvp_default_deny ON rsvp_guest_rsvp
    AS RESTRICTIVE FOR ALL TO PUBLIC USING (false);
CREATE POLICY guest_visible_to_owner ON rsvp_guest_rsvp FOR SELECT
    USING (
        event_id IN (
            SELECT id FROM events_event
            WHERE owner_id = (select current_setting('app.current_user_id'))::uuid
        )
    );
```

## Pitfalls (что НЕ делать)

- **НЕ забывать FORCE** — без него owner таблицы (роль `act_app`) bypass'ит политику. Default Postgres allows table-owner bypass; `FORCE ROW LEVEL SECURITY` это закрывает.
- **НЕ забывать RESTRICTIVE `default_deny`** — fail-closed default. Без него отсутствие PERMISSIVE-матча даёт «allow» в некоторых сценариях.
- **НЕ использовать `pgcrypto`** для application-level encryption — отвергнут в ADR-014 (ключ передаётся в БД в plain; Yandex admin видит ключ через `pg_stat_activity`). Использовать `django-cryptography` + Yandex Lockbox.
- **НЕ оборачивать `current_setting` без `(select ...)`** — без обёртки PG не кеширует initPlan, и при больших таблицах policy эвалюируется row-by-row (~100× slower). Источник: pganalyze.com/blog/postgres-row-level-security-django-python.
- **НЕ запускать миграцию через PgBouncer** — `CREATE EXTENSION` и advisory locks не совместимы с transaction-pooling. Использовать `PG_BOUNCER_HOST=""` или `make migrate-direct`.
- **НЕ забывать тест RLS изоляции** — без двух-tenant fixture тесты пройдут на одном tenant и пропустят утечку.
- **НЕ забывать `SET LOCAL` внутри `transaction.atomic()`** [F: NON-NEGOTIABLE #11] — PgBouncer transaction-pooling возвращает connection в pool после COMMIT; без `LOCAL` это cross-tenant leak.

## После применения миграции

1. Проверить `lint-imports` — не сломал ли change cross-context boundaries.
2. Запустить тесты RLS: `pytest -m rls` (или `make test-rls`).
3. Обновить ADR если меняется существующая стратегия; либо добавить snippet в соответствующий Level C в `docs/ARCHITECTURE.md`.
4. Записать в `docs/CHANGELOG.md` в секции `[Unreleased]` → `Added`.
