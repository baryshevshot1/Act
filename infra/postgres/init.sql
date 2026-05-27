-- Act — PostgreSQL initialization for local dev
-- Источник: ADR-006 (Required PostgreSQL extensions) + ARCHITECTURE.md.
-- В production: эти extensions нужно проверить в allowlist Yandex Managed PG 17.
--
-- Roles:
-- - act_app — основная роль приложения (БЕЗ BYPASSRLS, подчиняется RLS).
--   Создаётся автоматически через POSTGRES_USER в docker-compose.yml.
-- - act_admin — роль для Django Admin (с BYPASSRLS, для emergency ops + Django admin).
--   Создаётся отдельной Django миграцией в backend (после Phase 1 bootstrap).
--   Все mutations через act_admin ОБЯЗАТЕЛЬНО логируются в audit_log_pii_access
--   [F: CLAUDE.md строка 124].

-- Required extensions (ADR-006).
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- pg_uuidv7: нужно проверить allowlist в Yandex Managed PG 17.
-- В локальном PG 17 alpine — нужно установить вручную или использовать
-- uuid-utils из Python (см. ADR-006 Caveat).
-- CREATE EXTENSION IF NOT EXISTS pg_uuidv7;
