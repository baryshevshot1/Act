# apps/core/ — Shared utilities (создаётся в Phase 1)

> Cross-cutting infrastructure для всех 16 bounded contexts.

## Планируемые подпакеты (Phase 1)

- `apps.core.rls` — RLS middleware (transaction.atomic + SET LOCAL app.current_user_id),
  единственное место где разрешён `.raw()` / `connection.cursor()`
  (см. `.importlinter` CONTRACT 0).
- `apps.core.outbox` — Transactional Outbox publisher + Procrastinate periodic poll
  (ADR-016, см. `.claude/skills/outbox-event/SKILL.md`).
- `apps.core.logging` — `redact_pii` helper для безопасного логирования
  (см. apps/identity_auth/CLAUDE.md pitfalls).
- `apps.core.http` — outgoing HTTP с allowlist (OWASP A01 SSRF protection).

## Источники

- ADR-006 — RLS Operational Constraints (ARCHITECTURE.md).
- ADR-016 — Cross-context events via Transactional Outbox (ARCHITECTURE.md).
- CLAUDE.md NON-NEGOTIABLE #11.
