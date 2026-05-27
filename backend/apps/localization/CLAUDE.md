# apps/localization — Localization / i18n Context

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C Localization / i18n).
> Источники: `ARCHITECTURE.md` § Localization / i18n (Level C готов) + next-intl 4.x docs + ICU MessageFormat spec + CLDR Russian plural rules.

## Context

Localization — справочники стран / городов / категорий / тегов с локализованными именами в JSONB; список поддерживаемых UI-локалей; negotiation logic. Используется **всеми контекстами** через `apps.localization.contracts`. **UI-строки фронта** живут в `frontend/messages/{locale}.json` (next-intl + ICU MessageFormat), НЕ в БД. БД хранит только локализуемые данные доменных сущностей.

## Translation strategy by use case (verbatim из Level C)

Не вся локализация одинакова — стратегия зависит от частоты обновлений:

| Тип контента | Подход | Хранение |
|---|---|---|
| UI-строки фронта (buttons, labels, errors) | `messages/{locale}.json` в репо | `frontend/messages/` (compile-time bundled) |
| Справочники (country, city, category, tag, locale) | JSONB `localized_names` + expression index per-locale | `localization_country`, `localization_city`, etc. |
| Пользовательский контент (event title, description, group bio) | Выделенная translation-таблица | `events_event_translation` (per-event), `groups_group_translation`, etc. |

## Entities

| Entity | Description | RLS? |
|---|---|---|
| `Locale` (`localization_locale`) | Поддерживаемые UI-локали (`code`, `icu_language_tag`, `fallback_locale_code`, `is_rtl`, `is_active`) | — (справочник) |
| `Country` (`localization_country`) | `iso_code`, `localized_names JSONB` ({"ru-RU":"Россия","en-US":"Russia"}), expression indexes per-locale | — (справочник) |
| `City` (`localization_city`) | `country_id`, `localized_names`, `iana_timezone`, lat/lng, expression indexes | — (справочник) |
| `Category` / `Tag` | `localized_names JSONB` | — (справочники) |

## Conventions

- **NEVER в БД UI-строки** — `messages/{locale}.json` версионируются git, no DB roundtrip, ICU MessageFormat для plural.
- **NEVER в `messages/*.json` domain-данные** — категории / города идут в БД (администрирование без deploy).
- **`(localized_names->>'<locale>')` expression index per-locale** — быстрее GIN для lookup-by-current-locale (90%+ запросов). GIN ТОЛЬКО если нужен cross-locale search; на MVP не нужен.
- **Russian plurals — ОБЯЗАТЕЛЬНО four forms** (one / few / many / other). `one/other` ломает грамматику для 2,3,4. CI-проверка через `intl-messageformat-parser`.
- **`fallback_locale_code`** — `ru-RU.fallback = 'en-US'`; `en-US.fallback = NULL` (terminal). НЕ ставить fallback на самого себя.
- **Server-only функции** в `apps.localization.contracts` имеют префикс `get_*` (async-friendly Django ORM). Client-side — только через `next-intl` hooks. **НИКОГДА** не импортируем `next-intl` в Python service-layer и наоборот.
- **`setRequestLocale(locale)` обязателен** в `app/[locale]/layout.tsx` — иначе fall-back на dynamic rendering, SSG ломается [F: next-intl docs «Server Components» + Next.js 16 ISR guidelines].
- **Locale negotiation** — `Accept-Language` header → fallback chain → default `ru-RU`. Implementation в `apps.localization.services.negotiate_locale`.
- **TIMESTAMPTZ** для дат; форматирование per-locale через `Intl.DateTimeFormat` на фронте либо `babel.dates.format_datetime` на бэке.

## Russian plural rules — verbatim

```json
// frontend/messages/ru-RU.json — КОРРЕКТНО
{
  "events_count": "{count, plural, one {# событие} few {# события} many {# событий} other {# событий}}"
}

// АНТИ-ПАТТЕРН (часто делает AI без знания русского):
{
  "events_count": "{count, plural, one {# событие} other {# событий}}"  // ❌ ломает 2,3,4
}
```

| Form | Когда | Пример |
|---|---|---|
| `one` | 1, 21, 31, ... (mod 10 == 1, кроме mod 100 == 11) | 1 событие |
| `few` | 2-4, 22-24, ... (mod 10 ∈ {2,3,4}, кроме mod 100 ∈ {12,13,14}) | 2 события |
| `many` | 0, 5-20, 25-30, ... | 5 событий |
| `other` | fallback (дробные) | 1.5 события |

## next-intl 4.x integration patterns (verbatim из Level C)

| Контекст | API | Когда |
|---|---|---|
| Async Server Component | `await getTranslations(namespace)` | Server-rendered страницы — основной случай |
| Client Component | `useTranslations(namespace)` hook | Только при интерактивности (language switcher) |
| Static rendering | `setRequestLocale(locale)` в layout | Обязательно для SSG |
| Background jobs / outbox subscribers | `apps.localization.contracts.get_translated_string(key, locale)` | Server-only Python функция |

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `LocaleDTO`, `CountryDTO`, `CityDTO`, `CategoryDTO`, `negotiate_locale(request_headers, user_pref)`, `get_translated_string(key, locale)`, `get_city_by_id(city_id) -> CityDTO`.
- **Consumes:** ничего (Localization — leaf BC, не зависит от других).
- **Emits via Outbox:** `LocalizationCatalogUpdated` (когда добавляется/изменяется страна / город / категория) — frontend ISR revalidation.
- **Subscribes:** ничего.

## Common pitfalls

- **НЕ хранить UI-строки в БД** — каждое чтение = ORM call; UI должны быть compile-time bundled JSON.
- **НЕ хранить domain-данные (категории / города)** в `messages/*.json` — они должны быть в БД (admin без deploy).
- **НЕ копировать английский `one/other` паттерн** для русского — нужны four forms.
- **НЕ забывать `setRequestLocale(locale)`** в `app/[locale]/layout.tsx`.
- **НЕ импортировать `next-intl`** в Python service-layer.
- **НЕ забывать expression index** при добавлении нового locale в `localized_names` — без него lookup-by-locale делает full scan.
- **НЕ использовать GIN на маленьких JSONB** (< 500 rows) — overkill, expression index быстрее.
- **НЕ ставить fallback_locale на самого себя** — бесконечная рекурсия в negotiate.
- **НЕ забывать про IANA timezone в `City`** — `Europe/Moscow`, не `MSK` или `+03:00`.
- **НЕ хранить formatted numbers / dates в БД** — храни raw, форматируй per-locale на render.

## Cookie consent UI cross-ref

Cookie consent UI (Wave 3) пишет records в `identity_auth_consent` с purposes `cookies_essential / cookies_analytics / cookies_marketing`. Сами UI-строки баннера — в `messages/{locale}.json` под namespace `cookies`. PostHog `init()` должен быть **после** consent check (`useConsent` hook).

## Skills relevant to this BC

- `add-translation` — основной workflow (UI strings / справочники / user content).
- `outbox-event` — emit `LocalizationCatalogUpdated` для ISR revalidation.
- `create-migration` — schema changes для новых locales / expression indexes.

## i18n examples (cross-ref to other BCs)

- **Events title** → `events_event_translation` (per-event, audit, FTS per-locale dictionary).
- **Category name** → `localization_category.localized_names` (справочник, expression index).
- **«Записаться» button** → `frontend/messages/{locale}.json` (UI string).
- **«2 события» (plural)** → ICU MessageFormat с four Russian forms.
