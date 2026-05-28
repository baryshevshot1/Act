#!/usr/bin/env python
"""Django CLI entry-point.

[F: CLAUDE.md «Common commands»] — все manage.py команды запускаются отсюда.
Production deploy hook (Coolify pre-deploy):
    PG_BOUNCER_HOST="" python manage.py migrate --noinput
[NON-NEGOTIABLE #11 — миграции через прямой PG, минуя PgBouncer.]
"""

import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "act.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django. Are you in the right virtualenv?") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
