# Act — Root CLAUDE.md

## STACK (frozen V1.2, do not propose alternatives)
- Backend: Django 5.2 LTS + Python 3.12 + PostgreSQL 17 (Yandex Managed)
- Frontend: Next.js 16 App Router + next-intl + TypeScript
- Jobs: Procrastinate 3.8 (Postgres-backed). NEVER suggest Celery/Redis.
- Search: PostgreSQL FTS (tsvector + GIN). NEVER suggest Elasticsearch/Meilisearch.
- Hosting: Yandex Cloud + Coolify. NEVER assume Vercel/Heroku/AWS managed.
- Auth: django-allauth (Telegram OIDC primary, magic-link fallback) + django-otp-webauthn.

## CONVENTIONS
- Modular monolith with 16 bounded contexts under backend/apps/.
- Cross-context calls ONLY via apps.<ctx>.contracts (DTOs).
- ORM lives in services.py — views/route-handlers MUST NOT touch ORM directly.
- RLS is mandatory for tables containing user-attributed data.
- All datetimes UTC in DB; locale conversion in services or frontend.
- All migrations atomic; no data migrations in schema migration.
- Conventional Commits: feat:, fix:, chore:, docs:, refactor:, test:.

## REPO LAYOUT
- backend/   — Django modular monolith; apps/ под bounded contexts (создаётся в Phase 1)
- frontend/  — Next.js App Router [locale]/(public)/(authenticated)/(organizer)/ (Phase 1)
- infra/     — Docker Compose, Coolify config, Terraform (later)
- docs/      — ADR (docs/decisions/), design-документы, спецификации
- .claude/   — subagents, slash-commands, settings.json для Claude Code

## GLOSSARY (ubiquitous language, DDD)
- Event — конкретный экземпляр встречи (одна дата).
- EventSeries — родитель recurring; RRULE по RFC 5545.
- RecurrenceOverride — изменение конкретного instance из series.
- EventParticipant — RSVP залогиненного User.
- GuestRSVP — RSVP без аккаунта (по email/Telegram-handle).
- ConsentRecord — отдельный документ согласия по 152-ФЗ ст. 9 ред. 156-ФЗ.

## NON-NEGOTIABLE
- 152-ФЗ ст. 18: первичная обработка ПДн граждан РФ — ТОЛЬКО на серверах РФ.
- 152-ФЗ ст. 9 ред. 156-ФЗ от 24.06.2025: согласие — ОТДЕЛЬНЫЙ документ.
- No Stripe. No Vercel managed. No Clerk billing. No Convex Pro.
- iOS — only PWA + Telegram Mini App through Phase 5.

## CLAUDE.md HIERARCHY (3 уровня)
- Root (этот файл) — стек, конвенции, глоссарий, non-negotiable.
- backend/CLAUDE.md — Django-специфика, RLS-паттерны, services.py структура.
- frontend/CLAUDE.md — Next.js App Router, next-intl, server vs client components.
- Каждый <= 200 строк. Создаются при появлении содержимого в Phase 1.
