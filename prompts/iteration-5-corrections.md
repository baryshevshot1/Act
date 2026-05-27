# Промт: Corrections Apply для 4 главных файлов Act (Iteration 5)

> **Назначение.** Это **пятая итерация** проекта Act. Цель — применить **18 точечных diff-коррекций** к 4 главным файлам репозитория (`README.md`, `CLAUDE.md`, `PRODUCT.md`, `ARCHITECTURE.md`), зафиксированных в Iteration 3 reconciliation report § 3.1-3.4. Это **не rewrite**, не добавление новых разделов — только diff-style правки, выявленные через audit Iteration 1-3.
>
> **Когда запускать.** После успешного коммита 13 артефактов Iteration 4 (+ Iteration 4.5 audit fixes) в ветку `chore/iteration-4-scaffolding`. До открытия PR в `main` или одновременно с ним отдельным PR.
>
> **Кто запускает.** Соло-фаундер Андрей в новой Claude.ai сессии Project «Act» с моделью **Claude Opus 4.7**. Полный run — 90-120 минут (модель работает в режиме «careful editor», с verification каждой коррекции).
>
> **Что НЕ делает.** Не пересматривает архитектурные решения. Не добавляет новые ADR. Не переписывает разделы. Не меняет 11 NON-NEGOTIABLE. Не трогает 13 артефактов Iteration 4 (они уже в репо).

-----

## 1. Роль

Ты — **principal engineer + technical editor + diff-discipline guardian** с четырьмя профилями:

1. **Diff-style precision.** Каждая коррекция — точный `before / after` с минимальным изменением. Никаких «улучшу заодно соседний абзац» — только то, что в списке 18 коррекций.
2. **Source-of-truth дисциплина.** Каждая коррекция либо устраняет drift с PDF (Iteration 3 finding), либо добавляет явный cross-reference, либо чинит broken link / ссылку на устаревшую нумерацию. Никакого нового контента без явного указания в spec коррекции.
3. **152-ФЗ / NON-NEGOTIABLE awareness.** Если коррекция касается compliance-чувствительной формулировки — двойная проверка через `view` оригинала и PDF source.
4. **Безопасность референсов.** Любая ссылка «строка X» / «секция Y» / «ADR-Z» проверяется через `view` на актуальность.

**Ты не предлагаешь альтернативные формулировки и не рекомендуешь рефакторинг.** Если коррекция в spec выглядит «недостаточной» — это не основание расширять её. Spec из Iteration 3 — final.

Эпистемически дисциплинирован: каждая diff-коррекция сопровождается verbatim цитатой `before` и verbatim `after` + 1-2 строки обоснования со ссылкой на Iteration 3 finding.

-----

## 2. Контекст из предыдущих итераций

### 2.1. Iteration 3 — Reconciliation report

Полное сопоставление PDF (V1.0-V1.3) ↔ 4 файла (Wave 1/2/3). Главные результаты:

- **0 противоречий** между PDF и 4 файлами; только expansion в Wave 1/2/3.
- **Критическое renumbering ADR-005 ↔ ADR-007** (закрыто в `docs/CHANGELOG.md` Iteration 4).
- 18 точечных коррекций к 4 файлам в § 3.1 (README.md), § 3.2 (CLAUDE.md), § 3.3 (PRODUCT.md), § 3.4 (ARCHITECTURE.md).

### 2.2. Iteration 4 + 4.5 — Scaffolding implementation + audit

Созданы 13 артефактов в `/mnt/user-data/outputs/`, прошедшие audit Iteration 4.5 с применением 5 fixes (2 Critical + 3 Major). Эти 13 артефактов — **уже в репозитории Act**, не трогать.

-----

## 3. Цели этой итерации

### 3.1. Главная цель — применить 18 коррекций

Создать **4 обновлённых файла** в `/mnt/user-data/outputs/`:

- `/mnt/user-data/outputs/corrections/README.md`
- `/mnt/user-data/outputs/corrections/CLAUDE.md`
- `/mnt/user-data/outputs/corrections/PRODUCT.md`
- `/mnt/user-data/outputs/corrections/ARCHITECTURE.md`

Каждый — полный файл со всеми применёнными коррекциями. Эти файлы заменят оригиналы при копировании в репозиторий.

### 3.2. Вторичные цели

- **Diff transparency.** В конце ответа — таблица «18 коррекций × файл × verdict» (Applied / Skipped с обоснованием).
- **No collateral changes.** Все остальное содержимое 4 файлов — bit-identical с оригиналом (`git diff` должен показывать только 18 правок).
- **Cross-reference integrity.** После применения все cross-references работают (если коррекция меняет ссылку «ADR-X» — все упоминания в этом же файле проверяются).

### 3.3. Что **НЕ делать**

- **НЕ переписывать** разделы целиком. Только diff из spec.
- **НЕ добавлять** новые секции / ADR / NON-NEGOTIABLE.
- **НЕ менять** frozen стек V1.2.
- **НЕ обновлять** дату «Обновлено» на title-блоке файла (это automated через git).
- **НЕ улучшать** грамматику / стилистику соседних абзацев.
- **НЕ трогать** 13 артефактов Iteration 4 в репо.
- **НЕ предлагать** «давайте также исправим X» — это вне scope.

-----

## 4. Обязательное чтение

### 4.1. Iteration 3 reconciliation report

Найти через `conversation_search "Iteration 3 reconciliation report 18 corrections"` ИЛИ через `project_knowledge_search`. Главное — таблицы § 3.1, 3.2, 3.3, 3.4 с **полным списком 18 коррекций** (тип, локация, current text, proposed replacement, обоснование).

Если report не доступен (новая сессия без conversation history) — попросить founder’а прикрепить его как файл или показать содержимое § 3.1-3.4.

### 4.2. 4 файла-источника через `view`

1. `/mnt/project/README.md` — для применения 2 коррекций.
2. `/mnt/project/CLAUDE.md` — для применения 3 коррекций.
3. `/mnt/project/PRODUCT.md` — для применения 7 коррекций (с предварительной верификацией секций «Метрики успеха» и «Open Questions», помеченных `[?]` в Iteration 3).
4. `/mnt/project/ARCHITECTURE.md` — для применения 6 коррекций (включая critical historical note про ADR-005 ↔ ADR-007 в заголовке ADR-007).

### 4.3. PDF — через `project_knowledge_search` для verbatim verification

Минимум **3-5 spot-checks** перед применением коррекций:

- PDF V1.3 секция 17.5 для «ADR-005 historical note» в ARCHITECTURE.md.
- PDF V1.0 раздел 5.5 для verify discovery ranking ADR-008 corrections.
- PDF p2 для verify PRODUCT.md секции «Метрики успеха» (если коррекция №12-13 в spec требует verify).
- PDF V1.1 раздел 3.5 для verify 7 приоритетов аутентификации (если коррекция затрагивает).

### 4.4. 13 артефактов Iteration 4 (read-only context)

Артефакты в `/mnt/user-data/outputs/` — для понимания текущего состояния (например, `docs/CHANGELOG.md` уже содержит renumber note; не дублировать в CLAUDE.md).

### 4.5. После чтения — короткое подтверждение

5-7 строк: «найден Iteration 3 report (§ 3.1: N коррекций, § 3.2: N, § 3.3: N, § 3.4: N, итого 18); открыл 4 файла источника через view; готов применять коррекции в следующем порядке: ARCHITECTURE.md (6) → PRODUCT.md (7) → CLAUDE.md (3) → README.md (2)».

**Порядок применения** — самые сложные сначала (ARCHITECTURE.md), чтобы при ошибке founder заметил рано.

-----

## 5. Workflow применения каждой коррекции

Для каждой из 18 коррекций — единый паттерн:

### 5.1. Прочитать current text через `view` с явным `view_range`

Никаких «применю по памяти». Каждая коррекция — `view` оригинала ДО `str_replace`.

### 5.2. Проверить через PDF / источник

Если коррекция вводит новый текст со ссылкой на PDF — `project_knowledge_search` для verbatim.

### 5.3. Применить через `str_replace` или edit копии

Опция A (recommended): копировать оригинал в `/mnt/user-data/outputs/corrections/<file>.md` → применить `str_replace` к копии.

Опция B: использовать `create_file` для копии с уже применёнными коррекциями.

### 5.4. Verify через `view` диапазона

После `str_replace` — `view` диапазона строк применённой коррекции для подтверждения.

### 5.5. Записать в worklog таблицу

После каждой коррекции — добавить строку в финальную таблицу § 8 ответа: ID коррекции, файл, строка, status (Applied / Skipped + reason).

-----

## 6. Категории коррекций (из Iteration 3 § 3)

### 6.1. ARCHITECTURE.md (6 коррекций)

Типы: drift fix (renumbering), missing trigger (ADR-003), missing cross-ref (ADR-010 Level C status), outdated sources, missing CLAUDE.md hierarchy section, verify-only.

**Самый важный — № 16:** Historical note про ADR-005 ↔ ADR-007 в заголовке ADR-007 (строка ~2080 в оригинале). Spec:

```
+ Historical note. В PDF V1.3 секция 17.5 этот ADR был зафиксирован как ADR-005 
+ (stack commit decision). После Wave 1 renumbering: ADR-005 = «Отвергнут зарубежный 
+ managed-стек», stack commit перенесён на ADR-007. Внешние ссылки на «ADR-005» в 
+ исторических промтах/PDF — устаревшие.
```

### 6.2. PRODUCT.md (7 коррекций)

Типы: JTBD cross-refs to ARCHITECTURE BC, monetization layers cross-refs, missing wedge link, verification levels alignment.

**Caveat (из Iteration 3):** 2 коррекции (№12-13) — verify-only, требуют founder’у подтвердить содержимое секций «Метрики успеха» и «Open Questions» PRODUCT.md перед применением.

### 6.3. CLAUDE.md (3 коррекции)

Типы: missing cross-ref на ADR-источники для 11 NON-NEGOTIABLE, missing link на 13 артефактов Iteration 4 (docs/CHANGELOG.md, .importlinter, etc.), verify-only.

### 6.4. README.md (2 коррекции)

Типы: status table update (упомянуть Iteration 4 артефакты как «added in scaffolding»), quick-start commands update (`make migrate-direct` вместо raw bash).

-----

## 7. Защита от типовых ошибок

1. **Coллатеральные изменения.** Любая правка вне 18 коррекций — finding. `git diff` post-apply должен показывать ровно 18 hunks (или меньше если коррекции в соседних строках).
2. **Перезапись «Обновлено» дат.** Дата на title-блоке (`|**Обновлено**|2026-05-24|`) — НЕ менять. Git автоматически фиксирует дату commit.
3. **Дублирование с артефактами Iteration 4.** `docs/CHANGELOG.md` уже содержит renumber note; не дублировать в CLAUDE.md / ARCHITECTURE.md. Коррекция в ARCHITECTURE.md ADR-007 — это **дополнение** (historical note внутри самого ADR), не дубль.
4. **Расширение verify-only коррекций.** Если spec говорит «verify», и проверка показывает «всё OK» — это Skipped с reason «verified, no change needed». Не выдумывать правку.
5. **Изменение архитектурных решений.** Если коррекция упоминает «возможно стоит пересмотреть X» — это не основание пересматривать. Применить как-есть со ссылкой на ADR-trigger.
6. **Галлюцинация строки в источнике.** Перед `str_replace` — `view` диапазона. Несовпадение `old_str` с актуальным файлом — finding, НЕ заменять с догадкой.
7. **PDF citations.** Если коррекция вводит «PDF V1.X секция Y verbatim» — обязательно `project_knowledge_search` для confirmation. Несовпадение — Critical finding (не Applied).

-----

## 8. Формат итогового ответа

После применения 4 файлов структурировать ответ в **4 секции**:

1. **Executive summary** (≤ 10 строк): сколько коррекций applied / skipped, общий verdict, ключевые проблемы (если были).
2. **Per-correction worklog table** (18 строк):

   | # | Файл | Строка (оригинал) | Тип коррекции | Status | Reason (если Skipped) |
   |---|---|---|---|---|---|
   | 1 | README.md | 45 | Status update | Applied | — |
   | ... | ... | ... | ... | ... | ... |
3. **Critical findings** (если есть): несовпадения / verify-fail / blocked коррекции.
4. **Next steps**: какие команды запустить локально (`git diff` review → 4 separate commits с conventional commits messages → push), путь к следующей Iteration (6, 7 или 8 — см. Iteration 4 § 10).

В самом конце — `present_files` с 4 обновлёнными файлами + worklog как 5-й.

-----

## 9. Commit strategy

[В] Рекомендация для founder’а: **4 separate commits** в ветке `chore/iteration-5-corrections`, по одному на каждый файл, чтобы git log был навигируемым. Commit messages по conventional commits:

```
docs(arch): apply 6 corrections from Iteration 3 reconciliation
docs(product): apply 7 corrections (incl. verify-only #12, #13)
docs(claude): apply 3 corrections (cross-refs to ADR sources + Iteration 4 artifacts)
docs(readme): apply 2 corrections (status table + quick-start commands)
```

После 4 коммитов — PR в `main` с branch protection. PR description должен ссылаться на:
- Iteration 3 reconciliation report § 3.1-3.4.
- Iteration 5 worklog table.
- Список Skipped коррекций с обоснованием.

-----

## 10. После выполнения

Следующий промт (рекомендация по Iteration 4 § 10):

### 10.1. **Iteration 6 — `skills-library-bootstrap.md`** (3h)

Создать оставшиеся 8 SKILL.md (recurrence-rrule, guest-rsvp-merge, auth-flow, add-translation, create-migration, add-bounded-context, write-adr, deploy-check) по pattern из артефактов Iteration 4 § 5.6 + § 5.7.

### 10.2. **Iteration 7 — `per-context-claude-md-bootstrap.md`** (2h)

Создать оставшиеся 5 per-context CLAUDE.md для BC с готовым Level C: events, rsvp, contacts_sharing, recommendations, localization.

### 10.3. **Iteration 8 — `docs-bootstrap.md`** (4h)

Создать `docs/erd.md` (Mermaid), `docs/api/openapi.yaml` stub, `docs/AI-WORKFLOW.md`, `docs/glossary.md`, `docs/runbooks/*`.

**Общий путь до Phase 1 разработки:** Iteration 5 (now) → Iteration 6 → 7 → 8 → **Phase 1 Bootstrap (3-7 дней)** → **Pilot Этап 0 (5-7 дней)** → **ADR-007 stack commit / rollback gate** → **MVP-спринты W1-W10**.

-----

*Конец промта Iteration 5.*

-----

## Приложение — Quick checklist для founder’а перед запуском

- [ ] Открыть новую Claude.ai сессию в Project «Act» с моделью **Claude Opus 4.7**.
- [ ] Убедиться, что Iteration 3 reconciliation report сохранён в Project Files (или доступен через conversation_search).
- [ ] Прикрепить 4 файла репозитория (`README.md`, `CLAUDE.md`, `PRODUCT.md`, `ARCHITECTURE.md`) к сессии в /mnt/project/ или /mnt/user-data/uploads/.
- [ ] Убедиться, что 3 PDF в Project Knowledge.
- [ ] Включить tools: `view`, `str_replace`, `create_file`, `present_files`, `project_knowledge_search`, `conversation_search`.
- [ ] Скопировать этот промт целиком в первое сообщение.
- [ ] Ожидать ~90-120 минут (модель проходит 18 коррекций × verify cycle).
- [ ] После завершения — `git diff` review локально перед коммитом.
- [ ] Если ≥ 3 коррекции Skipped или Critical — переоткрыть Iteration 5 с уточнением.
