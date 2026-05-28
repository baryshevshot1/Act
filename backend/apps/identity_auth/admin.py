"""Django Admin — минимальная регистрация.

Кастомные ModelAdmin (PII redaction в list_display, action логирование
в audit_log_pii_access) — W9 sprint (Admin Console).

В production Django Admin использует DATABASES['admin'] (act_admin role
с BYPASSRLS) — RLS Operational Constraint #4. Routing — через decorator
@using('admin') или middleware-based switcher в W9.
"""
from django.contrib import admin

from .models import (
    AuthEvent,
    ConsentRecord,
    MagicLinkToken,
    OAuthIdentity,
    OAuthProvider,
    PasskeyCredential,
    Session,
    User,
)

admin.site.register(User)
admin.site.register(Session)
admin.site.register(MagicLinkToken)
admin.site.register(OAuthProvider)
admin.site.register(OAuthIdentity)
admin.site.register(PasskeyCredential)
admin.site.register(ConsentRecord)
admin.site.register(AuthEvent)
