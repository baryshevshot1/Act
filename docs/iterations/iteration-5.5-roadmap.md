# Iteration 5.5 — Next Steps Roadmap

> Strategic planning документ после Iteration 5 corrections. Превращает «много того, что можно сделать» в «вот ровно следующая последовательность с обоснованием»: Repository state snapshot · Open decisions · Roadmap DAG · Critical path · 7-day action plan.
>
> **Дата:** 2026-05-27.
> **Сессия:** Claude Opus 4.7 (planning-only, no code generation, no `git commit`).
> **Spec:** `prompts/next-steps-roadmap-planning.md` (Iteration 5.5).
> **Эпистемика:** `[F:]` факт со ссылкой; `[В]` вывод; `[Г]` гипотеза; `[?]` неизвестное.
> **Источники:** `CLAUDE.md`, `README.md`, `docs/CHANGELOG.md` (Unreleased + Wave 1-3), `prompts/README.md` (Iteration roadmap), `docs/ARCHITECTURE.md` (Bootstrap + Pilot Этап 0 + W1-W10 + Pre-pilot Compliance baseline), `docs/risk-register.md` (S/O/C/T categories), `docs/jtbd-bc-mapping.md` (Wedge focus + MVP-минимум BC), `docs/iterations/iteration-5-applied.md` (worklog 21 items), `docs/iterations/iteration-4.5-audit-report.md` (DoD pattern).

-----

## 1. Repository state snapshot

> Источник каждой цифры — `Bash`-проверка (`ls`, `find`, `test -f`) на дату 2026-05-27. Без интерпретаций — голые факты.

| Layer | Done | In progress | Missing |
|---|---|---|---|
| Documentation (4 main + supporting) | `README.md`, `CLAUDE.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md` (16 ADR + 6 Level C), `docs/CHANGELOG.md`, `docs/jtbd-bc-mapping.md`, `docs/risk-register.md`, `docs/design/principles.md`, `docs/pilot/day-template.md` | — | `docs/erd.md`, `docs/api/openapi.yaml`, `docs/glossary.md`, `docs/runbooks/*`, `docs/AI-WORKFLOW.md`, `SECURITY.md` (root) — все Iteration 8 |
| Compliance baseline (Pre-Phase 0) | — | — | 0.1 РКН ст. 22; 0.2 РКН ст. 12; 0.3 Privacy Policy; 0.4 Consent doc; 0.5 Cookie consent UI; 0.6 ИП + расчётный счёт; 0.7 домен (`act.app` или fallback) |
| Backend scaffolding | `backend/pyproject.toml`, `backend/.importlinter` (18 contracts), `backend/Dockerfile.dev`, `backend/apps/` (16 BC stubs + `core` + `recurrence_engine`, все только `__init__.py`), `backend/tests/`, `backend/scripts/`, `backend/act/`, `infra/postgres/init.sql` | — | `backend/manage.py`, `backend/requirements/{base,dev,prod}.in`, `backend/act/settings/{base,dev,prod}.py`, `apps/core/migrations/0001_extensions.py`, `apps/<ctx>/models.py` per BC, RLS middleware impl |
| Frontend scaffolding | `frontend/README.md`, `frontend/messages/{ru,en}.json` (placeholders), dir-каркас `app/components/public/styles/` | — | `frontend/package.json`, `frontend/next.config.mjs`, `frontend/tsconfig.json`, `frontend/middleware.ts`, `frontend/app/[locale]/(public)(authenticated)(organizer)/`, components без implementation |
| Infrastructure | `docker-compose.yml`, `Makefile`, `infra/postgres/init.sql`, dirs `infra/coolify/`, `infra/github-actions/` (пустые) | — | Yandex Cloud (folder + IAM + VPC + Compute + Managed PG 17 + Object Storage), Coolify install, `.github/workflows/ci.yml`, secrets, branch protection |
| Skills + CLAUDE.md hierarchy | `.claude/skills/write-rls-policy/SKILL.md` (NN #11), `.claude/skills/outbox-event/SKILL.md` (ADR-016); `backend/apps/identity_auth/CLAUDE.md` (Wave 1+ adjusted) | — | **8 SKILL.md** (recurrence-rrule, guest-rsvp-merge, auth-flow, add-translation, create-migration, add-bounded-context, write-adr, deploy-check); **5 per-context CLAUDE.md** (events, rsvp, contacts_sharing, recommendations, localization) |
| Level C status (по BC) | 6/16: identity_auth, events (с Recurrence), rsvp, contacts_sharing, recommendations, localization | — | 10/16: user_profile, verification, groups, ratings, discovery, notifications, moderation, analytics, admin_console, recurrence_engine standalone (если разделить) — все **пост-Pilot** [F: `docs/CHANGELOG.md` Unreleased § TODO] |
| Iteration memory | `docs/iterations/iteration-4.5-audit-report.md`, `docs/iterations/iteration-5-applied.md`, `docs/iterations/README.md`; `prompts/{iteration-0-bootstrap,iteration-4.5-audit,iteration-5-corrections}.md` | — | `prompts/iteration-6-skills-library.md`, `prompts/iteration-7-per-context-claude-md.md`, `prompts/iteration-8-docs-bootstrap.md`, `docs/iterations/iteration-{6,7,8}.md` worklog |
| Git state | Branch `claude/elegant-clarke-qe2HH`; HEAD = `ab2059b feat: bootstrap Act repository (Phase 0)`; 3 коммита; working tree clean | — | — |

-----

## 2. Open decisions требующие founder input

> 8 пунктов с предлагаемым default `[В]` и обоснованием. Каждый — с явным **unblocks** и **ETA для ответа**. Founder отвечает ДО запуска соответствующего шага.

| # | Decision | Default `[В]` | Обоснование default | Unblocks | ETA |
|---|---|---|---|---|---|
| D1 | Статус ИП + расчётного счёта (открыты ли?) | Зависит от факта | Без ИП невозможно: договор с Yandex.Cloud LLC (Phase 0.4), РКН-уведомления как оператор (Pre-Phase 0.1+0.2), приём платежей через ЮKassa в W6+ | Phase 0.1+0.2; Phase 1.1 Yandex Cloud setup | < 1 день |
| D2 | Compliance baseline start trigger — запускать НСЕЙЧАС параллельно с Iteration 6 или после Iteration 8? | **Сейчас** | РКН-проверка до 30 дней [F: ч. 4 ст. 22 152-ФЗ]; нет смысла блокировать timeline; 0.1+0.2 — founder-bound (не AI-task), независимы от Iter 6-8 | Phase 1 production-deploy (без 0.1+0.2 = штраф 100-300k ₽ для ИП по ч. 10 ст. 13.11 КоАП) | < 1 день |
| D3 | Domain choice — `act.app` ИЛИ `joinact.app` / `act.events` / `act-app.ru` | Проверить `whois act.app` и BotFather availability `act_bot`; если занят → `joinact.app` | `act.*` brand matches переименование (Wave 1) [F: `README.md` TODO line 15]; `.app` форсирует HTTPS; fallback `joinact.app` — generic English | Iter 8 docs (ссылки на canonical домен); Phase 1.1 (DNS setup) | < 2 дня |
| D4 | Iteration 6 launch mode — new Claude Code session ИЛИ продолжение текущей? | **New session** | Iteration 5 закрыт коммитом; promt 6 должен быть self-contained per Anthropic Boltzmann pattern [F: `docs/CHANGELOG.md` Failed approaches + `prompts/README.md` § Anthropic Boltzmann pattern] | Iteration 6 execution | 1 час на подготовку `prompts/iteration-6-skills-library.md` |
| D5 | Privacy Policy template — взять готовый template (e.g. Тильда / Юрист24 / opensource RU template) ИЛИ заказать у юриста | **Готовый template + customization под Act** | 0.3 имеет срок «1 день» [F: `docs/ARCHITECTURE.md` Phase 0]; ст. 18.1 152-ФЗ требует обязательных пунктов, не уникального текста; кастомизация под ТППД-получателей Telegram FZ-LLC | Pre-Phase 0.3 + 0.4 (consent doc reuses many sections) | 2-4 часа на drafting |
| D6 | Email ESP final — UniSender vs SendPulse | **UniSender** `[Г]` | Phase 0.10 — «2 часа выбор» [F: `docs/ARCHITECTURE.md` Phase 0]; обе RU, обе compliant; UniSender чаще упоминается в RU SaaS sources как mature; final decision — после feature parity check | W6 Notifications + email магических ссылок | 2 часа |
| D7 | Apple Developer Program registration — Phase 5+ ИЛИ now (для подготовки)? | **Defer до post-Pilot** | NN #5 [F: `CLAUDE.md`] — Through Phase 5 только PWA + Telegram Mini App; регистрация требует foreign card + VPN; не на critical path для MVP | Phase 5+ iOS native | N/A до Phase 5 |
| D8 | Yandex Lockbox setup — в Phase 1.1 (сразу с Cloud setup) ИЛИ позже (когда появится первое PII-поле в W1)? | **Phase 1.1** | NN #7 [F: `CLAUDE.md`] + ADR-014 — django-cryptography требует Lockbox key с дня 1; дешевле настроить вместе с Cloud, чем возвращаться | W1 Identity & Auth (phone + email encryption) | 1 час в Phase 1.1 |

-----

## 3. Roadmap DAG

> 25 шагов от Iteration 6 до Soft launch. **Type** ∈ {Tooling · Compliance · Code · Infra · Decision · External · Legal}. **Blockers** — что должно быть готово ДО; **Unblocks** — что становится возможным ПОСЛЕ. **Risk** — cross-ref на номер из `docs/risk-register.md` + NON-NEGOTIABLE из `CLAUDE.md`. Time `[Г]` calibrated по `docs/CHANGELOG.md` TODO entries и Phase 1 Bootstrap (3-7 дней) из `docs/ARCHITECTURE.md`.

| # | Step | Type | Blockers | Unblocks | Acceptance criteria (Done) | Time `[Г]` | Risk |
|---|---|---|---|---|---|---|---|
| 1 | **Iteration 6** — 8 SKILL.md (recurrence-rrule · guest-rsvp-merge · auth-flow · add-translation · create-migration · add-bounded-context · write-adr · deploy-check) | Tooling | D4 | Iter 7; better Phase 1 PR quality | 8 SKILL.md в `.claude/skills/<name>/SKILL.md` проходят DoD-чек по 4.5 pattern (frontmatter `name` + `description` + `allowed-tools`; [F:] source per spec block; ≤ 100 строк) | ~3h | — |
| 2 | **Iteration 7** — 5 per-context CLAUDE.md (events · rsvp · contacts_sharing · recommendations · localization) | Tooling | 1 | Iter 8; Phase 1.4 Django skeleton effective | 5 `backend/apps/<ctx>/CLAUDE.md` по образцу identity_auth (DoD: ≤ 100 строк; верхняя секция «Назначение BC + Level C cross-ref»; explicit NON-NEGOTIABLE ссылки; cross-ref на относимые SKILL.md из Iter 6) | ~2h | — |
| 3 | **Iteration 8** — Docs bootstrap (`docs/erd.md` Mermaid + `docs/api/openapi.yaml` stub + `docs/glossary.md` + `docs/runbooks/{deploy,rollback,db-restore}.md` + `docs/AI-WORKFLOW.md` + `SECURITY.md` root) | Tooling | 2 | Phase 1 quality (Claude Code в Phase 1.4-1.5 опирается на erd/openapi для models/api stubs) | 6 файлов в репо; erd покрывает 16 BC; openapi stub содержит paths `/auth/* /events/* /rsvp/*`; glossary 30+ терминов из ARCHITECTURE.md и PRODUCT.md | ~4h | — |
| 4 | **Pre-Phase 0.6** — Domain choice + регистрация | External | D3 | Phase 1.1 (DNS); Iter 8 (canonical домен в openapi servers + erd) | Домен зарегистрирован в Reg.ru / Yandex Domains; DNS зона создана; `act_bot` (или fallback) занят в BotFather | ~1 day | — |
| 5 | **Pre-Phase 0.1** — РКН ст. 22 уведомление (founder-bound) ⚙ | Compliance | D1 (ИП) | Phase 1 production-deploy (без 0.1 = штраф); 0.4 consent doc | Регистрация в реестре операторов ПДн РКН подтверждена (выписка из реестра в `docs/compliance/`) | ~1-30 дней (срок РКН) | ⚠ NN #10, C2 |
| 6 | **Pre-Phase 0.2** — РКН ст. 12 уведомление (ТППД в Telegram) ⚙ | Compliance | D1 (ИП); параллельно с 5 | Telegram OIDC + bot usage в production; W6 Notifications через Telegram | Подтверждение приёма + опубликовано на сайте оператора (`/privacy` секция «Получатели») | Параллельно с 5 | ⚠ NN #9, NN #10, C1, C2 |
| 7 | **Pre-Phase 0.3** — Privacy Policy опубликована на `/privacy` | Compliance | D5; minimum HTML page | Phase 1 production-deploy; 7 consent doc; cookie banner copy | `/privacy` доступен, содержит обязательные пункты ст. 18.1 + явный список ТППД-получателей + страны хранения + категории ПДн | ~1 day | ⚠ NN #1, NN #9 |
| 8 | **Pre-Phase 0.4** — Consent document + signup checkbox ⚙ | Compliance | D5; 7 | Phase 1 signup flow в W1 | Отдельный документ (не вложен в оферту); чекбокс на signup; запись в `identity_auth_consent` с `purpose='core_processing'` | ~1 day | ⚠ NN #2, NN #10 |
| 9 | **Pre-Phase 0.5** — Cookie consent UI (3 уровня: Essential / Analytics / Marketing) | Compliance / Code | Phase 1.5 (Next.js frontend готов); 7 (Privacy refers cookie types) | Production deploy | Banner-component в Next.js; запись `identity_auth_consent` с purposes `cookies_essential/analytics/marketing`; persistence + edit per-session | ~1-2 days | ⚠ NN #10 |
| 10 | **Pre-Phase 0.10** — Email ESP контракт (UniSender или SendPulse) ⚙ | External | D1 (ИП), D6 | W6 Notifications (email); магические ссылки в W1 | Контракт подписан + API ключ в `.env` (placeholder) + verified domain | ~2h | — |
| 11 | **Phase 1.2** — GitHub branch protection + GHA secrets ⚙ | Infra | None (можно сразу) | Все future PRs; CI в Phase 1.6 | Branch protection на `main` (require PR + status checks); secrets `YANDEX_*`, `DATABASE_URL_*`, `SENTRY_DSN`, `TELEGRAM_*` в GHA | ~1h | ⚠ O4 |
| 12 | **Phase 1.3** — Local dev (Python 3.12 pyenv · Node 20 + pnpm · Docker Compose) | Code | None | Phase 1.4 + 1.5 | `python --version` = 3.12; `node --version` = 20; `docker compose up postgres` работает; pre-commit hooks installed | ~2h | — |
| 13 | **Phase 1.1** — Yandex Cloud setup (folder prod/dev + IAM SA + VPC + 1× Compute 4vCPU 8GB + Managed PG 17 s3.micro + Object Storage bucket + Lockbox key) | Infra | D1 (ИП); D8 (Lockbox in 1.1); 5+6 поданы (можно начать setup до их завершения — production deploy блокирован, но setup нет) | Phase 1.4.bis migration; Phase 1.7 Procrastinate; Phase 1.8 Coolify | `yc` CLI работает; PG доступен через прямой connection + PgBouncer; S3 bucket с CORS для CDN; Lockbox key created | ~4-8h | ⚠ O1, O4 |
| 14 | **Phase 1.4** — Django skeleton (`requirements/{base,dev,prod}.in` + pip-compile · settings layered base→dev/prod · 3 BC `identity_auth/events/rsvp` с базовыми models · CSP middleware · django-allauth · RLS middleware импл) | Code | 12, 13, Iter 7 (per-context CLAUDE.md) | Phase 1.4.bis | `python manage.py check` = 0 errors; `python manage.py runserver` поднимается; 3 BC имеют `models.py` + `services.py` stubs; RLS middleware установлен | ~6-8h | ⚠ T3 (RLS) |
| 15 | **Phase 1.4.bis** — `apps/core/migrations/0001_extensions.py` (`pgcrypto`, `btree_gist`, `pg_trgm`, `unaccent`, `pg_uuidv7`) ПРЯМЫМ PG, минуя PgBouncer | Code | 14 | Phase 1.5+; W3 Events models; `id BIGINT GENERATED ALWAYS AS IDENTITY` или uuid_v7 PKs | `PG_BOUNCER_HOST="" python manage.py migrate` успешно; `SELECT extname FROM pg_extension` показывает 5 extensions | ~1h | ⚠ NN #11 (PgBouncer incompat) |
| 16 | **Phase 1.5** — Next.js skeleton (App Router `[locale]/(public)(authenticated)(organizer)/` + next-intl proxy не middleware + TypeScript strict) | Code | 12 (можно параллельно с 14) | Phase 1.8 deploy; Pilot core-flow | `pnpm dev` поднимается на :3000; `/ru/` и `/en/` рендерят placeholder; tsconfig strict mode | ~3-4h | — |
| 17 | **Phase 1.6** — import-linter в CI | Code | 11, 14 | All future PRs (architectural enforcement) | `.github/workflows/ci.yml` запускает `lint-imports`; failing import нарушает CI | ~1h | — |
| 18 | **Phase 1.7** — Procrastinate periodic-task stub (Recurrence Engine + outbox poller заглушки) | Code | 14, 15 | W5 Recurrence; W6 outbox delivery | `python manage.py procrastinate worker` поднимается; одна periodic-task выполняется по cron | ~1-2h | — |
| 19 | **Phase 1.8** — Coolify install на Yandex Compute | Infra | 13 | Pilot deploys; production deploys | Coolify UI доступен через HTTPS; admin аккаунт создан; первый deploy stub приложения работает | ~2-4h | ⚠ O1, T7 |
| 20 | **Phase 1.9** — Cost monitoring (Yandex Cloud Budget Alerts 1k/5k/10k ₽ MTD + Telegram bot нотификации) | Infra | 13 | Защита от runaway costs | 3 budget alerts настроены; test notification приходит в Telegram-bot | ~1h | ⚠ — (защита) |
| 21 | **Pilot Этап 0** — Core-flow end-to-end в проде на Coolify (Telegram OIDC signup → создать event → share OG → guest RSVP → организатор видит в admin); ежедневный трекинг 10 risk checks в `docs/pilot/day-N.md` | Code | 11-20 done; 5+6 поданы (production deploy нельзя без РКН-регистрации — но можно тестовый домен / staging) | ADR-007 decision | Accept-Rate ≥ 60% **или** branch на Fix/Pivot; ≤ 10 import-linter violations за пилот; ≤ 7 рабочих дней | ~5-7 рабочих дней | ⚠ S4 (burnout), O2 (ORM), T1-T10 |
| 22 | **ADR-007 decision gate** — `docs/decisions/ADR-007-stack-commit.md` (MADR 4.0) | Decision | 21 | MVP W1-W10 (Go) ИЛИ Fix 3-day ext ИЛИ Pivot re-open backend | ADR-007 написан с verdict + reference to `docs/pilot/day-7-decision.md` | ~0.5 day | — |
| 23 | **MVP W1-W10** (10 недель, каждая = один user flow): W1 Identity+Profile+i18n · W2 Verification · W3 Events CRUD · W4 Groups · W5 Recurrence · W6 RSVP+Attendance+Notifications · W7 Ratings · W8 Discovery · W9 Admin+Moderation · W10 Polish + security review | Code | 22 (Go); compliance 0.1-0.5 завершены ДО W10 | Soft launch | Каждая неделя имеет `docs/iterations/sprint-W{N}.md` с DoD; staging→production deploy без RLS violations; 70% test coverage | ~8-10 недель | ⚠ S3 (cold-start), S4, O2 |
| 24 | **Iteration 9** — 10 missing Level C drafts (user_profile · verification · groups · ratings · discovery · notifications · moderation · analytics · admin_console · recurrence_engine standalone) — параллельно с W2+ MVP | Tooling | 21 success (Pilot inform Level C decisions); 23 (start) | W4-W9 implementation quality (Level C → models + services) | 10 Level C в `docs/ARCHITECTURE.md` (расширение существующей секции); каждый покрывает: aggregates, services signatures, RLS-tables, outbox subscriptions | ~3-4 недели (parallel с MVP) | — |
| 25 | **Soft launch** — ручной outreach 50-100 тренеров регулярных групп в Москве; private beta; KPI = NSM (Confirmed Weekly Attendances) ≥ 5 за неделю 4 | External | 23 done; 5+6+7+8+9 done (production legal) | Wedge validation; Series A pre-discovery | ≥ 30 активных еженедельных серий за 4 недели [F: `docs/risk-register.md` S3 trigger]; Accept-Rate тренеров на core-flow ≥ 60% | ~2-4 недели | ⚠ S1 (wedge invalidate), S3 |

-----

## 4. Critical path

> Минимальная серийная последовательность от now (2026-05-27) до Soft launch. ║ — параллельный трек. Источники estimates — `docs/CHANGELOG.md` Unreleased + `docs/ARCHITECTURE.md` Phase 0/1 + Pilot Этап 0 секции.

```
1. [Now → +1-2 раб. дня] Iteration 6 (8 SKILL.md, ~3h)
   ║ В параллель ⚙ founder: Pre-Phase 0.1 + 0.2 (РКН ст. 22 + ст. 12, founder-bound; до 30 дней проверки)
   ║ В параллель ⚙ founder: D3 domain whois + BotFather check (≤ 2 дня)
   ║ В параллель ⚙ founder: D1 ИП status (если не открыт)
   
2. [+1 раб. день] Iteration 7 (5 per-context CLAUDE.md, ~2h) — серийно после 1.

3. [+1 раб. день] Iteration 8 (6 docs артефактов, ~4h) — серийно после 2.
   ║ В параллель ⚙ founder: Pre-Phase 0.3 + 0.4 (Privacy Policy + Consent doc, ~2 дня; D5 template choice)
   ║ В параллель ⚙ founder: D6 Email ESP final → 0.10 контракт UniSender/SendPulse
   ║ В параллель ⚙ founder: 0.6 domain регистрация

4. [+3-7 раб. дней] Phase 1 Bootstrap (параллельные подэтапы):
   a. Phase 1.1 Yandex Cloud setup (~4-8h) — требует ИП + 0.6 domain
   b. Phase 1.2 GitHub branch protection (~1h) — независимо
   c. Phase 1.3 Local dev (~2h) — независимо
   d. Phase 1.4 Django skeleton (~6-8h) — после 1.1 + 1.3 + Iter 7
   e. Phase 1.4.bis PG extensions migration (~1h) — после 1.4
   f. Phase 1.5 Next.js skeleton (~3-4h) — параллельно с 1.4
   g. Phase 1.6 import-linter в CI (~1h) — после 1.2 + 1.4
   h. Phase 1.7 Procrastinate stub (~1-2h) — после 1.4
   i. Phase 1.8 Coolify install (~2-4h) — после 1.1
   j. Phase 1.9 Cost monitoring (~1h) — после 1.1
   ║ В параллель ⚙ founder: 0.5 Cookie consent UI design (после 1.5 готов, ~1-2 дня)

5. [+5-7 раб. дней] Pilot Этап 0 (core-flow end-to-end, daily tracking 10 risk checks)
   Pre-condition: Phase 1 a-j done; РКН-регистрация можно ждать (Pilot — на staging domain, не production)

6. [+0.5 дня] ADR-007 decision gate
   ├── Go (Accept-Rate ≥ 60%, ≤ 10 import-linter violations, ≤ 7 рабочих дней) → step 7
   ├── Fix (Accept-Rate 45-59% ИЛИ ≥ 1 риск в зоне Fix) → 3-day extension + повторный замер → step 6
   └── Pivot (Accept-Rate < 45% ИЛИ > 1 риск в зоне Pivot ИЛИ невозможно собрать core-flow за 10 дней) → переоткрытие backend (FastAPI как альтернатива Django) — этот roadmap инвалидируется, нужен новый

7. [+8-10 недель] MVP W1-W10 (по неделе на user flow)
   ║ В параллель: Iteration 9 (10 missing Level C drafts, ~3-4 недели) — стартует в W2+
   ║ В параллель ⚙ founder: получение РКН-регистрации (если ещё не пришла) — БЛОКЕР для W10 production deploy

8. [+2-4 недели] Soft launch — 50-100 тренеров вручную в Москве; private beta; NSM tracking
```

**Суммарная оценка от 2026-05-27 до Soft launch (Go-сценарий):**

| Этап | Min | Max | Calibration source |
|---|---|---|---|
| Iter 6+7+8 | 1 раб. день | 2 раб. дня | `prompts/README.md` Iteration roadmap (~3h+2h+4h `[Г]`) |
| Phase 1 Bootstrap | 3 раб. дня | 7 раб. дней | `docs/ARCHITECTURE.md` Phase 1 «3-7 дней» |
| Pilot Этап 0 | 5 раб. дней | 10 раб. дней (с 3-day Fix ext) | `docs/ARCHITECTURE.md` Pilot Этап 0 «5-7 рабочих дней» + exit criterion 2 |
| ADR-007 gate | 0.5 day | 0.5 day | `docs/ARCHITECTURE.md` Decision gate |
| MVP W1-W10 | 8 недель | 12 недель (с slippage `[Г]`) | `docs/ARCHITECTURE.md` Спринты W1-W10 |
| Soft launch | 2 недели | 4 недели | `docs/PRODUCT.md` + `docs/risk-register.md` S3 trigger «< 30 активных серий за 4 недели» |
| **Total** | **~13 недель (≈ 3 мес)** | **~20 недель (≈ 5 мес)** | — |

**Compliance baseline (Track B)** идёт параллельно, terminal до W10 — **БЛОКЕР для production deploy в W10**. Если РКН-проверка > 30 дней или fail → откат на staging-only до получения регистрации.

-----

## 5. Next 7-day action plan

> Конкретные действия, не «работать над X». Соглашения: ⚙ = founder-only action (legal/external/decision); 🤖 = Claude Code task (AI-execution); 📋 = decision/review.

### Day 1 (2026-05-27, today): Iteration 6 prep + Compliance kickoff

- **1.1 🤖** Создать `prompts/iteration-6-skills-library.md` по образцу `prompts/iteration-5-corrections.md` — содержит: roles · 8 SKILL.md spec (recurrence-rrule, guest-rsvp-merge, auth-flow, add-translation, create-migration, add-bounded-context, write-adr, deploy-check) · DoD per skill (frontmatter + body + [F:] sources) · workflow per Iteration 4.5 audit. ETA: ~30 мин.
- **1.2 ⚙** Проверить статус ИП + расчётного счёта; если ИП открыт → запустить ст. 22 РКН-уведомление через `pd.rkn.gov.ru/operators-registry/notification/` (Pre-Phase 0.1). ETA: 1-2 часа на форму.
- **1.3 ⚙** `whois act.app` + `act_bot` через BotFather; зафиксировать verdict в `docs/iterations/iteration-5.5-roadmap.md` § 6 (or отдельный коммит). ETA: 15 мин.
- **1.4 📋** Ответить на 8 open decisions из § 2 этого документа (можно inline-edit или коротко в чате). ETA: 30 мин.

### Day 2: Iteration 6 execution + 0.2 РКН

- **2.1 🤖** Запустить Iteration 6 в новой Claude Code сессии (Opus 4.7, `prompts/iteration-6-skills-library.md` в первом сообщении). Output: 8 SKILL.md в `.claude/skills/<name>/SKILL.md`. ETA: ~3h.
- **2.2 ⚙** Подать ст. 12 РКН-уведомление (ТППД в Telegram), отдельное от 0.1. ETA: 1-2 часа.
- **2.3 📋** Founder review Iteration 6 output (`git diff` 8 файлов); если pass DoD — `git commit` от founder. ETA: 30 мин.

### Day 3: Iteration 7 prep + Privacy Policy drafting

- **3.1 🤖** Создать `prompts/iteration-7-per-context-claude-md.md` (5 per-context CLAUDE.md spec: events / rsvp / contacts_sharing / recommendations / localization; DoD pattern — same как identity_auth/CLAUDE.md). ETA: ~30 мин.
- **3.2 ⚙** Подобрать Privacy Policy template (RU); customize под Act (ТППД-получатели: Telegram FZ-LLC, ОАЭ; страны хранения: РФ + ОАЭ + NL + SG; категории ПДн из 0.1 уведомления). ETA: 2-3 часа.

### Day 4: Iteration 7 execution + Consent doc

- **4.1 🤖** Запустить Iteration 7 в новой Claude Code сессии. Output: 5 per-context CLAUDE.md. ETA: ~2h.
- **4.2 ⚙** Drafting consent document (отдельный от Privacy Policy и оферты per ст. 9 ред. 156-ФЗ); 1 страница. ETA: 1-2 часа.
- **4.3 📋** Founder review Iteration 7; commit. ETA: 30 мин.

### Day 5: Iteration 8 prep + domain регистрация

- **5.1 🤖** Создать `prompts/iteration-8-docs-bootstrap.md` (spec для 6 артефактов: erd.md / openapi.yaml / glossary.md / runbooks/{deploy,rollback,db-restore}.md / AI-WORKFLOW.md / SECURITY.md). ETA: ~30 мин.
- **5.2 ⚙** Регистрация домена (Reg.ru или Yandex Domains) — `act.app` или fallback `joinact.app`. ETA: 30 мин.
- **5.3 ⚙** Финализировать выбор Email ESP (D6) → запустить регистрацию контракта UniSender/SendPulse. ETA: 1 час.

### Day 6: Iteration 8 execution

- **6.1 🤖** Запустить Iteration 8 в новой Claude Code сессии. Output: 6 файлов (erd / api / glossary / runbooks×3 / workflow / SECURITY). ETA: ~4h.
- **6.2 📋** Founder review Iteration 8; commit. ETA: 1 час.

### Day 7: Phase 1 prep + verify gates

- **7.1 📋** Verify gates перед Phase 1: (a) ИП открыт; (b) 0.1+0.2 поданы (даже если регистрация ещё не пришла — это OK для setup, БЛОКЕР только для production deploy); (c) Iter 6+7+8 commit-нуты; (d) домен зарегистрирован. ETA: 30 мин.
- **7.2 ⚙** Если все gates pass → начать Phase 1.1 (Yandex Cloud signup → folder structure → IAM SA). ETA: 2-4 часа.
- **7.3 🤖** (Опционально) Создать `prompts/phase-1-bootstrap.md` если хочется AI-driven Phase 1.4-1.7 (recommended given Iter 4.5/5 pattern). ETA: ~1 час.

**Если в Day 7 не все gates passed:** буфер на догон + переход к Day 8+ с тем же содержимым.

-----

## 6. Открытые вопросы за горизонтом 7 дней

> Не требуют ответа сейчас, но founder должен иметь их в виду при планировании +14-90 дней.

1. **Pivot decision criteria для ADR-007** — определить ДО Pilot start. Какие конкретно «риск в зоне Pivot» из 10 risk checks приведут к re-open backend? Сейчас все 10 имеют criteria, но composite verdict при mixed signals — нет. См. `docs/ARCHITECTURE.md` § Pilot Этап 0.
2. **Soft launch target metrics** — что считать «успешным wedge validation»? NSM ≥ 5 / неделя (S3 trigger says < 30 серий за 4 недели = failure)? Иначе?
3. **KudaGo API access** — запрос подавать в Phase 0.8 (1-2 недели ответа) ИЛИ в Phase 4 (post-Pilot)? Для wedge JTBD-2 не нужен. См. `docs/jtbd-bc-mapping.md` (JTBD-8 NOT IN MVP).
4. **PostHog self-hosted** — поднимать в Phase 1.1 (с Yandex Cloud setup) ИЛИ в W7 (Ratings/Reputation — первый источник event-данных)?
5. **Sentry vs GlitchTip** — финальный выбор; рекомендация Sentry self-hosted для лучшего DX (но GlitchTip легче).
6. **Backup git repo в Selectel S3** (Plan B per O4 риск) — когда настраивать? Рекомендация: после Phase 1.1, weekly cron через GHA.
7. **SBOM generation** — Phase 1 или после первого production release?
8. **RuStore distribution** — Phase 6+ (нужно ИП-юр.лицо отдельно от обычного ИП?). Параметры не verified.
9. **Wedge invalidation thresholds** — S1 risk trigger «< 30% confirmation в Этап 0 интервью». Запланировать 10-15 интервью с тренерами в Москве в Day 8-14 для empirical validation.
10. **Apple Developer Program registration** — defer до Phase 5+ per D7; но проверить feasibility per current санкционные изменения в Q3 2026.

-----

## 7. Triggers пересмотра этого roadmap

> Условия, при которых этот документ требует обновления (Iteration 5.5.bis или новый Iteration 10 spec).

- **Iteration N (6/7/8) занимает > 2× estimated time** (e.g. Iter 6 > 6h) → review: CLAUDE.md иерархия / SKILL.md разбиение неоптимальны.
- **Любой trigger из § 5.6 risk register наступает** (e.g. РКН-проверка > 30 дней, vendor price hike +30%, ИП заблокирован за санкции).
- **ADR-007 commit gate fail** (Pivot verdict) → mandatory re-plan: новый roadmap с FastAPI / Rails 8 backend; этот документ инвалидируется.
- **Wedge invalidation** (S1: < 30% confirmation от тренеров в Этап 0 интервью) → re-plan на JTBD-4 хобби-группы.
- **Burnout signal от founder** (S4: > 7/10 субъективно > 2 недель) → re-plan: reduce scope (e.g. drop W7 Ratings до post-MVP) или delay timeline без re-scope.
- **Compliance escalation** (РКН требует доработать уведомление; жалоба пользователя; письмо РКН) → freeze MVP development до compliance ready.
- **Phase 1 Pilot timing slippage > 7 рабочих дней** (вышли за 3-7 days estimate) → re-evaluate Iter 8 docs completeness (возможно нужен Iter 8.5 audit).
- **Stack alternative emerges** (новая RU-managed Postgres с лучшей RLS performance; Yandex Cloud meaningful price changes) → defer до ADR-007 commit, не менять curr roadmap.

**Routine review cadence:** этот документ должен пересматриваться **(a) после ADR-007 gate** (mandatory; success/fix/pivot все три requires re-plan для W1-W10) и **(b) каждые 2 недели в W1-W10** для tracking slippage против estimates.

-----

*Конец Iteration 5.5 — Next Steps Roadmap (planning-only, без code changes / commits / pushes).*
