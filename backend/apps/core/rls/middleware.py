"""RLS context middleware.

[F: docs/ARCHITECTURE.md «RLS Operational Constraints» #1]
[F: CLAUDE.md NON-NEGOTIABLE #11]

`SET LOCAL` живёт только до COMMIT; PgBouncer в transaction-pooling режиме
возвращает connection в pool после commit. Без оборачивания в
`transaction.atomic()` следующий запрос на этом же физическом коннекте получит
чужой `app.current_user_id` — **cross-tenant leak / CVE.**

Anonymous users → NULL_UUID — RLS PERMISSIVE policies fail-match (default_deny
блокирует доступ ко всем RLS-таблицам). Это ожидаемое поведение: anon
получают только public read-only данные (Discovery feed, published Events),
которые не имеют RLS вообще либо имеют public-permissive policy.

Pitfall: middleware ОБЯЗАН быть после AuthenticationMiddleware
(нужен `request.user`). Порядок зафиксирован в `act.settings.base.MIDDLEWARE`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from django.db import connection, transaction

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class RLSContextMiddleware:
    """Set GUC `app.current_user_id` for the duration of each request.

    На non-PG backends (SQLite в dev/tests) middleware no-op'ит — `set_config()`
    не существует в SQLite, и попытка вызвать его сломает каждый запрос
    в `manage.py check`/тестах. RLS работает только в PG.
    """

    NULL_UUID = "00000000-0000-0000-0000-000000000000"

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if connection.vendor != "postgresql":
            return self.get_response(request)

        user_id = (
            str(request.user.id)
            if getattr(request, "user", None) and request.user.is_authenticated
            else self.NULL_UUID
        )
        with transaction.atomic():
            with connection.cursor() as cursor:
                # `set_config(name, value, is_local=true)` идентично `SET LOCAL`,
                # но возвращает значение — удобнее для логирования.
                # [F: pganalyze.com/blog/postgres-row-level-security-django-python]
                cursor.execute(
                    "SELECT set_config('app.current_user_id', %s, true)",
                    [user_id],
                )
            return self.get_response(request)
