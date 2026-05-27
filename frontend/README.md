# frontend/ — Next.js 16 App Router (создаётся в Phase 1 Bootstrap)

> Скелет TypeScript-части Act. На текущем этапе (Phase 0) — только каркас директорий и i18n catalogs. Next.js-проект инициализируется в Phase 1.

## Структура

```
frontend/
├── package.json            # Phase 1: `pnpm create next-app frontend --typescript --app`
├── tsconfig.json           # Phase 1: TS config с strict mode + path aliases
├── next.config.mjs         # Phase 1: next-intl + proxy на Django backend
├── app/                    # Next.js 16 App Router
│   └── [locale]/           # i18n dynamic route (ru / en через next-intl)
├── components/             # UI bounded contexts (зеркалят backend/apps/)
│   ├── identity/           # auth forms, consent banner, magic-link UI
│   ├── events/             # event card, event detail, OG preview
│   ├── rsvp/               # RSVP form, guest flow, attendance check-in
│   └── shared/             # primitives + DTO types (зеркалят apps.X.contracts)
├── messages/               # i18n catalogs — ICU MessageFormat
│   ├── ru.json             # Russian (wedge primary)
│   └── en.json             # English (deferred till JTBD-5/6 expansion)
├── public/                 # static assets
└── styles/                 # global styles (UI-kit TBD после Pilot)
```

## Phase 1 Bootstrap commands (для будущей сессии)

```bash
cd frontend
pnpm create next-app@latest . --typescript --app --eslint --no-tailwind \
  --import-alias "@/*" --use-pnpm
pnpm add next-intl
# Затем — настроить middleware.ts для locale negotiation,
# создать messages/ru.json + en.json structure (см. ARCHITECTURE.md Level C Localization).
```

## Конвенции

- **i18n с дня 1** — все строки в `messages/{ru,en}.json`, никаких хардкодов в JSX
  [F: ARCHITECTURE.md строка 39].
- **First-write locality** — все POST-запросы идут через Django backend (RU-region),
  не напрямую на сторонние сервисы (ст. 18 ч. 5 152-ФЗ, см. ARCHITECTURE.md принцип 6).
- **Mobile-first + PWA** — primary form factor 375×667 (NON-NEGOTIABLE #5).
- **Без UI-kit** на старте — отложено до ADR-007 stack commit
  [F: CLAUDE.md строка 153].

## После Pilot Этап 0

После ADR-007 commit — добавляются:
- `frontend/lib/` — API client (типизированный через `drf-spectacular` schema).
- `frontend/middleware.ts` — next-intl locale negotiation.
- DDR-001 «Mobile-first PWA + Telegram Mini App» — в `docs/design/decisions/`.
- Storybook setup (после component-library bootstrap, ~W3-W5).
