# Runbook — Database Restore (Yandex Managed PostgreSQL)

> Backup + restore procedures для production PG. Required для disaster recovery + RLS-leak rollback (см. `rollback.md` Сценарий 3).
> Источники: ADR-006 (PostgreSQL single source of truth); `docs/ARCHITECTURE.md` § Disaster Recovery (Wave 3 operational sections).

## Backup strategy

### Auto-backup (Yandex Managed PostgreSQL)

| Type | Retention | Granularity |
|---|---|---|
| Daily full backup | 7 days (free tier) — 30 days (paid retention) | Once per 24h |
| WAL streaming | Continuous | Point-In-Time Recovery (PITR) до любой секунды в retention window |
| Manual snapshot | Indefinite (until deleted) | Triggered manually pre-deploy |

**Verify backup actively works:**
```bash
yc managed-postgresql backup list --cluster-name act-prod
# Должен показывать last 7+ backups, с automated=true
```

### Manual snapshot (pre-deploy safety)

```bash
yc managed-postgresql cluster backup --name act-prod
# Returns backup-id; сохранить в incident log если deploy risky
```

### Cross-region backup (Plan B per O4 sanctions risk)

Weekly cron в Procrastinate task:

```python
# apps/core/backup/tasks.py
@app.periodic_task(cron='0 3 * * 0')  # каждое воскресенье 03:00 UTC
def weekly_backup_to_selectel_s3():
    """
    Copy latest Yandex PG backup → Selectel S3 bucket.
    Plan B на случай sanctions-blockade Yandex (Risk O4).
    """
    backup_id = get_latest_yandex_backup_id('act-prod')
    download_backup(backup_id, '/tmp/backup.sql.gz')
    upload_to_selectel_s3('/tmp/backup.sql.gz', 'act-backups-selectel')
    delete_local('/tmp/backup.sql.gz')
```

## Restore scenarios

### Scenario 1: Point-In-Time Recovery (PITR)

> Use case: deploy сломал данные (bad migration, runaway script деnormalized таблицу).
> Цель: восстановить до timestamp T0 — до момента поломки.

```bash
# Determine target timestamp (за 5 минут до incident):
INCIDENT_TIME=$(date -d '2026-05-27 14:30:00' +%s)
TARGET_TIME=$(date -d "@$((INCIDENT_TIME - 300))" --iso-8601=seconds)

# Create new cluster from PITR (Yandex doesn't restore IN-PLACE — создаёт новый):
yc managed-postgresql cluster restore \
  --name act-prod-restored-$(date +%Y%m%d-%H%M) \
  --backup-id <backup-id-before-target> \
  --time $TARGET_TIME \
  --resource-preset s3.micro \
  --disk-size 20 \
  --environment PRODUCTION

# ⏳ Yandex provisions новый cluster (~10-30 минут для s3.micro).
```

После provision:

```bash
# Verify data на restored cluster:
psql "host=<restored-host> dbname=act user=postgres" -c "SELECT count(*) FROM events_event;"

# Если данные корректны → switch DNS / connection string в Coolify:
# 1. Update DATABASE_URL secret в Coolify → новый host.
# 2. Restart all app containers (Coolify deploy без code change).
# 3. Drop старый сломанный cluster через 7 дней (safety window).
```

### Scenario 2: Full restore из daily backup

> Use case: catastrophic data loss; PITR недоступен (out of WAL retention window).

```bash
# Find last good backup:
yc managed-postgresql backup list --cluster-name act-prod | tail -5

# Restore из specific backup-id:
yc managed-postgresql cluster restore \
  --name act-prod-restored-fullrestore \
  --backup-id <chosen-backup-id> \
  --resource-preset s3.micro \
  --disk-size 20

# Switch как в Scenario 1.
```

### Scenario 3: Restore из Selectel S3 (Plan B при sanctions / Yandex blockade)

> Use case: Yandex Cloud недоступен (sanctions escalation, account suspension).

```bash
# Download from Selectel:
aws s3 cp s3://act-backups-selectel/backup-YYYY-MM-DD.sql.gz . \
  --endpoint-url https://s3.ru-1.storage.selectel.com

gunzip backup-YYYY-MM-DD.sql.gz

# Create new PG instance на Selectel Managed PG (или self-host если managed недоступен):
# 1. Provision new PG (Selectel Managed Cloud Databases для PostgreSQL 16+).
# 2. Apply extensions: pgcrypto, btree_gist, pg_trgm, unaccent, pg_uuidv7
#    (см. apps/core/migrations/0001_extensions.py).
# 3. Restore dump:
psql "host=<selectel-host> dbname=act user=act_app password=<...>" < backup-YYYY-MM-DD.sql

# Update Coolify DATABASE_URL → Selectel endpoint.
# Verify RLS policies все ENABLE + FORCE — backup может не сохранить настройки если pg_dump --schema-only:
psql -c "SELECT tablename, rowsecurity, forcerowsecurity FROM pg_tables WHERE schemaname='public';"
```

### Scenario 4: Single-table restore

> Use case: один table corrupted; rest fine. Не want full DB restore.

```bash
# Restore в side-cluster (Scenario 1), потом export specific table:
pg_dump -h <restored-host> -d act -t events_event > events_event.sql

# Import в production cluster (overwriting):
psql "host=<prod-host> dbname=act user=act_admin" -c "TRUNCATE events_event CASCADE;"
psql "host=<prod-host> dbname=act user=act_admin" < events_event.sql

# CAREFUL: act_admin = BYPASSRLS — verify audit log записан.
# CASCADE удаляет EventParticipant, GuestRSVP — может быть OK если они тоже corrupt; иначе восстановить тоже.
```

## Monthly restore drill (mandatory)

Каждый 1-го месяца — verify restore работает:

```bash
# 1. Take manual snapshot
yc managed-postgresql cluster backup --name act-prod
BACKUP_ID=$(yc managed-postgresql backup list --cluster-name act-prod | head -1 | awk '{print $1}')

# 2. Restore в test cluster:
yc managed-postgresql cluster restore \
  --name act-prod-drill-$(date +%Y%m) \
  --backup-id $BACKUP_ID \
  --resource-preset s3.micro \
  --disk-size 20

# 3. Verify data integrity:
psql "<restored-host>" -c "SELECT count(*) FROM identity_auth_user;"
# Expected: same as prod count ± 5% (transaction window)

# 4. Verify RLS работает:
psql "<restored-host>" -c "SELECT count(*) FROM pg_policies WHERE policyname LIKE '%default_deny';"
# Expected: same as prod count (13 RLS tables)

# 5. Delete drill cluster:
yc managed-postgresql cluster delete --name act-prod-drill-$(date +%Y%m)

# 6. Document в `docs/runbooks/restore-drills/drill-YYYY-MM.md`:
# - Backup ID used
# - Restore time elapsed
# - Verification results
# - Any anomalies
```

**Если drill fail** → P0 incident; investigate ASAP. Backup без verified restore = no backup.

## Compliance considerations

- **152-ФЗ ст. 18** — restored cluster ОБЯЗАТЕЛЬНО в РФ region. Selectel Plan B — выбирать Москва / СПб datacenter.
- **`audit_log_pii_access`** — после restore, audit log должен быть intact (не truncated). Если truncated → compliance gap; уведомить РКН.
- **PII encryption** (ADR-014) — `channel_value`, `phone_e164`, `primary_email` остаются encrypted; Yandex Lockbox key должен быть доступен в restored environment.
- **Backups содержат PII** — Selectel S3 bucket должен иметь encryption at rest (AES-256) + access control только для service account.

## Pitfalls

- **НЕ restore-ить in-place** на production PG — Yandex Managed PG не поддерживает; всегда создаётся новый cluster.
- **НЕ забывать update DATABASE_URL** в Coolify после switch на restored cluster.
- **НЕ забывать drop старый сломанный cluster** через safety window (7 дней).
- **НЕ забывать verify RLS** на restored cluster — backups могут не сохранить policy settings правильно.
- **НЕ trust auto-backup без drill** — monthly verify обязателен.
- **НЕ скачивать backup в insecure location** — содержит PII; encrypted-only filesystem + delete после use.
- **НЕ забывать про PITR retention window** — Yandex free tier = 7 дней; если incident detected late → out of window, only daily backup доступен (granularity 24h, data loss).

## RTO / RPO targets

| Metric | Target | Source |
|---|---|---|
| RPO (Recovery Point Objective) | ≤ 5 минут | PITR WAL streaming |
| RTO (Recovery Time Objective) — code rollback | ≤ 10 минут | Coolify image swap |
| RTO — single-cluster restore | ≤ 60 минут | Yandex provisioning ~30 min + verify + switch |
| RTO — cross-cloud Selectel restore | ≤ 4 часа | Provisioning + extensions + import + verify |

## Cross-refs

- Deploy procedure → `docs/runbooks/deploy.md`.
- Rollback decision tree → `docs/runbooks/rollback.md`.
- Backup tasks impl → `apps/core/backup/tasks.py` (Phase 1+).
- Risk register vendor lock-in → `docs/risk-register.md` O1, O4.
- ADR-006 PostgreSQL → `docs/ARCHITECTURE.md` § ADR-006.
- Disaster Recovery operational section → `docs/ARCHITECTURE.md` § Wave 3.
