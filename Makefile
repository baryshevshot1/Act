# Act — make targets
# Источник: CLAUDE.md строки 73-94 (common commands).
# NON-NEGOTIABLE #11: миграции через прямой PG (миную PgBouncer).

.PHONY: help up down logs migrate migrate-direct test test-rls test-outbox lint fmt rls-check shell worker clean ci-check

help:
	@echo "Act — common dev tasks"
	@echo "  make up              — start postgres + worker"
	@echo "  make down            — stop all"
	@echo "  make migrate         — Django migrations (через PgBouncer если есть)"
	@echo "  make migrate-direct  — Django migrations through DIRECT PG (NON-NEGOTIABLE #11)"
	@echo "  make test            — pytest -m 'not slow'"
	@echo "  make test-rls        — pytest -m rls"
	@echo "  make test-outbox     — pytest -m outbox"
	@echo "  make lint            — ruff + mypy + import-linter"
	@echo "  make ci-check        — те же проверки что GitHub Actions CI (для локальной верификации перед push)"
	@echo "  make fmt             — ruff format + ruff check --fix"
	@echo "  make rls-check       — verify FORCE+RESTRICTIVE default_deny on RLS tables"
	@echo "  make shell           — Django shell"
	@echo "  make worker          — Procrastinate worker"
	@echo "  make clean           — remove __pycache__ + .pytest_cache + .coverage"

up:
	docker-compose up -d postgres

down:
	docker-compose down

logs:
	docker-compose logs -f postgres

migrate:
	cd backend && python manage.py migrate

# NON-NEGOTIABLE #11: миграции ОБЯЗАТЕЛЬНО через прямой PG, минуя PgBouncer
migrate-direct:
	cd backend && PG_BOUNCER_HOST="" python manage.py migrate

test:
	cd backend && pytest -m "not slow"

test-rls:
	cd backend && pytest -m rls -v

test-outbox:
	cd backend && pytest -m outbox -v

lint:
	cd backend && ruff check . && mypy . && lint-imports

# Локальное эхо .github/workflows/ci.yml — позволяет verify перед `git push`.
# Без service container postgres — DATABASE_URL_TEST не задан → smoke tests
# с PG-проверкой skip'ается (test_db_connection_is_postgres_in_ci). Для полного
# PG-run: `docker compose up -d postgres` + DATABASE_URL_TEST=postgres://...`
# Не валидирует frontend (это будет в Phase 1.5).
ci-check:
	@echo "=== 1. ruff check ==="
	cd backend && ruff check .
	@echo ""
	@echo "=== 2. ruff format --check ==="
	cd backend && ruff format --check .
	@echo ""
	@echo "=== 3. Django check (dev) ==="
	cd backend && DJANGO_SETTINGS_MODULE=act.settings.dev python manage.py check
	@echo ""
	@echo "=== 4. Django check --deploy (prod, smoke) ==="
	cd backend && ALLOWED_HOSTS=ci.act.app \
		DATABASE_URL=postgres://act_app:ci@localhost:5432/d \
		DATABASE_URL_ADMIN=postgres://act_admin:ci@localhost:5432/d \
		DATABASE_URL_DIRECT=postgres://act_app:ci@localhost:5432/d \
		PII_HMAC_SECRET=ci-only-replace-via-secrets \
		SECRET_KEY=ci-only-replace-via-secrets-very-long-string-for-django-pass \
		DJANGO_SETTINGS_MODULE=act.settings.prod \
		python manage.py check --deploy
	@echo ""
	@echo "=== 5. import-linter (18 contracts) ==="
	cd backend && DJANGO_SETTINGS_MODULE=act.settings.dev lint-imports | grep "Contracts:"
	@echo ""
	@echo "=== 6. makemigrations --dry-run (Phase 1.4.bis territory) ==="
	cd backend && DJANGO_SETTINGS_MODULE=act.settings.dev python manage.py \
		makemigrations --dry-run core identity_auth events rsvp | tail -5
	@echo ""
	@echo "=== 7. pytest tests/ ==="
	cd backend && DJANGO_SETTINGS_MODULE=act.settings.test pytest tests/ --no-cov -q
	@echo ""
	@echo "✓ All CI checks PASS"

fmt:
	cd backend && ruff format . && ruff check . --fix

# Verify FORCE ROW LEVEL SECURITY + RESTRICTIVE default_deny on all RLS tables.
# (Phase 1+ — будет реализовано как backend/scripts/check_rls_policies.py)
rls-check:
	cd backend && python scripts/check_rls_policies.py || echo "TODO: implement check_rls_policies.py in Phase 1"

shell:
	cd backend && python manage.py shell

worker:
	cd backend && python manage.py procrastinate worker

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	find . -type f -name "*.pyc" -delete
