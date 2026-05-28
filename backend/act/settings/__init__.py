# Django settings package — layered.
# Точки входа:
# - base.py — общие настройки, читает env через os.environ
# - dev.py  — local development (DEBUG=True, SQLite fallback если DATABASE_URL не задан)
# - test.py — pytest-django (см. pyproject.toml: DJANGO_SETTINGS_MODULE = "act.settings.test")
# - prod.py — Yandex Cloud + Coolify; DATABASE_URL_DIRECT для миграций (NN #11)
