"""Project-level pytest configuration.

Per-BC conftest.py появится в `backend/apps/<bc>/tests/conftest.py` в W1+.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _allow_db_access_without_django_db_marker(django_db_blocker):  # type: ignore[no-untyped-def]
    """Allow DB access во всех smoke tests без `@pytest.mark.django_db`.

    Зачем:
    - RLS middleware (apps/core/rls/middleware.py) на PG обёртывает каждый
      request в `transaction.atomic()`. Это требует open DB connection
      даже для anon healthz-request. Без unblock pytest-django падает
      с RuntimeError "Database access not allowed".
    - `@pytest.mark.django_db` marker НЕ подходит — он триггерит `migrate`
      на test DB, что ломается на ArrayField в SQLite fallback (Phase 1.4
      design — миграции в 1.4.bis).

    Trade-off: unblock сессия использует **существующую** DB (act_ci в CI,
    SQLite `:memory:` локально). Тесты не пишут данные → side effects нет.
    Для будущих write-тестов в W1+ — отдельный conftest per-BC с
    explicit `@pytest.mark.django_db` + миграции готовы.

    See: pytest-django docs «Enabling database access in tests».
    """
    with django_db_blocker.unblock():
        yield
