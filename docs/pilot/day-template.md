# Pilot Этап 0 — Day N

> Шаблон ежедневного трекинга на pilot-фазе.
> Период: 5-7 рабочих дней после Phase 0 (compliance + scaffolding) перед stack commit (**ADR-007**, не ADR-005 — см. `docs/CHANGELOG.md` renumber note).
> Источник KPI: PDF `Leto_project_p3.pdf` секции 17.4-17.5.
> Goal: **Accept-Rate ≥ 60%** на core-flow [F: Pilot KPI V1.3 секция 17.1].

## Day N — YYYY-MM-DD

### Контекст дня

- **Задача дня (одна строка):** [...]
- **BC в фокусе:** identity_auth | events | rsvp | core
- **Тип работы:** new feature | refactor | debug | infra

### Метрики (заполняются в конце дня)

| Метрика | Целевое | Факт сегодня | Кумулятивно за пилот |
|---|---|---|---|
| `accepted_tasks / total_tasks` (Accept-Rate) | ≥ 0.60 | __ / __ | __ / __ |
| `rework_lines / generated_lines` | ≤ 0.20 | __ / __ | __ / __ |
| `time_per_feature_min` (медиана) | ≤ 120 мин | __ | __ |
| `import_linter_violations` | 0 | __ | __ |
| `n_plus_one_detected` (django-silk) | ≤ 2 | __ | __ |
| `rls_violations` | 0 | __ | __ |
| `i18n_missing_keys` | 0 | __ | __ |

### Claude errors log

> Категории: `hallucinated_import` | `n_plus_one` | `rls_violation` | `i18n_missing` | `module_boundary` | `other`

| # | Категория | Описание (1 строка) | Caught by (lint/test/manual) |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

### 10 Risk checks status (PDF V1.3 секция 21)

> Pass / Fix / Pivot. См. полные criteria в `docs/risk-register.md`.

| # | Риск | Статус сегодня | Кумулятивная оценка |
|---|---|---|---|
| 1 | Скорость Claude Code (≥ 3 фичи/день) | | |
| 2 | Качество ORM (N+1 ≤ 2) | | |
| 3 | RLS-correctness (0 violations) | | |
| 4 | i18n-correctness (0 missing keys) | | |
| 5 | Module boundary (≤ 10 violations за пилот) | | |
| 6 | OG-generation (Satori standalone) | | |
| 7 | Coolify deploy reliability | | |
| 8 | Yandex Cloud-специфика | | |
| 9 | Telegram OIDC adapter (готовый пакет) | | |
| 10 | Procrastinate vs Celery достаточность | | |

### Что мешало сегодня (3 пункта макс)

1. 
2. 
3. 

### Что улучшить в CLAUDE.md / skills / agents (≤ 3 пункта)

1. 
2. 
3. 

### Что осталось на Day N+1

- [ ] ...
