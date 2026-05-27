---
name: write-adr
description: Writes a new Architecture Decision Record (ADR) using MADR 4.0 format adapted for Act conventions (Context · Decision · Alternatives · Consequences · Triggers пересмотра). Use when user says "write ADR", "new ADR", "architecture decision", "ADR-NNN", or when making a significant architecture / stack / vendor / compliance choice. NEVER renumber existing ADRs (1-16 are frozen — see ADR-005↔007 renumbering note for consequences).
allowed-tools: [Read, Write, Edit]
---

# Write ADR (Architecture Decision Record, MADR 4.0)

> **ADR-001..016** уже зафиксированы [F: `docs/ARCHITECTURE.md` § ADR + `docs/CHANGELOG.md` Wave 1 renumber note]. Новый ADR получает следующий свободный номер (`ADR-017` etc.). **Renumbering запрещён** — ADR-005↔007 renumbering уже стоил project-wide reference correction (см. CHANGELOG).

## When to use

- Значимое архитектурное решение, которое влияет на > 1 BC ИЛИ vendor choice ИЛИ compliance posture ИЛИ stack choice.
- Отвержение варианта который рассматривался долго (e.g. ADR-005 = «отвергли managed-стек»).
- Изменение существующего решения → создать новый ADR со ссылкой на старый (status = `Superseded by ADR-N`).
- Pilot-этап решений (ADR-007 = stack commit).

## When NOT to use

- Тривиальные изменения (variable name, refactor) — это commit message, не ADR.
- Полностью внутри одного BC (e.g. «использовать pydantic вместо dataclass в `apps/events/contracts.py`») — это design choice, документировать в `apps/events/CLAUDE.md`.
- Принципы вне конкретных решений — это `docs/design/principles.md`, не ADR.
- Анти-паттерны после fact — это `docs/CHANGELOG.md` § Failed approaches.

## Где живут ADRs

| Локация | Назначение |
|---|---|
| `docs/ARCHITECTURE.md` § ADR | ADR-001..016 + новые — **canonical**, inline в ARCHITECTURE.md |
| `docs/design/decisions/ADR-NNN-*.md` | Допустимо для extended discussions (deferred сейчас); пока пусто |
| `docs/CHANGELOG.md` | Reference при добавлении/изменении ADR (Wave / Iteration) |

## Шаблон (MADR 4.0 adapted для Act)

```markdown
### ADR-NNN — Краткое название одной фразой

- **Status:** Proposed | Accepted (YYYY-MM-DD) | Superseded by ADR-XXX | Deprecated.
- **Context:** Почему решение нужно. Что мы знали к этому моменту. Какие constraints (compliance / санкции / решения предыдущих ADR / scope соло-фаундера).
- **Decision:** Конкретно что мы делаем. Один абзац.
- **Alternatives considered:** 
  - **<Alternative 1>** — отвергнуто, потому что <one-line reason>.
  - **<Alternative 2>** — отвергнуто, потому что <one-line reason>.
  - **<Alternative 3>** — рассматривается как Plan B при <trigger>.
- **Consequences:** 
  - Прямые: <list>.
  - Косвенные: <list>.
  - Что мы теряем: <list>.
- **Триггеры пересмотра:** (a) <metric / event 1>; (b) <metric / event 2>; (c) <metric / event 3>.
- **Источники:** [F: <url или path внутри проекта>]
```

## Verbatim примеры из ADR-001..016

### Пример A — короткий ADR (ADR-001)

```markdown
### ADR-001 — Modular monolith из 16 bounded contexts

- **Status:** Accepted (V1.0).
- **Context:** соло-фаундер на AI-коде; нужна архитектура, которая держит границы 
  при AI-генерации и не требует distributed debugging.
- **Decision:** modular monolith с 16 bounded contexts; cross-context calls — 
  только через `apps.<ctx>.contracts`; enforcement через `import-linter`.
- **Alternatives considered:** микросервисы (отвергнуто: операционный налог без 
  выгоды для соло); большой монолит без границ (отвергнуто: 6 месяцев AI-генерации 
  размывает domain model).
- **Consequences:** один деплой, одна БД, читаемые stack traces; необходимость 
  дисциплины с границами; модуль можно экстрагировать в сервис при необходимости.
```

### Пример B — ADR с триггерами пересмотра (ADR-003)

```markdown
### ADR-003 — Frontend: Next.js 16 App Router + next-intl

- **Status:** Accepted (V1.2).
- **Context:** OG-cards в V1.1 требуют SSR/streaming; нужен i18n routing с дня 1.
- **Decision:** Next.js 16 App Router + next-intl + TypeScript строгий на API-границах 
  через zod, либеральный внутри компонентов.
- **Alternatives considered:** Remix/RR v7 (равнозначен по SSR, меньше adoption); 
  SvelteKit (меньше Claude Code training data); Astro (динамика RSVP требует SSR); 
  SolidStart / TanStack Start (ранняя стадия).
- **Consequences:** self-host через `standalone build` на Yandex Cloud Compute 
  (Vercel не подходит под 152-ФЗ ст. 18).
- **Триггеры пересмотра:** (a) Next.js 16+ становится EOL без 5-летнего LTS path; 
  (b) Server Components patterns ломаются в major upgrade и breaking changes 
  > 2 раз/год; (c) bundle size grows > 2× на equal feature set → пересмотреть 
  на Remix/RR v7 или Astro.
```

## Шаги создания

### 1. Определить следующий свободный номер

```bash
grep -n "^### ADR-" docs/ARCHITECTURE.md | tail -5
# Последний номер + 1 = ваш ADR-NNN
```

### 2. Добавить ADR inline в `docs/ARCHITECTURE.md`

Открыть `docs/ARCHITECTURE.md`, найти секцию `## ADR (Architecture Decision Records)`, добавить новый ADR в конец секции (или в логическое место по теме — Compliance / Stack / Operational).

### 3. Записать в `docs/CHANGELOG.md`

```markdown
## [Unreleased]

### Added

- **ADR-NNN** — Краткое название (см. `ARCHITECTURE.md` § ADR-NNN).
```

### 4. Обновить cross-references

Если ADR влияет на:

- `CLAUDE.md` NON-NEGOTIABLE → добавить «(основание: ADR-NNN)» в нужный пункт.
- `README.md` Compliance baseline → обновить если применимо.
- `docs/risk-register.md` Mitigation column → ссылка на ADR-NNN.

### 5. (Опционально) Long-form в `docs/design/decisions/`

Если ADR требует > 30 строк (трудные trade-offs, multiple stakeholders) — создать файл `docs/design/decisions/ADR-NNN-short-name.md` с расширенной discussion + ссылкой в ARCHITECTURE.md inline.

## Status lifecycle

| Status | Когда | Action |
|---|---|---|
| **Proposed** | ADR написан, но решение ещё не финализировано (e.g. pending Pilot Этап 0) | Добавить inline в ARCHITECTURE.md |
| **Accepted (YYYY-MM-DD)** | Решение принято и применено | Зафиксировать дату принятия |
| **Superseded by ADR-XXX** | Заменено новым ADR | Сохранить старый ADR + добавить header «Superseded by ADR-XXX»; новый ADR ссылается на старый в Context |
| **Deprecated** | Применимо для legacy data, но не для новых решений | Не удалять — для исторической трассировки |

## Pitfalls

- **НЕ удалять старый ADR** при его replacement — `Superseded by ADR-XXX` + сохранение для трассировки решений во времени.
- **НЕ менять номер существующего ADR** — это случилось с ADR-005↔007 (см. `docs/CHANGELOG.md` Wave 1 renumber note); reference risk на 12+ месяцев вперёд.
- **НЕ делать ADR в коде** (comments) — Boltzmann pattern (`docs/CHANGELOG.md` § Failed approaches); ADRs хранятся в `docs/`.
- **НЕ забывать "Alternatives considered"** — самая частая ошибка; без альтернатив ADR превращается в декрет, не decision.
- **НЕ забывать "Триггеры пересмотра"** — иначе ADR живёт вечно даже когда обстоятельства поменялись. Минимум 2-3 trigger metrics.
- **НЕ копировать text из публичных источников** без `[F: source]` — source-grounded дисциплина.
- **НЕ ADR-ить тривиальное** — не каждое решение требует ADR (см. When NOT to use).
- **НЕ забывать timestamp** в Status — `Accepted (YYYY-MM-DD)` критичен для будущих re-evaluations.

## Cross-context эффекты

- Новый ADR обычно влияет на multiple BC — обновить per-context `CLAUDE.md` если нужно.
- Если ADR трогает compliance (152-ФЗ / ст. 9 / ст. 12 / ст. 22) → cross-ref в `docs/risk-register.md` Compliance category.
- Если ADR меняет vendor → cross-ref в `docs/risk-register.md` Operational category (O1 vendor lock-in).

## После записи

1. `git diff docs/ARCHITECTURE.md` — verify добавление inline.
2. `git diff docs/CHANGELOG.md` — verify Added entry.
3. Cross-references обновлены если применимо.
4. `lint-imports` — если ADR вводит новые modules или isolation rules.
5. Commit message: `docs(adr): add ADR-NNN <short title>`.
