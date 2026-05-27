"""Content-Security-Policy middleware.

[F: docs/ARCHITECTURE.md «OWASP Top 10:2025» A06 Insecure Design]

Минимальный CSP для Phase 1.4 (dev-permissive). Tightening — W10 security review.
Заголовки накладываются на ВСЕ ответы, не зависят от транзакции/RLS.
django-csp не в pyproject.toml — hand-roll, ~20 строк.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


_DEFAULT_POLICY = (
    "default-src 'self'; "
    # 'unsafe-inline' для script-src OK на dev / skeleton; W10 review tighten до nonce.
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)


class CSPMiddleware:
    """Set `Content-Security-Policy` on every response.

    Не используем `Report-Only` — pre-MVP трафик мал, можно сразу enforce.
    """

    def __init__(self, get_response: Callable[["HttpRequest"], "HttpResponse"]) -> None:
        self.get_response = get_response

    def __call__(self, request: "HttpRequest") -> "HttpResponse":
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", _DEFAULT_POLICY)
        return response
