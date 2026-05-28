"""Smoke tests — Phase 1.6 (CI bootstrap).

[F: docs/iterations/iteration-5.5-roadmap.md step #17]

Цель: каждый тест = strong signal что одна из ключевых assumptions Phase 1.4
не сломана. Минимальный scope; per-BC unit-тесты появятся в W1+.

Запуск:
    # Локально (SQLite fallback):
    DJANGO_SETTINGS_MODULE=act.settings.test pytest backend/tests/test_smoke.py
    # CI / реальный PG17:
    DATABASE_URL_TEST=postgres://... DJANGO_SETTINGS_MODULE=act.settings.test \
        pytest backend/tests/test_smoke.py
"""

from __future__ import annotations

import os

import django
import pytest
from django.db import connection
from django.test import Client


def test_django_version_is_5_2() -> None:
    """Frozen stack invariant: Django 5.2 LTS (ADR-002).

    Защищает от accidental bump на 6.0 — major bump требует ADR-002 update.
    """
    assert django.VERSION[:2] == (5, 2), (
        f"Frozen stack ожидает Django 5.2 LTS; реально {django.__version__}. "
        "Смотри ADR-002 в docs/ARCHITECTURE.md."
    )


def test_healthz_returns_200() -> None:
    """`/healthz/` доступен без auth и возвращает {status: ok}.

    Покрывает:
    - URL routing работает (act/urls.py).
    - View loads (apps.core.views.healthz).
    - CSP/RLS middleware stack не ломает базовый request.
    """
    response = Client().get("/healthz/")
    assert response.status_code == 200, response.content
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_db_connection_is_postgres_in_ci() -> None:
    """В CI ожидается PG17 (DATABASE_URL_TEST set).

    Локально без DATABASE_URL_TEST = SQLite — этот ассерт skip'ается.
    Гарантирует что CI реально гоняется на target backend (frozen stack).

    Намеренно БЕЗ `@pytest.mark.django_db` — этот marker заставил бы pytest-django
    создать test DB через `migrate`, что упало бы на ArrayField в SQLite local
    run. Здесь нужно только открыть connection и запросить version() — никаких
    моделей не трогается.
    """
    if not os.environ.get("DATABASE_URL_TEST"):
        pytest.skip("local SQLite run; PG17 проверяется только в CI")

    assert connection.vendor == "postgresql", (
        f"DATABASE_URL_TEST set, но backend = {connection.vendor!r}. "
        "Проверь _parse_db_url в act/settings/base.py."
    )

    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        version_string = cursor.fetchone()[0]

    assert "PostgreSQL 17" in version_string, (
        f"Frozen stack ожидает PG 17, реально: {version_string}"
    )
