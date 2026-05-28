# Phase 1.5-1.7 prep — Research findings (2026-05-28)

> **Источник:** outside-LLM сессия с web-search (founder обратился к параллельной нейросети с prompt'ом `prompts/research-phase-1-prep.md`).
> **Дата:** 2026-05-28.
> **Verdicts summary:** R1-R8 — все вопросы получили actionable verdicts. Блокеров нет; одна «жёлтая» зона (R6 django-cryptography-django5 stale).
> **Methodology:** 18 web searches + 1 web_fetch + 1 subagent. Источники tier'ованы ★★★/★★/★ per prompt requirement #6.

-----

## Executive summary

| # | Вопрос | Verdict | Confidence | Применение к Act |
|---|---|---|---|---|
| **R1** | `pg_uuidv7` в Yandex Managed PG 17 | **✅ available v1.5** (PG17), v1.5.0 (PG18) | HIGH | Phase 1.4.bis: extension + `DEFAULT uuid_generate_v7()` в DDL. Снимает TODO в моделях. |
| **R2** | django-allauth Telegram | **✅ native provider** (`allauth.socialaccount.providers.telegram`) | HIGH | W1 scope сокращён ~100 LOC → ~5 LOC config. Custom adapter НЕ нужен. |
| **R3** | next-intl + Next.js 16 | **⚠️ breaking:** `middleware.ts` → **`proxy.ts`** (Node.js runtime, не Edge) | HIGH | Phase 1.5 skeleton: `proxy.ts` + `NextIntlClientProvider` mandatory + `locale` в `getRequestConfig`. |
| **R4** | Procrastinate compat | **⚠️ 3.8.1 совместим, но Django 5.2 НЕ в CI** | MEDIUM-HIGH | Pin `procrastinate==3.8.1`. Worker — прямой коннект к мастеру (NOTIFY не работает в PgBouncer txn pool). |
| **R5** | PG 18 в Yandex MDB | **✅ available_now** (GA подтверждён в FAQ 2026-05-05) | HIGH | MVP на 17 → in-place upgrade 17→18 в Q3-Q4 2026; нативный `uuidv7()` снимет extension dependency. |
| **R6** | django-cryptography-django5 ≥ 2.0 | **⚠️ stale** (last release 2024-06, classifiers только Django 5.0) | MEDIUM | **Action needed:** replace до W1. Cand: `cryptography` + custom EncryptedField (~50 LOC) ИЛИ `django-encrypted-model-fields`. |
| **R7** | django-otp-webauthn + django-otp | **✅ Django 5.2 явно в classifiers** | HIGH | Bump pins: `django-otp>=1.7,<2` + `django-otp-webauthn>=0.8,<1`. |
| **R8** | import-linter forbidden subpackages | **alternative:** `include_external_packages=True` + root-level forbidden (не `root_packages`) | MEDIUM-HIGH | Phase 1.4 workaround работает, но есть cleaner path. Optional cleanup. |

**Критические блокеры:** нет.
**Yellow flags:** R3 (require rename middleware→proxy), R4 (Django 5.2 not in CI — нужен local validation), R6 (PII encryption package risk).

-----

## R1. `pg_uuidv7` в Yandex Managed PG 17 — ✅ available v1.5

### Findings

Yandex Cloud публикует matrix allowed extensions: `pg_uuidv7` 1.5 для PG 15/16/17; 1.5.0 для PG 18.

Verbatim:
> "pg_uuidv7 — Adds support for generating and managing UUIDv7 identifiers."
> — yandex.cloud/en/docs/managed-postgresql/operations/extensions/cluster-extensions (Updated 2026-05-14)

> "Managed Service for PostgreSQL clusters do not support managing PostgreSQL extensions via SQL commands."

Активация: `yc managed-postgresql database update <db> --extensions pg_uuidv7,...` ИЛИ Terraform `extension { name = "pg_uuidv7" }`. **НЕ через `CREATE EXTENSION` в SQL.**

Upstream `fboulnois/pg_uuidv7` — v1.7.0 (2025-10-13); Yandex поставляет 1.5 — функционально достаточно (RFC 9562 format identical).

### Sources

- ★★★ https://yandex.cloud/en/docs/managed-postgresql/operations/extensions/cluster-extensions (2026-05-14)
- ★★★ https://github.com/yandex-cloud/docs/blob/master/en/managed-postgresql/operations/extensions/cluster-extensions.md
- ★★ https://github.com/fboulnois/pg_uuidv7 (v1.7.0, 2025-10-13)

### Recommendation for Act

**Path (a):** `pg_uuidv7` extension + `DEFAULT uuid_generate_v7()` в DDL (имя функции в v1.5).

```sql
CREATE TABLE events_event (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    ...
);
```

Phase 1.4.bis: добавить `pg_uuidv7` в `apps/core/migrations/0001_extensions.py`. После Yandex 17→18 upgrade — `ALTER COLUMN id SET DEFAULT uuidv7()` (нативный, без extension).

**Confidence:** HIGH.

-----

## R2. Django-allauth Telegram — ✅ native provider

### Findings

`allauth.socialaccount.providers.telegram` **в django-allauth core**. Telegram реализован как non-OAuth2 callback с HMAC-SHA256 верификацией внутри `CallbackView`.

Verbatim config (official docs):
```python
SOCIALACCOUNT_PROVIDERS = {
    'telegram': {
        'APP': {
            'client_id': '<bot_id>',
            'secret': '<bot token>',   # complete bot token, ID-prefixed
        },
        'AUTH_PARAMS': {'auth_date_validity': 30},
    }
}
```

Verbatim Telegram HMAC spec (https://core.telegram.org/widgets/login):
> "You can verify the authentication and the integrity of the data received by comparing the received hash parameter with the hexadecimal representation of the HMAC-SHA-256 signature of the data-check-string with the SHA256 hash of the bot's token used as a secret key."
>
> "Data-check-string is a concatenation of all received fields, sorted in alphabetical order, in the format key=<value> with a line feed character ('\n', 0x0A) used as separator"

```
secret_key = SHA256(<bot_token>)
data_check_string = ...  # alphabetically sorted key=value, \n-separated
verify: hex(HMAC_SHA256(data_check_string, secret_key)) == hash
```

**ВАЖНО:** Mini App initData — другой алгоритм: `secret_key = HMAC_SHA256(<bot_token>, "WebAppData")`. Mini App auth в allauth core пока НЕ покрыт → отдельный flow, отложить до Phase 5+.

allauth release 65.16.0 (2026-04-13); Telegram-провайдер активно поддерживается.

### Sources

- ★★★ https://docs.allauth.org/en/dev/socialaccount/providers/telegram.html
- ★★★ https://github.com/pennersr/django-allauth/blob/main/allauth/socialaccount/providers/telegram/views.py
- ★★★ https://core.telegram.org/widgets/login (HMAC spec)
- ★★★ https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

### Recommendation for Act

**Verdict: `ready_package`** — native provider, custom adapter НЕ нужен.

W1 sprint implementation:
1. Add `allauth.socialaccount.providers.telegram` в `INSTALLED_APPS`.
2. BotFather: создать бота, `/setdomain` — указать `act.app`.
3. `SOCIALACCOUNT_PROVIDERS['telegram']` config в `act/settings/base.py` (secrets через env).
4. Login Widget script на странице login.
5. NN #9 (ст. 12 ТППД consent) — гейтить через `ConsentRecord(purpose='cross_border_transfer')` ДО показа Telegram widget.

**Phase 5+ (deferred):** Mini App initData flow (~50-100 LOC custom view).

**Side effect:** обновить `identity_auth/CLAUDE.md` («Telegram OIDC primary — `django-allauth` + custom adapter (~100 строк)») — больше НЕ верно.

**Confidence:** HIGH.

-----

## R3. next-intl + Next.js 16 — ⚠️ middleware → proxy.ts

### Findings

**Next.js 16 переименовал `middleware.ts` → `proxy.ts`** (file-system convention, не next-intl сам по себе). Verbatim из Next.js docs:

> "You are using the `middleware` file convention, which is deprecated and has been renamed to `proxy`."
> — nextjs.org/docs/messages/middleware-to-proxy

> "The middleware filename is deprecated, and has been renamed to proxy to clarify network boundary and routing focus. **The edge runtime is NOT supported in proxy. The proxy runtime is nodejs, and it cannot be configured.**"
> — nextjs.org/docs/app/guides/upgrading/version-16

**next-intl latest:** 4.12.0 (2026-05-13). next-intl 4.0 принёс breaking changes:
1. **`NextIntlClientProvider` обязателен** в root layout (был optional в 3.x).
2. **`locale` обязателен** в return из `getRequestConfig`.
3. **`createMiddleware` → wrapper в `proxy.ts`**.

Verbatim recommended setup:

```ts
// src/proxy.ts
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

const intlProxy = createMiddleware(routing);

export function proxy(request) {
  return intlProxy(request);
}

export const config = {
  matcher: '/((?!api|_next|_vercel|.*\\..*).*)',
};
```

```tsx
// app/[locale]/layout.tsx
import {setRequestLocale} from 'next-intl/server';
import {hasLocale, NextIntlClientProvider} from 'next-intl';
import {notFound} from 'next/navigation';
import {routing} from '@/i18n/routing';

export default async function LocaleLayout({children, params}) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}
```

```ts
// src/i18n/request.ts
import {getRequestConfig} from 'next-intl/server';
import {hasLocale} from 'next-intl';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested) ? requested : routing.defaultLocale;
  return {
    locale,                       // ← required в v4
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
```

**`setRequestLocale(locale)` обязан в каждом layout/page**, который должен быть статическим, ДО `getTranslations`/`useTranslations`.

**Russian plurals:** ICU MessageFormat в next-intl поддерживает CLDR `one | few | many | other` (1/2-4/5+/1.5):

```json
{"followers": "{count, plural, =0 {No followers} one {# follower} few {# followers} many {# followers} other {# followers}}"}
```

### Sources (9 ★★★)

- ★★★ https://nextjs.org/blog/next-16
- ★★★ https://nextjs.org/docs/app/guides/upgrading/version-16
- ★★★ https://nextjs.org/docs/messages/middleware-to-proxy
- ★★★ https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- ★★★ https://next-intl.dev/docs/routing/middleware (now "Proxy / middleware")
- ★★★ https://next-intl.dev/docs/routing/setup (setRequestLocale)
- ★★★ https://next-intl.dev/blog/next-intl-4-0
- ★★★ https://github.com/amannn/next-intl/releases (v4.12.0, 2026-05-13)
- ★★★ https://www.npmjs.com/package/next-intl

### Recommendation for Act

**Verdict: `wrapper_only` setup** (proxy.ts + NextIntlClientProvider layout wrapper).

Phase 1.5 implementation:
1. Pin: `"next": "^16.0.0"`, `"next-intl": "^4.12.0"`.
2. **`src/proxy.ts`** (НЕ `middleware.ts`), named export `proxy`. Runtime: Node.js automatic.
3. `app/[locale]/layout.tsx`: `<NextIntlClientProvider>` обязателен; `setRequestLocale(locale)` первой строкой.
4. Каждая `page.tsx` под `[locale]`: вызывать `setRequestLocale(locale)` — иначе dynamic rendering.
5. `getRequestConfig` обязательно возвращает `{ locale, messages }`.
6. Route groups: `app/[locale]/(public)/`, `(authenticated)/`, `(organizer)/` — все ниже `[locale]`.
7. Codemod `npx @next/codemod@canary upgrade latest` — НЕ полагаться на silent rename middleware→proxy, проверить вручную.

**Side effect:** обновить `iteration-5.5-roadmap.md` step #16 от «next-intl proxy (не middleware) — Next 16» до явных action-items.

**Confidence:** HIGH (medium для production-references — конкретные репо не найдены, но docs полные).

-----

## R4. Procrastinate 3.8.1 + Django 5.2 + Python 3.12 — ⚠️ compatible но не в CI

### Findings

Latest: **procrastinate 3.8.1** (2026-04-08). Зависимости:
- `Requires: Python >=3.10`
- `django = ["django>=2.2"]` — open lower bound, без upper.

CI matrix: «latest Django for each Python» — Django 5.2 LTS **не в матрице** (тестируется только 6.0.x). 5.2 формально удовлетворяет `>=2.2` но **не покрыта** explicit CI.

**Sync API доступен:**
```python
import procrastinate
app = procrastinate.App(connector=procrastinate.SyncPsycopgConnector())

@app.task(queue="sums")
def sum(a, b):  # sync function
    ...
```

Release 3.0.0 notes: "Synchronous tasks are now launched asynchronously in a ThreadPoolExecutor using asgiref.sync_to_async."

**PgBouncer compatibility — critical:**

> "LISTEN/NOTIFY ... transaction pooling: No"
> — pgbouncer.org/features.html

NOTIFY (single statement) формально работает в transaction-mode, но LISTEN — нет. То есть:
- Web app `defer_async()` через pooled connection — OK.
- Worker обязан session-mode или прямой коннект к мастеру.

В Procrastinate **нет** polling-only режима — worker всегда LISTEN.

**Periodic tasks для Outbox poller (≤5s requirement):**

> "The cron syntax is on 5 columns ... an optional 6th column is supported for seconds with the same syntax, allowing you to make a periodic task as frequent as '1 per second'."

```python
@app.periodic(cron="*/5 * * * * *")  # каждые 5 секунд
@app.task(queueing_lock="outbox_poll")
def poll_outbox(timestamp: int): ...
```

**Django integration** (2.0.0+):
> "When using Procrastinate with Django, you don't need to define a Procrastinate App anymore ... As long as Procrastinate is in your INSTALLED_APPS, you can use procrastinate.contrib.django.app."

Management command: `python manage.py procrastinate worker -q outbox,emails -c 4`

### Sources (8 ★★★)

- ★★★ https://pypi.org/project/procrastinate/ (3.8.1, 2026-04-08)
- ★★★ https://procrastinate.readthedocs.io/en/stable/changelog.html
- ★★★ https://procrastinate.readthedocs.io/en/stable/howto/django/configuration.html
- ★★★ https://procrastinate.readthedocs.io/en/stable/howto/advanced/cron.html
- ★★★ https://procrastinate.readthedocs.io/en/stable/howto/django/basic_usage.html
- ★★★ https://github.com/procrastinate-org/procrastinate/releases/tag/2.0.0
- ★★★ https://www.pgbouncer.org/features.html
- ★★ https://jpcamara.com/2023/04/12/pgbouncer-is-useful.html

### Recommendation for Act

**Verdict: `procrastinate==3.8.1`** (pin or `>=3.8,<4`).

Phase 1.7 actions:
1. `pip install 'procrastinate[django,psycopg2]==3.8.1'`.
2. **Connection routing:**
   - Worker — прямой коннект к мастеру PG (FQDN `c-<cluster_id>.rw.mdb.yandexcloud.net`, port 5432), либо session-mode pgbouncer (если Yandex поддерживает).
   - Web app — pooled connection (transaction-mode OK).
3. **Outbox poller:** `@app.periodic(cron="*/5 * * * * *")`. Идемпотентность через `event.id` как dedupe key (ADR-016 уже фиксирует).
4. Sync API через `SyncPsycopgConnector` — соответствует Django 5.2 sync style.
5. **MANDATORY:** до production прогнать Act test-suite на pinned `django==5.2.x` + `procrastinate==3.8.1` локально + staging — official CI этого не делает.
6. Management command в systemd / Coolify: `python manage.py procrastinate worker --concurrency=4 --queues=outbox,emails`.

**Side effect:** Phase 1.1 (Yandex Cloud) setup должен включить либо session-mode pgbouncer pool для worker DB-user, либо direct master FQDN config.

**Confidence:** MEDIUM-HIGH (для самого пакета high; для Django 5.2 — medium из-за отсутствия CI).

-----

## R5. Yandex MDB PG 18 — ✅ available_now

### Findings

> "Managed Service for PostgreSQL supports PostgreSQL versions 14, 15, 16, 17, and 18, and PostgreSQL versions 14, 15, 16, 17, and 18 for 1C."
> — yandex.cloud/en/docs/managed-postgresql/qa/general (2026-05-05)

> "All extensions supported in PostgreSQL 17 are available for PostgreSQL 18."
> — yandex.cloud/en/docs/managed-postgresql/release-notes (December 2025)

**Upgrade path 17→18:** sequential in-place.

> "You can only upgrade to the next sequential version, e.g., from 14 to 15. Upgrading to subsequent versions must be done incrementally."
> — yandex.cloud/en/docs/managed-postgresql/operations/cluster-version-update (Updated 2026-03-05)

> "After the DBMS upgrade, you cannot revert a cluster to the previous version."
> "We recommend you first upgrade a test cluster with the same data and configuration."

**PG 18 native `uuidv7()`** (verbatim PostgreSQL 18 release notes):
> "Add UUID version 7 generation function uuidv7() (Andrey Borodin)"
> "This UUID value is temporally sortable. Function alias uuidv4() has been added to explicitly generate version 4 UUIDs."

### Sources

- ★★★ https://yandex.cloud/en/docs/managed-postgresql/qa/general (2026-05-05)
- ★★★ https://yandex.cloud/en/docs/managed-postgresql/release-notes
- ★★★ https://yandex.cloud/en/docs/managed-postgresql/operations/cluster-version-update (2026-03-05)
- ★★★ https://yandex.cloud/en/docs/managed-postgresql/operations/extensions/cluster-extensions (2026-05-14)
- ★★★ https://yandex.cloud/en/docs/cli/release-notes
- ★★★ https://www.postgresql.org/docs/current/release-18.html (2025-09-25)
- ★★★ https://www.postgresql.org/docs/current/functions-uuid.html

### Recommendation for Act

**Verdict: `available_now` + `in_place_supported` (sequential).**

Strategy:
1. **MVP — PG 17** (стабильный, все extensions есть; PG 18 в Yandex может иметь minor issues в первые месяцы GA).
2. **Q3-Q4 2026:** после 6-12 месяцев runtime PG 18 в Yandex — in-place upgrade 17→18.
3. После 17→18: `ALTER TABLE events_event ALTER COLUMN id SET DEFAULT uuidv7();` (нативный). UUIDv7 values из `pg_uuidv7.uuid_generate_v7()` бинарно идентичны (RFC 9562) — данные не мигрируются.
4. **Pre-upgrade ritual:** test-кластер из backup, full Act test-suite, EXPLAIN ANALYZE критических query, backup непосредственно перед.

**Side effect:** обновить ADR-006 — pg_uuidv7 confirmed v1.5 в Yandex MDB; PG 18 path добавить как «future upgrade».

**Confidence:** HIGH.

-----

## R6. django-cryptography-django5 — ⚠️ stale, нужна замена

### Findings

`django-cryptography-django5` v2.2 — last release 2024-06-04. Classifiers: `Django :: 5.0` (НЕ 5.1, НЕ 5.2). Python: 3.8-3.12.

Pyproject.toml Act сейчас pin'ит `django-cryptography-django5>=2.0`.

### Recommendation for Act

**Verdict: replace до W1 sprint.**

Кандидаты:
- **Option A:** `cryptography` напрямую + custom `EncryptedField` (~50 LOC). Низкие dependencies, полный контроль. Reference impl: identify_auth/CLAUDE.md уже описывает HMAC + encrypt pattern.
- **Option B:** `django-encrypted-model-fields` (если жив на момент проверки — research не верифицировал).
- **Option C:** `pgcrypto` на стороне PG (extension в Yandex allowlist). Минус: ключ хранится в БД либо передаётся в SQL — увеличивает audit-surface. ADR-014 уже отверг pgcrypto.

**Action needed:** ADR-014 review + ADR update + replacement choice ДО W1 PII implementation.

**Confidence:** MEDIUM (требует follow-up verification альтернатив).

-----

## R7. django-otp 1.7 + django-otp-webauthn 0.8 — ✅ Django 5.2 явно

### Findings

- `django-otp` 1.7.0 (2026-01-07, "Async support") + 1.6.0 (2025-04-02 — добавил Django 5.2 явно).
- `django-otp-webauthn` 0.8.0: classifiers `Django :: 5.2` и `Django :: 6.0`; Python 3.10-3.14.
- Maintainer (May 2025): "As of May 2025, I now consider this package stable enough for production use."

### Recommendation for Act

Bump pins в pyproject.toml:
```toml
"django-otp>=1.7,<2",
"django-otp-webauthn>=0.8,<1",
```
(Текущие: `>=1.5` и `>=0.3`.)

**Confidence:** HIGH.

-----

## R8. import-linter forbidden subpackages — alternative pattern

### Findings

> "forbidden_modules: ... These may include root level external packages (i.e. django, but not django.db.models). If external packages are included, the top level configuration must have **internal_external_packages = True**."
> — import-linter.readthedocs.io/en/stable/contract_types/forbidden/

То есть: `forbidden_modules = django` (root-level) разрешено, `django.db.backends.utils` (subpackage of external) — нет. Это и причина Phase 1.4 ошибки.

### Recommendation for Act

**Verdict: alternative cleaner pattern**, но текущий workaround (add `django` to `root_packages` + `allow_indirect_imports = True`) — работает.

Optional cleanup:
1. Убрать `django` из `root_packages`.
2. `forbidden_modules = django` (root-level).
3. `ignore_imports` для legitimate ORM использования.

ИЛИ оставить как есть — функционально equivalent.

**Confidence:** MEDIUM-HIGH.

-----

## Action plan для Act (приоритеты)

| Приоритет | Action | Effort | Зависит |
|---|---|---|---|
| **P0** | Save findings в репо (этот файл) | done | — |
| **P0** | identity_auth: Telegram custom adapter ~100 LOC → native provider (R2). Update CLAUDE.md + services.py docstrings. | 15 мин | — |
| **P0** | pyproject.toml bumps: django-otp >=1.7, django-otp-webauthn >=0.8, procrastinate ==3.8.1 (R4/R7). | 5 мин | — |
| **P1** | ADR-006 update: pg_uuidv7 confirmed v1.5; PG 18 upgrade path; activation через Terraform/yc CLI (НЕ SQL). | 20 мин | — |
| **P1** | ADR-014 review: django-cryptography-django5 stale → decision на замену (cryptography + custom field) (R6). | 30 мин + decision | founder input |
| **P1** | roadmap delta (`iteration-5.5.bis-roadmap.md`): применить findings к steps #15-18; обновить Phase 1.5 spec про `proxy.ts`. | 30 мин | — |
| **P2** | Phase 1.4.bis migrations prep (extensions + RLS policies): использовать R1/R5 findings. | 2-3 ч | P1 ADR-006 |
| **P3** | import-linter cleanup (R8): optional, может оставить текущий workaround. | 30 мин | — |

-----

## Notes / caveats из research

- **Yandex MDB pgbouncer pool-mode detail** — точная конфигурация per-DB session-mode НЕ верифицирована публично. Founder action: support ticket ИЛИ test cluster ИЛИ direct master FQDN для worker.
- **Production GitHub references** для next-intl 4 + Next.js 16 — конкретных репо не нашлось в budget'е research. Не блокер, но «no public reference».
- **Procrastinate Django 5.2 CI** — pinned local validation обязателен.
- **Mini App vs Login Widget** в Telegram — разные HMAC алгоритмы. allauth core покрывает только Login Widget. Mini App (Phase 5+) — отдельный custom view ~50-100 LOC.
- **Yandex docs URL canonicalization** — официальный домен `yandex.cloud/en/docs/...` (НЕ `cloud.yandex.com` legacy).
