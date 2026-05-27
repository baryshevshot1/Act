from django.apps import AppConfig


class IdentityAuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity_auth"
    label = "identity_auth"
    verbose_name = "Identity & Auth (root BC)"
