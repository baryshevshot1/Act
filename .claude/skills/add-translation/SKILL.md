---
name: add-translation
description: Adds new UI strings (next-intl messages/*.json), reference data localizations (JSONB), or user-content translations (events_event_translation) to Act. Use when user says "add translation", "add i18n", "translate string", "new locale", "Russian plurals", "ICU MessageFormat", or when adding a new UI label / category / event title in another language. Russian REQUIRES four plural forms (one/few/many/other).
allowed-tools: [Read, Write, Edit]
---

# Add Translation (UI strings · reference data · user content)

> **Localization context** (Level C готов) [F: `docs/ARCHITECTURE.md` § Localization / i18n]. Три разных подхода под три use case: UI-строки в JSON-файлах next-intl, справочники в JSONB с expression indexes, пользовательский контент в `events_event_translation`. **Никогда не смешивать.**

## Стратегия по типу контента (verbatim из Level C)

| Тип контента | Подход | Файл / таблица |
|---|---|---|
| UI-строки фронта (buttons, labels, errors) | `messages/{locale}.json` в репо | `frontend/messages/ru-RU.json`, `en-US.json` |
| Справочники (country, city, category, tag) | JSONB `localized_names` + expression index per-locale | `localization_country`, `localization_city`, и т.п. |
| Пользовательский контент (event title, description) | Выделенная translation-таблица | `events_event_translation` |

## When to use

- Добавить новую UI-кнопку / label / error message → `messages/{locale}.json`.
- Добавить новую страну / город / категорию → JSONB row + expression index если нужен.
- Перевод существующего event на другой locale → `events_event_translation` insert.
- Добавить новый locale (`de-DE`, `kk-KZ`) → создать `messages/de-DE.json` + row в `localization_locale`.

## When NOT to use

- НЕ для бизнес-данных (цены, daty) — это format, не translation; используй `Intl.NumberFormat` / `Intl.DateTimeFormat` на фронте.
- НЕ для системных error codes — они в коде, English (для логов и Sentry); user-facing message — отдельная UI-строка.
- НЕ хранить локализованные URL-slugs — Act использует locale prefix (`/ru/`, `/en/`), не localized paths.

## Pattern 1. UI-строка (messages/*.json)

### Простая строка

```json
// frontend/messages/ru-RU.json
{
  "events": {
    "rsvp_button": "Записаться",
    "rsvp_confirmed": "Заявка подтверждена",
    "rsvp_waitlist": "Вы в листе ожидания"
  }
}

// frontend/messages/en-US.json
{
  "events": {
    "rsvp_button": "RSVP",
    "rsvp_confirmed": "RSVP confirmed",
    "rsvp_waitlist": "You are on the waitlist"
  }
}
```

### Использование в Server Component

```tsx
import {getTranslations} from 'next-intl/server';

export default async function EventPage() {
  const t = await getTranslations('events');
  return <button>{t('rsvp_button')}</button>;
}
```

### **Russian plural rules** — ОБЯЗАТЕЛЬНО four forms

```json
// frontend/messages/ru-RU.json — корректно
{
  "events_count": "{count, plural, one {# событие} few {# события} many {# событий} other {# событий}}"
}

// АНТИ-ПАТТЕРН (часто делает AI без знания русского):
{
  "events_count": "{count, plural, one {# событие} other {# событий}}"  // ❌ ломает 2,3,4
}
```

| Plural form | Когда | Пример |
|---|---|---|
| `one` | 1, 21, 31, … (mod 10 == 1, кроме mod 100 == 11) | 1 событие |
| `few` | 2-4, 22-24, … (mod 10 ∈ {2,3,4}, кроме mod 100 ∈ {12,13,14}) | 2 события |
| `many` | 0, 5-20, 25-30, … | 5 событий |
| `other` | fallback для дробных и unknown | 1.5 события |

CI-проверка: `intl-messageformat-parser` валидирует наличие all four cases для `ru-RU` при `{n, plural, ...}`.

## Pattern 2. Справочник (JSONB + expression index)

### Insert row

```sql
INSERT INTO localization_country (iso_code, localized_names, default_locale_code, sort_order)
VALUES ('KZ', '{"ru-RU": "Казахстан", "en-US": "Kazakhstan"}', 'ru-RU', 50);
```

### Expression index per-locale (для lookup-by-current-locale)

```sql
-- Создаётся ОДИН раз через миграцию (apps.core.rls — нет, это apps.localization)
CREATE INDEX localization_country_name_ru_idx
    ON localization_country ((localized_names->>'ru-RU'));
CREATE INDEX localization_country_name_en_idx
    ON localization_country ((localized_names->>'en-US'));
```

### Lookup в Django ORM

```python
# apps/localization/services.py
from django.db.models import F

def find_country_by_name(*, name: str, locale: str) -> Country | None:
    # PostgreSQL JSONB ->>  efficient через expression index
    return Country.objects.filter(localized_names__contains={locale: name}).first()
```

### Когда GIN вместо expression index?

Только если нужен **cross-locale search** («найти "Москва" в любой локали»). На MVP — не нужен. См. Level C verbatim.

## Pattern 3. User content (events_event_translation)

> Per-field updates, audit, FTS per-locale dictionary, content-moderation per language.

```sql
CREATE TABLE events_event_translation (
    event_id        UUID NOT NULL REFERENCES events_event(id) ON DELETE CASCADE,
    locale_code     VARCHAR(8) NOT NULL REFERENCES localization_locale(code),
    title           TEXT NOT NULL,
    description     TEXT,
    translated_by   UUID NULL REFERENCES identity_auth_user(id),
    translated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_machine      BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (event_id, locale_code)
);

-- FTS per-locale (Russian dictionary handles morphology)
CREATE INDEX events_event_translation_fts_ru
    ON events_event_translation USING GIN (
        to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(description, ''))
    ) WHERE locale_code = 'ru-RU';

CREATE INDEX events_event_translation_fts_en
    ON events_event_translation USING GIN (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
    ) WHERE locale_code = 'en-US';
```

```python
# apps/events/services.py
def add_event_translation(*, event_id: UUID, locale_code: str,
                          title: str, description: str | None,
                          translator_user_id: UUID, is_machine: bool = False) -> None:
    with transaction.atomic():
        EventTranslation.objects.update_or_create(
            event_id=event_id, locale_code=locale_code,
            defaults={
                'title': title, 'description': description,
                'translated_by_id': translator_user_id, 'is_machine': is_machine,
            },
        )
```

## Pitfalls

- **НЕ забывать four Russian plurals** — `one/other` ломает грамматику для 2,3,4.
- **НЕ копировать английский паттерн** для славянских языков — Polish, Czech тоже имеют 3-4 формы.
- **НЕ хранить UI-строки в БД** — каждое чтение = ORM call; UI-строки должны быть compile-time bundled в JSON.
- **НЕ хранить domain-данные в `messages/*.json`** — категории, города должны быть в БД (можно администрировать без deploy).
- **НЕ забывать `setRequestLocale(locale)`** в `app/[locale]/layout.tsx` — иначе fall-back на dynamic rendering, SSG ломается.
- **НЕ импортировать `next-intl` в Python** или backend logic в TS messages — strict separation per Level C.
- **НЕ забывать expression index** для справочников — без него lookup-by-locale делает full scan.
- **НЕ использовать GIN на маленьких JSONB** (< 500 rows) — overkill, expression index быстрее.
- **НЕ ставить fallback_locale на самого себя** — `ru-RU.fallback_locale_code = 'en-US'`; `en-US.fallback_locale_code = NULL` (terminal).

## Cross-context эффекты

- Все BC обращаются к translations ТОЛЬКО через `apps.localization.contracts.get_*` (server-only) ИЛИ next-intl hooks (client). Никогда напрямую через ORM.
- Когда добавляется новая category/tag/city → `apps.localization` эмитит `LocalizationCatalogUpdated` через Outbox; кеш на фронте инвалидируется через ISR revalidation.

## После реализации

1. Build: `pnpm typecheck && pnpm lint` — проверить что все ключи присутствуют во ВСЕХ locale-файлах.
2. Тест Russian plurals: запросить string c `{count: 2}` → должен быть `2 события` (few), не `2 событий` (other).
3. Если новый locale: создать `messages/<locale>.json` копией `en-US.json` и переводить inkrementally; добавить row в `localization_locale`.
4. Если новая категория/город: migration с INSERT + expression index если нужен.
5. `lint-imports` — не сломали ли cross-context isolation.
6. Записать в `docs/CHANGELOG.md` § Unreleased → Added.
