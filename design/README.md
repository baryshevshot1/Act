# design/ — Binary design assets

> Бинарные файлы дизайна (Figma exports, моки, скриншоты). Текстовые принципы — в `docs/design/`.

## Структура

```
design/
├── wireframes/     # Low-fidelity wireframes per JTBD
│   └── jtbd-2-trainer/   # wedge primary — создаётся первым
├── journeys/       # User journey maps (Markdown + опционально PNG)
└── tokens.json     # Machine-readable design tokens (Phase 1+)
```

## Конвенции

- **Figma** — single source of truth для interactive prototypes. Экспорт PNG / SVG для коммитов.
- **Имена файлов**: `jtbd-<номер>-<краткое-описание>-<state>.png` (e.g., `jtbd-2-trainer-event-create-mobile.png`).
- **Wireframes** — Markdown-первые: `journey.md` + опциональные PNG-моки рядом.
- **Tokens** — JSON для design-as-code (Style Dictionary совместимо).

## Phase 0 — empty placeholders

На этапе scaffolding — только структура папок. Финализация после Pilot Этап 0.

См. `docs/design/principles.md` для context.
