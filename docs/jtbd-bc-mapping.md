# JTBD ↔ Bounded Contexts mapping

> Связка 8 JTBD из `docs/PRODUCT.md` со 16 Bounded Contexts из `docs/ARCHITECTURE.md`.
> Источники verbatim: `PRODUCT.md` (JTBD-1..8); `ARCHITECTURE.md` строки 52-71 (16 BC).
> Цель документа — single source of truth для product+arch decisions; закрывает gap из Iteration 3 § 2.3.
> Обновляется при добавлении/изменении JTBD или BC.

## Таблица mapping

| JTBD | Description (1 строка) | Primary BC | Supporting BC | Status в MVP wedge |
|---|---|---|---|---|
| **JTBD-1** Спонтан | «иду в кафе X в 20:00, кто со мной» — 1 час, 2-3 человек | Events + RSVP | Identity, Notifications, Discovery | NICE-TO-HAVE (не блокер wedge) |
| **JTBD-2** Тренер регулярных групп | стабильная группа 8-12 человек, серия с per-event RSVP | Events + Recurrence + Groups + RSVP | Identity, Verification L3, Notifications, Ratings, Discovery, Billing Слой 1 | **WEDGE PRIMARY** |
| **JTBD-3** Платная экспертная консультация | психолог / коуч публикует слоты с верификацией + оплата на платформе | Events + Contacts Sharing | Identity, Verification L4 ID, Billing Слой 1+2 (Pro), Ratings, Discovery | DEFERRED (после wedge validation) |
| **JTBD-4** Хобби-группа | открытая группа настолок с расписанием + «уровень: новички» | Groups (ADR-009 `members_moderated` / `members_open`) + Events | Identity, Discovery, Moderation, Recommendations | NICE-TO-HAVE (V2 wedge) |
| **JTBD-5** Поездка в новом городе | 4 дня в Тбилиси / Берлин, найти за 60 сек что сегодня вечером | Discovery + Recommendations | Events, Localization (EN), Geo (City filter) | DEFERRED (после RU PMF) |
| **JTBD-6** Сообщество в новом городе | переехал, 2-3 регулярные группы по интересам за месяц | Groups + Recommendations + Discovery | Identity, Localization | DEFERRED |
| JTBD-7 Профессиональный нетворкинг | founders / designers — отложен после PMF в JTBD-2/3 | Groups + Verification | Post-PMF | NOT IN MVP |
| JTBD-8 Культурные походы (концерты, выставки) | KudaGo mirror imports | Discovery + mirror imports | Events (read-only) | NOT IN MVP |

## Wedge focus [F: `CLAUDE.md` строка 119]

> **Wedge** — стартовое сужение: одна категория × одна география. На старте — **тренеры регулярных групп × Москва**. То есть **JTBD-2 — единственный primary** для MVP wedge.

### MVP-минимум BC для JTBD-2

Чтобы запустить wedge (JTBD-2), необходимы и достаточны следующие BC:

1. **Identity & Auth** (Level C готов; ADR-013 notification fallback + ADR-014 PII encryption).
2. **Events** (Level C готов; ADR-009 — `owner_only` достаточен для JTBD-2).
3. **Recurrence Engine** (Level C готов внутри Events; ADR-016 для `EventGeneratedFromSeries`).
4. **RSVP & Attendance** (Level C готов; merge_guest_on_signup из PDF V1.3 секция 20.4).
5. **Notifications** (Level C missing — Wave 4; но ADR-010 FSM зафиксирован; `acknowledged` как NSM ground truth).
6. **Localization** (Level C готов; для wedge достаточно RU only).
7. **Verification** (Level C missing — для JTBD-2 опциональная phone + photo, не L4).
8. **Analytics** (Level C missing — для NSM Confirmed Weekly Attendances).

### MVP-достаточно (не нужны на wedge)

- Groups (Level C missing) — нужен для JTBD-4, не для JTBD-2 (тренер может вести Series без Group, привязка опциональна).
- Discovery — на wedge каталог 30 серий за 4 недели сортируется простой recency, не требует ADR-008 сложности.
- Ratings — после первого цикла «организатор → participant → next series», не критично в первые 2 недели.
- Contacts Sharing — opt-in, не критично для wedge.
- Moderation — фаундер модерирует вручную.
- Admin Console — Django admin достаточен на wedge.
- Recommendations — placeholder в MVP [F: `CLAUDE.md` строка 38].
- User Profile — минимальный (display_name + photo) достаточен.

## Monetization mapping

> 4 слоя монетизации (см. `PRODUCT.md`) активируются на разных JTBD:

| Слой | JTBD trigger | BC | Включается |
|---|---|---|---|
| **0 (бесплатно)** | All | All | С дня 1 |
| **1 (комиссия 5-7%)** | JTBD-2, JTBD-3 (paid events) | + Billing | Месяц 4 (после wedge validation) |
| **2 (Pro subscription)** | JTBD-2 (тренеры), JTBD-3 (эксперты) | + Billing | Месяц 5-6 |
| **3 (Featured / Boost)** | All paid events | + Billing | Месяц 6-9 |
| **4 (B2B / White-label)** | Тренерские студии | + Billing | После 12 мес |

## Decision flow

При добавлении новой feature ask:

1. Какому JTBD служит? (если ни одному → не делать или фиксировать как новый JTBD).
2. Какие BC затрагивает? (если > 2 BC → разделить на 2 PR — contracts first).
3. Это wedge или deferred? (wedge → текущий sprint; deferred → backlog).
4. Какие ADR применимы? (если новое архитектурное решение → нужен ADR, не в Phase 1).
