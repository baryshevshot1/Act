# Runbook — Deploy to Production (Coolify on Yandex Cloud)

> Standard production deploy workflow для Act. Активируется после Pilot Этап 0 + ADR-007 Go decision + Compliance baseline (РКН ст. 22 + ст. 12 регистрации получены).
> **БЛОКЕР:** без compliance gates C1-C5 (см. skill `deploy-check`) — НЕ deploying to production (штраф 100-300k ₽ для ИП по ч. 10 ст. 13.11 КоАП).

## Trigger conditions

| Trigger | When |
|---|---|
| Merge в `main` | Standard feature deploy |
| Manual button «Deploy» в Coolify UI | Hotfix / out-of-cycle |
| Sentry P0 fix verified | Emergency hotfix |
| Pilot Этап 0 day-by-day deploys | Daily during pilot (skip C1-C5 если pilot domain = staging) |

## Pre-deploy gates (используй skill `deploy-check`)

### Compliance (production-only БЛОКЕРЫ)

- [ ] **C1** РКН ст. 22 регистрация получена → `docs/compliance/rkn-st22-cert.pdf`.
- [ ] **C2** РКН ст. 12 (ТППД Telegram) подано + опубликовано в `/privacy`.
- [ ] **C3** `/privacy` HTTP 200 + содержит ТППД-получателей, страны хранения, категории ПДн.
- [ ] **C4** Consent document отдельно от оферты + чекбокс на signup → `identity_auth_consent`.
- [ ] **C5** Cookie consent UI (3 уровня: Essential / Analytics / Marketing).

### Technical (для всех deploys)

- [ ] **T1** `lint-imports` — 18 contracts kept.
- [ ] **T2** `pytest -x --cov-fail-under=70` — all pass.
- [ ] **T3** `PG_BOUNCER_HOST="" python manage.py migrate --check` (NN #11).
- [ ] **T4** `pytest -m rls` — two-tenant isolation работает.
- [ ] **T5** `FORCE ROW LEVEL SECURITY` на всех 13 RLS-таблицах (verify через `pg_tables`).
- [ ] **T7** `pnpm typecheck && pnpm lint` — i18n keys all present, Russian plurals four forms.
- [ ] **T8** Security headers (CSP + HSTS + X-Frame-Options) через `curl -sI`.
- [ ] **T9** `gitleaks detect` — 0 secrets in repo.
- [ ] **T10** Coolify pre-deploy hook содержит `PG_BOUNCER_HOST=""` (NN #11).

## Deploy steps

### Step 1. Stage to staging first

```bash
# В Coolify UI: deploy branch `claude/elegant-clarke-qe2HH` → environment `staging`
# ИЛИ через GHA workflow:
gh workflow run deploy-staging.yml --ref claude/elegant-clarke-qe2HH
```

Coolify runs pre-deploy hook:
```bash
set -euo pipefail
cd /app/backend && lint-imports || exit 1
PG_BOUNCER_HOST="" python manage.py migrate --noinput || exit 1
python manage.py collectstatic --noinput || exit 1
cd /app/frontend && pnpm build || exit 1
```

### Step 2. Smoke tests on staging

```bash
STAGING=https://staging.act.app

# Liveness
curl -fsS $STAGING/healthz || exit 1

# Version
curl -fsS $STAGING/api/v1/version | jq

# Public events
curl -fsS $STAGING/api/v1/events | jq '. | length'

# Security headers
curl -sI $STAGING/ | grep -iE 'content-security|strict-transport|x-frame' || exit 1

# i18n landing page renders
curl -fsS $STAGING/ru/ | grep -q '<html' || exit 1
curl -fsS $STAGING/en/ | grep -q '<html' || exit 1
```

### Step 3. Monitor staging для 15 минут

- Sentry — нет new errors (рост error rate < 5%).
- Grafana dashboards — p95 latency < 500ms; нет spike на endpoint.
- Procrastinate worker — `python manage.py procrastinate status` показывает healthy state.
- Outbox lag — `SELECT count(*) FROM outbox_event WHERE published_at IS NULL` < 100.

Если staging green → переходим к production. Если red → rollback staging (см. `rollback.md`) + диагностика.

### Step 4. Production deploy

```bash
# Coolify UI: select prod environment → click «Deploy» (manual confirmation)
# ИЛИ:
gh workflow run deploy-prod.yml --ref claude/elegant-clarke-qe2HH
```

Coolify runs same pre-deploy hook + дополнительно:
- Yandex Cloud Budget Alerts triggers verify (нет threshold breach до deploy).
- DB backup snapshot (Yandex managed PG auto-backup latest 15 min) — verify present.

### Step 5. Post-deploy verification (10 minutes)

```bash
PROD=https://act.app

# Smoke (same as staging):
curl -fsS $PROD/healthz
curl -fsS $PROD/api/v1/version
curl -sI $PROD/ | grep -iE 'content-security|strict-transport'

# RLS sanity (нет cross-tenant leak):
# В Django shell или management command:
# python manage.py check_rls_isolation
```

Monitor production:
- Sentry — error rate baseline (не должен подняться > +20%).
- LGTM Grafana — request latency p95, p99.
- Procrastinate — outbox lag растёт ≤ 100.
- Yandex Cloud cost — Budget Alert 1k ₽ MTD не triggered внезапно.

Если что-то off → rollback (см. `rollback.md`).

## Special cases

### Migration deploy (zero-downtime expand-contract)

См. skill `create-migration`. Стандартный workflow:

1. **Migration A (Expand)**: deploy — добавляет nullable column / new index.
2. **Backfill task**: Procrastinate periodic-task заполняет (1k rows / min, monitor 24h).
3. **Code deploy**: переключается на новую колонку.
4. **Migration B (Contract)**: deploy — drops old column (через 1-2 cycles).

**Запрещено в одном deploy:** RENAME COLUMN, ADD COLUMN NOT NULL без default, DROP NOT NULL без default, ALTER COLUMN TYPE большой таблицы.

### Hotfix (< 10 lines)

- ✅ T1 (lint-imports), T2 (tests), T7 (i18n if frontend), T9 (secrets).
- ⏭️ Skip C1-C5 если compliance unchanged; skip T3-T5 если no migration.
- Deploy direct to production (skip staging) ТОЛЬКО при P0 (data loss / security incident).

### Feature deploy

- ✅ All T1-T10.
- ✅ Compliance gates если scope touches PII / new ТППД / new consent purpose.
- ✅ Stage to staging first; minimum 15 min smoke.

### Phase 1 / Pilot Этап 0 deploys

- Pilot работает на staging domain (`staging.act.app`) → C1-C5 skip OK (нет production users / нет PII real).
- Daily tracking в `docs/pilot/day-N.md` (template уже в репо).

## Pitfalls (читай перед каждым deploy)

- **НЕ deploying пятницу вечером** — incident response capacity ограничена; deploy в ранние рабочие часы.
- **НЕ skipping staging** кроме P0 hotfix.
- **НЕ deploying с broken contracts** даже один import violation = architectural debt.
- **НЕ ignoring compliance gates** — штраф = экзистенциальный риск для ИП.
- **НЕ deploying если outbox lag > 100** — может сигнализировать subscriber poison message.
- **НЕ deploying без BACKUP-snapshot** — Yandex auto-backup latest 15 min; verify present до deploy.
- **НЕ запускать migrate через PgBouncer** — `PG_BOUNCER_HOST=""` обязателен (NN #11). Coolify pre-deploy hook это enforce-ит, но verify локально.

## After successful deploy

1. **Tag release**: `git tag v0.X.Y && git push --tags`.
2. **Update `docs/CHANGELOG.md`** § Unreleased → версия с датой.
3. **Notify** (если есть users): release notes в Telegram canal / email digest.
4. **Monitor** 30 минут — Sentry + Grafana + Yandex Cost.
5. **Document incidents** если что-то off → `docs/incidents/incident-YYYY-MM-DD.md` post-mortem.

## Cross-refs

- Pre-deploy checklist полный → skill `.claude/skills/deploy-check/SKILL.md`.
- Rollback procedure → `docs/runbooks/rollback.md`.
- DB restore (если migration сломала) → `docs/runbooks/db-restore.md`.
- Compliance gates basis → ADR-012 + 152-ФЗ ст. 22 + ст. 12.
- Cost monitoring → `docs/ARCHITECTURE.md` § Cost Monitoring + skill `deploy-check` T7.
