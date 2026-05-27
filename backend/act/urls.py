"""Root URL conf.

На Phase 1.4 (skeleton):
    /healthz/           → liveness probe (без DB check)
    /accounts/          → django-allauth (default flows; Telegram adapter — W1)
    /admin/             → Django Admin (RLS bypass через act_admin DB role в prod)

API routes (api/v1/...) appear в W1+ как app.urls в каждом BC.
"""
from django.contrib import admin
from django.urls import include, path

from apps.core.views import healthz

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]
