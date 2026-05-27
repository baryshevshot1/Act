# Runbook — Rollback (Coolify image + optional DB)

> Когда + как откатить production deploy.
> Источники: ADR-004 (Coolify hosting); `docs/ARCHITECTURE.md` § DB Migration Strategy (expand-contract).

## Trigger conditions (когда rollback)

| Trigger | Severity | Action |
|---|---|---|
| Sentry error rate +50% за 5 мин после deploy | P0 | **Immediate rollback** |
| p95 latency > 2× baseline | P0 | **Immediate rollback** |
| 500 errors на main user flow (signup / event create / RSVP) | P0 | **Immediate rollback** |
| Database corruption / RLS leak detected | P0 | **Rollback + DB restore (см. db-restore.md)** |
| Compliance failure (РКН-сертификат revoked) | P0 (legal) | **Take down site** + rollback не поможет, ждать compliance fix |
| Feature flag misconfiguration | P1 | Toggle flag в PostHog, не rollback |
| UI bug (cosmetic) | P2 | Hotfix вместо rollback |
| Single endpoint slow | P2 | Investigate, fix forward |

## Coolify image rollback (типичный путь)

Coolify хранит previous Docker images. Rollback = свап на предыдущий image без re-build.

### UI path

1. Open Coolify dashboard → environment `prod` → application `act-web`.
2. Tab «Deployments» → see history (last 10 deployments).
3. Click previous deployment → «Redeploy this version».
4. Coolify pulls cached image + restarts containers (~30 sec).

### CLI path

```bash
# SSH в Coolify host:
ssh coolify@<yandex-compute-ip>

# Find previous image SHA:
docker images | grep act-web | head -3
# Например:
# act-web   abc123def456   2 hours ago
# act-web   xyz987uvw321   3 hours ago  ← rollback target

# Coolify-managed:
coolify deploy --app act-web --image-sha xyz987uvw321
```

### Verification после rollback

```bash
PROD=https://act.app
curl -fsS $PROD/api/v1/version | jq '.build_sha'
# Должен показать предыдущий commit SHA
```

Sentry — error rate должен вернуться к baseline в течение 5 минут. Если нет → проблема НЕ в deploy (внешняя зависимость, DDOS, etc.).

## DB rollback (если migration сломала)

### Сценарий 1: Migration backward-compatible (expand-contract pattern correct)

- Code rollback достаточен — старый код работает с новой схемой (новая колонка nullable, старая колонка ещё есть).
- DB **НЕ откатываем**.

### Сценарий 2: Migration NOT backward-compatible (ошибка в discipline)

- Это нарушение expand-contract — должно было быть caught в pre-deploy review.
- **DB rollback нужен.** См. `db-restore.md` для full restore из Yandex managed PG backup.
- Альтернативно: reverse migration через `python manage.py migrate <app> <previous_migration>`:
  ```bash
  PG_BOUNCER_HOST="" python manage.py migrate <ctx> <previous_migration_number>
  ```
- **Только** если migration имеет proper `reverse_sql` (skill `create-migration` enforce-ит это).

### Сценарий 3: RLS policy сломала доступ (cross-tenant leak ИЛИ забыли default_deny)

- **P0 incident.** Take down site (Coolify scale to 0) — стоп leak.
- Reverse RLS migration (drop bad policy + add correct).
- Audit `audit_log_pii_access` — кто читал что после deploy.
- Если PII leaked → 152-ФЗ ст. 21 — уведомить РКН в течение 24 часов (или 72 для GDPR-overlap).
- Post-mortem обязателен → `docs/incidents/incident-YYYY-MM-DD-rls-leak.md`.

## Communication

### Internal (founder solo — self-communication)

- Update `docs/incidents/incident-YYYY-MM-DD.md`:
  - Trigger
  - Timeline (deploy time → detection → rollback time → resolved time)
  - Root cause (5 whys)
  - Action items (preventive)

### External (когда есть users — post Soft launch)

- **Status page** (statuspage.io / instatus.com self-host) — update incident status.
- **Twitter / Telegram-канал** — короткое объявление если impact > 30% users.
- **In-app banner** — если incident длится > 30 минут.

## Rollback discipline

- **Resolve forward, не backward**, если fix < 30 минут и понятный → hotfix предпочтительнее rollback (избегаем shipping back known-bad code).
- **Rollback быстрый, не perfect** — если есть сомнения, rollback + дискуссия после.
- **Document every rollback** — `docs/incidents/` для learning loop.
- **No silent rollbacks** — каждый rollback должен иметь incident report + RCA.

## Cost / quota considerations

- Coolify rollback — free (cached image, no rebuild).
- DB restore из backup — Yandex managed PG free для standard backup retention; PITR может иметь cost при крупных операциях.
- Bandwidth + compute spike при mass-rollback — мониторить через Yandex Cloud Cost Alerts.

## After rollback

1. **Sentry** — confirm error rate вернулся к baseline.
2. **Grafana** — p95 latency normalized.
3. **Incident report** обязателен (даже если impact малый).
4. **Re-test** failed scenario локально → fix → re-deploy.
5. **Если incident был compliance-related** → review ADR-012 + risk register C2.
6. **Update `docs/CHANGELOG.md`** § Unreleased — пометить rollback (если был released SHA).

## Pitfalls

- **НЕ rollback-ить database** если можно code rollback (expand-contract pattern должен спасти).
- **НЕ забывать audit log** — после rollback compliance audit может потребовать «кто видел что и когда».
- **НЕ rollback-ить без incident report** — теряем learning loop, repeat ошибки.
- **НЕ silent rollback** — даже один-человек команда требует артефакт для будущей review.
- **НЕ blame** — incident review focuses на process / system, не на people.

## Cross-refs

- Deploy procedure → `docs/runbooks/deploy.md`.
- DB restore (включая PITR) → `docs/runbooks/db-restore.md`.
- Pre-deploy gates → skill `.claude/skills/deploy-check/SKILL.md`.
- Risk register (RLS leak, compliance fail) → `docs/risk-register.md` C2, C3.
