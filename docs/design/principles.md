# Act — Design Principles (UI / UX)

> Скелет принципов дизайна. Создан в Iteration 0 / Phase 0 как placeholder.
> Финальный дизайн — после **Pilot Этап 0 + ADR-007 stack commit** (см. CLAUDE.md строка 153: «Не предлагать UI-kit ... отложено до пилота»).
> Эпистемика: `[F:]` факт; `[В]` вывод; `[Г]` гипотеза; `[?]` неизвестное.

## 6 принципов дизайна Act

### 1. JTBD-driven, не feature-driven

Каждый wireframe / journey / экран привязан к конкретному JTBD из `docs/jtbd-bc-mapping.md`. **JTBD-2 (тренеры регулярных групп) — wedge primary** = первый набор экранов. Никаких «давайте сделаем красивый дашборд» без JTBD-привязки.

### 2. i18n-aware с дня 1

ICU MessageFormat везде (через `next-intl`). Layouts учитывают +30% длины для DE / FR / RU vs EN. Никаких хардкоженных строк в JSX. [F: `ARCHITECTURE.md` строка 39 + Level C Localization].

### 3. Mobile-first + Telegram Mini App

PWA — primary form factor (**NON-NEGOTIABLE #5** [F: `CLAUDE.md` строка 135]). Все экраны проектируются на 375×667 viewport, потом расширяются. App Store distribution — отложен до Phase 6+ (требует зарубежного юр.лица).

### 4. Frictionless onboarding (V1.1)

Guest RSVP без аккаунта, magic links, прогрессивный профиль. Никаких «complete your profile» баров [F: `PRODUCT.md` принцип Airbnb]. Magic links через POST после явного клика (**NON-NEGOTIABLE #6** [F: `CLAUDE.md` строка 136]).

### 5. Privacy-respecting components

- Cookie consent UI как 3-уровневый компонент (`cookies_essential` / `cookies_analytics` / `cookies_marketing`) [F: `ARCHITECTURE.md` Wave 3].
- Audit log indicator для admin actions.
- Никаких third-party tracking pixels (152-ФЗ ст. 18 — РФ-локальность ПДн).
- PII-fields в UI помечены явно (encrypted at rest, see ADR-014).

### 6. Accessibility WCAG 2.2 AA как baseline

Не AAA (over-spec для wedge), но AA обязательно: контрасты ≥ 4.5:1 для текста, keyboard navigation, screen reader labels, focus states. [F: WCAG 2.2 W3C Recommendation].

## Decision flow при создании нового UI

1. **Какому JTBD служит?** Если ни одному → не делать или фиксировать как новый JTBD в `docs/jtbd-bc-mapping.md`.
2. **Какие UI-BC затрагивает?** (`frontend/components/<bc>/`). Если > 1 → contracts first (типы в `frontend/components/shared/`).
3. **Wedge или deferred?** Wedge = текущий sprint; deferred = `docs/design/decisions/DDR-XXX-deferred.md`.
4. **Требуется ли новое архитектурное решение?** Если да → DDR (Design Decision Record по MADR 4.0).

## После Pilot Этап 0

Финализируется в `docs/design/decisions/`:

- **DDR-001** — Mobile-first PWA + Telegram Mini App (acceptance gate из NN #5).
- **DDR-002** — UI framework decision (Tailwind / shadcn / custom) на основе эмпирики Pilot.
- **DDR-003** — Design tokens (palette, typography, spacing) — `docs/design/tokens.md`.
- **DDR-004** — Component library bootstrap (Storybook + Vitest).
- **DDR-005** — Form patterns (validation, error states, async submission).

## Ссылки

- `docs/jtbd-bc-mapping.md` — 8 JTBD × 16 BC × wedge focus.
- `docs/ARCHITECTURE.md` Level C Localization — i18n strategy + RU plurals.
- `docs/PRODUCT.md` Frictionless Onboarding (V1.1 раздел 3).
- `docs/risk-register.md` C5 — Apple MPP / iOS privacy shifts risk.
- `CLAUDE.md` NON-NEGOTIABLE #5 (iOS), #6 (magic link POST).
