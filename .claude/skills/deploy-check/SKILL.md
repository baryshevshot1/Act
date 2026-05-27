---
name: deploy-check
description: Runs the pre-deploy checklist for Act — import-linter, migrations via direct PG, RLS isolation tests, OWASP basics, compliance gates (РКН / consent / cookie UI), and Coolify hooks. Use when user says "deploy check", "pre-deploy", "ready to deploy", "release checklist", "production gate", "before deploy", or before any merge to main / push to production. Production deploy BLOCKED until РКН ст. 22 + ст. 12 регистрации получены (NN #10).
allowed-tools: [Read, Bash, Edit]
---

# Pre-Deploy Checklist (production-readiness gate)

> Список обязательных проверок ДО любого production-deploy. **НЕ executable script** — это checklist; каждый пункт founder/developer verifies manually либо CI auto-проверяет.
> Источники: `docs/ARCHITECTURE.md` § Phase 1 Bootstrap + Pilot Risk checks + DB Migration Strategy; `CLAUDE.md` 11 NON-NEGOTIABLE; `README.md` § Compliance baseline.

## When to use

- Pилот Этап 0 daily checks.
- Перед merge feature branch → main.
- Перед `coolify deploy` на production.
- Перед public soft launch (50-100 тренеров).
- Audit при срабатывании Critical CI alert.

## When NOT to use

- Локальный dev deploy (`docker compose up`) — пропускаем compliance gates, оставляем technical.
- Staging deploy (без real PII / production users) — только technical + RLS checks, без РКН blockers.
- Hotfix < 10 lines (typo fix) — упрощённая версия (только import-linter + tests).

## Pre-Phase 0 / Compliance Gates (БЛОКЕРЫ для production)

> **NN #10** [F: `CLAUDE.md`]: РКН-уведомления ст. 22 + ст. 12. Штраф 100-300k ₽ для ИП по ч. 10 ст. 13.11 КоАП (с 30.05.2025). 50%-скидка не действует.

| # | Gate | Acceptance criteria | Источник |
|---|---|---|---|
| C1 | РКН ст. 22 регистрация получена | Выписка из реестра операторов в `docs/compliance/rkn-st22-cert.pdf` | ADR-012 |
| C2 | РКН ст. 12 (ТППД Telegram) подано | Подтверждение из РКН + опубликовано на `/privacy` | ADR-013 |
| C3 | Privacy Policy опубликована на `/privacy` | HTTP 200; содержит ТППД-получателей, страны хранения, категории ПДн (ст. 18.1) | ADR-012 |
| C4 | Consent document отдельно от оферты | На signup отдельный чекбокс; запись в `identity_auth_consent` с purpose='core_processing' | NN #2 (152-ФЗ ст. 9 в ред. 156-ФЗ) |
| C5 | Cookie consent UI (3 уровня) | Banner на первый визит; записи в `identity_auth_consent` с purposes `cookies_*` | Wave 3 |

**Если любой C1-C5 fail → не deploying to production. Coolify deploy script abort с явным error.**

## Technical Gates (для всех deploys)

### T1. Import-linter (architectural boundaries)

```bash
cd backend && lint-imports
```

**Expected:** Exit code 0; «Contracts: 18 kept, 0 broken».

**Если broken:**
- Контракт 1-17 (BC isolation): найти cross-context импорт `apps.A.models` или `apps.A.services` из `apps.B/`; переписать через `apps.A.contracts`.
- Контракт 0 (no-raw-sql): найти `.raw()` / `connection.cursor()` вне `apps.core.rls.*`; переместить в `apps.core.rls.*` или переписать через ORM.
- Контракт 18 (outbox): найти Django signal на cross-context concern; переписать через outbox event (skill `outbox-event`).

### T2. Tests pass

```bash
cd backend && pytest -x --cov=apps --cov-fail-under=70
```

**Expected:** All pass; coverage ≥ 70%; markers `rls`, `outbox`, `compliance` все выполнены.

### T3. RLS migration via direct PG (NN #11)

```bash
PG_BOUNCER_HOST="" python backend/manage.py migrate --check
# или check:
psql $DATABASE_URL_DIRECT -c "SELECT count(*) FROM pg_policies WHERE policyname LIKE '%default_deny';"
# Expected: count = N (where N = number of RLS tables)
```

**Если fail:** migration не применена через прямой PG (PgBouncer transaction-pooling блокирует CREATE EXTENSION / advisory locks).

### T4. RLS isolation tests

```bash
cd backend && pytest -m rls
```

**Expected:** Two-tenant fixture проходит — tenant A не видит данные tenant B.

### T5. FORCE ROW LEVEL SECURITY на всех RLS-таблицах

```bash
psql $DATABASE_URL_DIRECT <<EOF
SELECT tablename, rowsecurity, forcerowsecurity 
FROM pg_tables 
WHERE schemaname='public' AND tablename IN (
  'identity_auth_user', 'identity_auth_session', 'identity_auth_passkey',
  'identity_auth_consent', 'rsvp_event_participant', 'rsvp_guest_rsvp',
  'contacts_sharing_channel', 'contacts_sharing_share',
  'verification_document', 'notifications_delivery',
  'ratings_rating', 'recommendations_score_cache', 'audit_log_pii_access'
);
EOF
```

**Expected:** Все имеют `rowsecurity=true` AND `forcerowsecurity=true`.

### T6. N+1 detection (django-silk + manual review)

```bash
pytest -m slow --benchmark-only --benchmark-warmup=on
# Если new endpoint — manual review через django-silk profiles
```

**Expected:** ≤ 2 N+1 violations на feature (Pilot Этап 0 T2 Pass criteria). > 5 = Pivot signal.

### T7. ICU MessageFormat валиден (i18n correctness)

```bash
cd frontend && pnpm typecheck && pnpm lint
# next-intl validates messages/*.json при build; missing keys = build error
```

**Expected:** 0 missing keys в `ru-RU.json` и `en-US.json`; all `{n, plural, ...}` для `ru-RU` имеют four forms (one/few/many/other).

### T8. Security headers (CSP, HSTS, X-Frame-Options)

```bash
curl -sI https://staging.act.app/ | grep -i 'content-security\|strict-transport\|x-frame'
```

**Expected:** Все три headers присутствуют; CSP не имеет `'unsafe-inline'` для scripts.

### T9. Secrets scan (no real secrets in repo)

```bash
# В CI через gitleaks или trufflehog
gitleaks detect --no-banner --redact
```

**Expected:** 0 findings. `.env.example` имеет только placeholders.

### T10. Coolify deploy script — pre-deploy hook check

В `infra/coolify/<env>.yaml`:

```yaml
pre_deploy: |
  set -euo pipefail
  PG_BOUNCER_HOST="" python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  cd /app/backend && lint-imports
```

**Expected:** Все три команды в pre-deploy; lint-imports запускается ДО deploy.

## OWASP Top 10:2025 quick check

| OWASP | Check |
|---|---|
| A01 Broken access control | RLS tests pass; FORCE + default_deny на всех user-attributed таблицах |
| A02 Cryptographic failures | `django-cryptography` + Yandex Lockbox active; `pgcrypto` НЕ для app encryption (ADR-014) |
| A03 Injection | Django ORM (no .raw outside core.rls); psycopg parametrized queries |
| A04 Insecure design | RLS + Outbox patterns documented в Level C; ADRs cover trade-offs |
| A05 Security misconfiguration | CSP / HSTS / X-Frame headers (T8); DEBUG=False в prod |
| A07 Auth/Identification failures | Magic link POST (NN #6); rate limit 3/15min/IP; Argon2id passwords |
| A09 Logging/monitoring | Sentry + LGTM; `audit_log_pii_access` для admin reads |

## Specific gates per deploy type

### Hotfix (< 10 lines change)

- ✅ T1 (lint-imports), T2 (tests), T7 (i18n if frontend), T9 (secrets)
- ⏭️ Skip C1-C5 if compliance unchanged; skip T3-T5 if no migration.

### Feature deploy

- ✅ All technical gates T1-T10.
- ✅ Compliance gates if scope touches PII / new ТППД / new consent purpose.

### Production deploy (any size)

- ✅ All C1-C5.
- ✅ All T1-T10.
- ✅ Manual founder review: `docs/CHANGELOG.md` § Unreleased properly updated.

## Pilot Этап 0 specific (10 risk checks)

[F: `docs/risk-register.md` Technical risks]:

| # | Check | Pass / Fix / Pivot criteria |
|---|---|---|
| T1 | Скорость Claude Code | ≥ 3 фич/день / 1-2 фич/день / < 1 |
| T2 | N+1 violations | 0-2 / 3-5 / > 5 |
| T3 | RLS violations | 0 / 1-2 / ≥ 3 |
| T4 | i18n missing keys | 0 / 1-3 / > 3 |
| T5 | Module boundary violations | ≤ 10 / 11-25 / > 25 |
| T6 | OG generation (Satori) | работает / custom server / Cloudflare API |
| T7 | Coolify deploy reliability | 100% / 1-2 fixes / > 50% fails |
| T8 | Yandex Cloud quirks | без сюрпризов / 1-2 workarounds / > 2 блокера |
| T9 | Telegram OIDC adapter | nashёлся / 100-200 lines / > 500 lines |
| T10 | Procrastinate sufficiency | 3 use cases / 1 needs Redis / Celery from day 1 |

**Decision gate:** Pivot хотя бы по одному → pilot failed, переоткрытие стека (ADR-007).

## Pitfalls

- **НЕ deploying to production без C1+C2** — штраф 100-300k ₽ для ИП.
- **НЕ запускать migrate через PgBouncer** — `PG_BOUNCER_HOST=""` обязателен (NN #11).
- **НЕ deploying с broken contracts** — даже один import violation = architectural debt; refactor first.
- **НЕ deploying без coverage check** — `--cov-fail-under=70` в pyproject.toml; не игнорировать.
- **НЕ skipping RLS isolation tests** — single security failure = compliance incident.
- **НЕ забывать `docs/CHANGELOG.md`** обновление — иначе release history fragmented.
- **НЕ deploying на пятницу вечером** — incident response capacity ограничена; deploy в ранние рабочие часы.

## Coolify automation (auto-fail если broken)

В `infra/coolify/production.yaml`:

```yaml
pre_deploy: |
  set -euo pipefail
  # T1 architectural
  cd /app/backend && lint-imports || exit 1
  # T2 tests (если CI ещё не пробежался — что не должно случиться, но защита)
  pytest -x || exit 1
  # T3 migrate via direct PG (NN #11)
  PG_BOUNCER_HOST="" python manage.py migrate --noinput || exit 1
  # T7 frontend i18n
  cd /app/frontend && pnpm typecheck || exit 1
```

## После прохождения checklist

1. Tag release: `git tag v1.X.Y && git push --tags`.
2. Update `docs/CHANGELOG.md` § Unreleased → версия с датой.
3. Deploy через Coolify UI или GHA workflow `deploy-prod.yml`.
4. Post-deploy smoke: hit `/` (HTTP 200), `/healthz`, `/api/version`.
5. Monitor Sentry + Grafana dashboards 30 минут — нет spike errors.
6. Если что-то сломалось — rollback через Coolify (предыдущий image хранится).
