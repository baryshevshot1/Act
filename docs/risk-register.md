# Act — Risk register

> Объединённый реестр рисков из 4 источников:
> 1. PDF `Leto_project_p2.pdf` раздел «Главные риски» (Wave 0).
> 2. PDF `Leto_project_p3.pdf` секция 16 (Risk register V1.2).
> 3. PDF `Leto_project_p3.pdf` секция 21 (10 Risk checks перед stack commit).
> 4. `ARCHITECTURE.md` секция «Risk register» (Wave 1+).
> Эпистемика: `[F:]` факт; `[В]` вывод; `[Г]` гипотеза; `[?]` неизвестное.

## Категории

- **Strategic** — wedge, конкуренция, PMF.
- **Operational** — vendor, performance, hiring.
- **Compliance** — 152-ФЗ, санкции, регуляторика.
- **Technical (Pilot checks)** — 10 чеков перед stack commit (см. ADR-007, не ADR-005).

## Strategic risks

| # | Риск | P | I | Trigger | Mitigation | Источник |
|---|---|---|---|---|---|---|
| S1 | Wedge не валидируется (< 30% тренеров подтверждают pain point) | M | H | Этап 0 интервью даёт < 30% confirmation | Pivot на JTBD-4 хобби-группы (настолки, бук-клубы) | PDF p2 «Recommendations» |
| S2 | Конкурентная атака (Luma RU / VK / Yandex запускают аналог > 100K MAU/квартал) | L | H | Mention в новостях или 100K MAU замечен | Фокус на recurring per-event RSVP + verified эксперт-категория; не играть в Luma-копию | PDF p2 «Главные риски» |
| S3 | Cold-start liquidity failure | M | H | < 30 активных еженедельных серий за 4 недели в Этапе 3 | Synthetic supply через KudaGo + ручной outreach 50-100 тренеров | PDF p2 + `ARCHITECTURE.md` |
| S4 | Бёрнаут соло-фаундера | M | H | > 7/10 субъективно в течение 2 недель | Modular monolith дисциплина; no on-call; T&S SLA рабочие часы | PDF p2 «Главные риски» #6 |

## Operational risks

| # | Риск | P | I | Trigger | Mitigation | Источник |
|---|---|---|---|---|---|---|
| O1 | Vendor lock-in на Yandex Cloud | M | H | Yandex прайс +30% / квартал ИЛИ закрытие для ИП | Selectel as Plan B; Docker Compose portable; `pg_dump` weekly в Selectel S3 | `ARCHITECTURE.md` Risk #1 |
| O2 | Performance ceiling Django ORM | M | M | p95 latency > 500ms на любом endpoint | django-silk profiling с дня 1; raw SQL в hot paths (через `apps.core.rls.*`); FastAPI extraction для read-heavy | `ARCHITECTURE.md` Risk #2 |
| O3 | Hiring impossibility (Python+Django pool узкий в РФ) | L | M | Решение нанять + неделя без кандидатов | Phased rewrite на TypeScript + NestJS, начать с Frontend BFF | `ARCHITECTURE.md` Risk #3 |
| O4 | Санкционный риск GitHub / Yandex / др | H | H | Один пропущенный билд или отказ Yandex | Plan B на Forgejo + Selectel; backup git-repo еженедельно в S3; SBOM локально | `ARCHITECTURE.md` Risk #4 |
| O5 | Burnout / wrong-choice rollback cost (выбор Django + Yandex не такой productive как казалось) | M | H | 30 дней разработка < 50% плана; rework > 30% | Pilot Этап 0 (5-7 дней) с явным KPI Accept-Rate ≥ 60%; rollback без emotional sunk-cost | `ARCHITECTURE.md` Risk #5 |

## Compliance risks

| # | Риск | P | I | Trigger | Mitigation | Источник |
|---|---|---|---|---|---|---|
| C1 | РКН меняет статус Telegram FZ-LLC ОАЭ / NL / SG в Приказе №128 | L | H | Изменение перечня на сайте РКН или письмо | Domestic-fallback готов (ADR-013); migration на чисто-SMS режим за 1 неделю | `ARCHITECTURE.md` Risk #6 |
| C2 | Compliance audit РКН с штрафом по ч. 10 ст. 13.11 КоАП | L | H | Жалоба пользователя или плановая проверка | Compliance baseline в Pre-pilot (ADR-012) выполнен ДО первой production-публикации; уведомления ст. 22 + ст. 12 поданы | `ARCHITECTURE.md` Risk #7 |
| C3 | Регуляторный риск 152-ФЗ (контактные данные participants = ПДн) | M | H | Любая утечка или жалоба | privacy-by-design (хранить минимум; encrypt at rest через ADR-014; localised storage in RU); политика + отдельное согласие готовы к запуску | PDF p2 «Главные риски» #4 |
| C4 | Deepfake / AI-bot supply (AI «организаторы» с фейковыми тренировками) | M | M | Появление > 5 фейковых организаторов в первый месяц | Gesture-based selfie verification; rate-limit создания событий новыми аккаунтами; ручной review первой опубликованной серии | PDF p2 «Главные риски» #3 |
| C5 | Apple Mail Privacy Protection / iOS shifts (расширение MPP / Link Tracking Protection) | M | M | Apple анонсирует новую privacy-фичу в WWDC | ADR-010 уже использует `acknowledged` (не `opened`) как ground truth; pivot на in-app + SMS для критичных | `ARCHITECTURE.md` Risk #9 |

## Technical risks (10 Risk checks перед stack commit — PDF V1.3 секция 21)

> Заполняется ежедневно в `docs/pilot-day-N.md` (см. template).
> Pass / Fix / Pivot criteria. **Decision gate:** при Pivot хотя бы по одному пункту — pilot failed, переоткрытие выбора стека.

| # | Check | Pass | Fix | Pivot |
|---|---|---|---|---|
| T1 | Скорость Claude Code (фичи/день) | ≥ 3 | 1-2, оптимизация CLAUDE.md | < 1 → backend под вопросом |
| T2 | Качество ORM (N+1 в django-silk) | 0-2 за пилот | 3-5, добавить N+1 detector в pre-commit | > 5 → Django ORM проблематичен |
| T3 | RLS-correctness | 0 violations | 1-2, эксплицитная инструкция в CLAUDE.md | ≥ 3 → pivot на app-level authz |
| T4 | i18n-correctness (ICU MessageFormat) | 0 missing keys | 1-3 missing, лучшая интеграция next-intl | > 3 → переосмыслить ICU |
| T5 | Module boundary discipline | ≤ 10 violations за пилот | 11-25, refactor с явными contracts | > 25 → Django module-структура слабая |
| T6 | OG-generation (Satori standalone в Next.js) | работает с дня 1 | требует custom server | Pivot на Cloudflare Image API |
| T7 | Coolify deploy reliability | 100% успешных | 1-2 фикса конфига | > 50% fails → Selectel direct |
| T8 | Yandex Cloud-специфика | без сюрпризов | 1-2 quirks с workaround | > 2 серьёзных блокера → Selectel |
| T9 | Telegram OIDC adapter (готовый пакет) | нашёлся в pip | custom 100-200 строк | требует > 500 строк → рассмотреть VK ID primary |
| T10 | Procrastinate vs Celery достаточность | работает на 3 use cases | 1 use case требует Redis | требует Celery с дня 1 → +Redis в инфру |

## Triggers пересмотра реестра

- При добавлении нового BC → проверить, не появляются ли новые риски.
- При срабатывании Trigger любого риска → review mitigation + record в `docs/CHANGELOG.md`.
- При завершении Pilot Этап 0 → удалить категорию Technical / 10 Risk checks (либо в архив `docs/archive/`).
- Ежеквартальная ревизия Operational + Compliance categories.
