"""Core HTTP views — public infrastructure endpoints only.

Phase 1.4: только healthz (liveness probe для Coolify / Yandex CLB).
Никаких DB-проверок — heavy readiness probe — отдельный endpoint в W10.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.http import JsonResponse
from django.views.decorators.http import require_GET

if TYPE_CHECKING:
    from django.http import HttpRequest


@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness probe — возвращает 200 если процесс запущен."""
    return JsonResponse({"status": "ok", "version": "0.1.0"})
