# docs/iterations/ — Iteration memory

> Архив iteration outputs (audit reports, decision matrices, reconciliation reports). Это **Anthropic Boltzmann pattern** — portable long-term memory для AI-сессий.
> Отличие от `prompts/`: здесь — **результаты** итераций (reports), там — **инструкции** (промты).

## Содержимое

| Файл | Что это | Когда читать |
|---|---|---|
| `iteration-4.5-audit-report.md` | Полный red-team audit 13 артефактов с 6-dimensional rubric + 5 applied fixes | Перед запуском любой новой scaffolding-итерации; для понимания quality bar |

## Будущие добавления

- `iteration-3-reconciliation-report.md` — после восстановления из conversation history.
- `iteration-5-corrections-applied.md` — после Iteration 5 worklog.
- `iteration-N-*.md` — для каждой следующей итерации.

## Дисциплина

- Каждая итерация заканчивается **report-файлом** в этой папке.
- Report — **read-only после commit** (исторический документ).
- Эпистемика: `[F:]` / `[В]` / `[Г]` / `[?]` сохраняется.
