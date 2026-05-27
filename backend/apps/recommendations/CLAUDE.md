# apps/recommendations — Recommendations Context (Stable API for ML migration)

> Per-context `CLAUDE.md`. Загружается Claude Code on-demand при работе с этим BC.
> ROOT-context: `../../../CLAUDE.md`. Domain knowledge: `../../../docs/ARCHITECTURE.md` (Level C Recommendations).
> Источники: `ARCHITECTURE.md` § Recommendations + ADR-008 (Discovery ranking) + Failed approaches (multiplicative ranking).

## Context

Recommendations — **MVP stub-модуль**. Возвращает отсортированные Events для пользователя через делегирование в Discovery с весом, смещённым в reputation. **На MVP НЕ содержит ML, НЕ строит профилей предпочтений, НЕ имеет embeddings**. Главный design goal — **stable API contract**, который переживает ML-миграцию без breaking changes для callers. ML deferred до >10K MAU [F: `CLAUDE.md` § «Что Claude НЕ должен делать»: не предлагать ML до 10K MAU].

## Entities (verbatim из `docs/ARCHITECTURE.md` § Recommendations)

| Entity | Description | RLS? | When used |
|---|---|---|---|
| `RecommendationsScoreCache` | Опциональный pre-computed scores per (user, event) | ✓ | Может быть пустым на MVP — `recommend_for_user` считает on-the-fly через discovery |

```sql
CREATE TABLE recommendations_score_cache (
    id UUID PRIMARY KEY DEFAULT uuidv7(),
    user_id UUID NOT NULL REFERENCES identity_auth_user(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES events_event(id) ON DELETE CASCADE,
    score NUMERIC(10, 6) NOT NULL,  -- нормализованный [0, 1]
    algorithm_version VARCHAR(32) NOT NULL DEFAULT 'mvp_reputation_sort_v1',
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE (user_id, event_id, algorithm_version)
);
```

## Stable API contract (verbatim — НЕ менять signatures)

```python
# apps/recommendations/contracts.py — public API
def recommend_for_user(
    *,
    user_id: UUID,
    city_id: UUID | None = None,
    limit: int = 20,
    use_cache: bool = True,
) -> list[EventDTO]:
    """MVP-stub: top-N events from Discovery sorted by reputation_score + city filter.
    Post-ML: replace implementation WITHOUT changing this signature.

    Контракт:
    - Возвращает EventDTO (public DTO, не internal model) — никакого ML-leakage.
    - Идемпотентен в read-only режиме (use_cache=True): тот же user_id + city_id
      + limit → тот же result в пределах cache_ttl (1 час).
    - Безопасен по RLS — фильтрует только публичные events видимые user_id.
    """

def recommend_for_anonymous(*, city_id: UUID, limit: int = 20) -> list[EventDTO]:
    """Для гостей без user_id — pure recency × city-fit через cold_start_weights ADR-008.
    Никакой персонализации, никакого fingerprint-tracking."""

def invalidate_user_recommendations(*, user_id: UUID) -> int:
    """Удаляет cache для user_id. Вызывается из subscribers на RatingPosted,
    UserPreferencesUpdated, etc. Возвращает число удалённых строк."""
```

## Conventions

- **NEVER ML on MVP** [F: `CLAUDE.md` строка 155] — replace-implementation подход; ML deferred до >10K MAU.
- **No `RecommendationDTO`** на MVP — переиспользуем `EventDTO` из `apps.events.contracts`. Pre-mature wrapping = техдолг без выгоды.
- **Migration path** — смена `services.py` от stub-реализации к ML — это replace-implementation, не replace-interface. EventDTO в contracts остаётся неизменным; ranking algorithm меняется внутри.
- **Internal ML detail** — все ML-параметры (`algorithm_version`, `embedding_vector`, `feature_weights`) остаются в `apps/recommendations/internal/`. **НЕ просачиваются в `contracts.py`**.
- **Delegation to Discovery** — `recommend_for_user` → `apps.discovery.contracts.score_events_for_user(user_id, weights=mature_weights, filters)`. На MVP — Recommendations почти прозрачный wrapper над Discovery.
- **RLS обязательна** на `recommendations_score_cache` даже на MVP — раскрытие подобранных рекомендаций другому пользователю = leak профиля интересов.
- **Use multiplicative ranking — ОТВЕРГНУТ** [F: `docs/CHANGELOG.md` Failed approaches + ADR-008]. На MVP — weighted sum через `mature_weights`. `(rep × act × rec × prox)` обнуляет новое событие → ломает cold-start.

## Cross-context dependencies

- **Exposes (через `contracts.py`):** `recommend_for_user`, `recommend_for_anonymous`, `invalidate_user_recommendations` — три функции, никаких DTOs (использует `EventDTO`).
- **Consumes:** `apps.events.contracts` (`EventDTO`), `apps.discovery.contracts` (`score_events_for_user` — core delegation на MVP), `apps.identity_auth.contracts` (`UserContract` для user_id validation).
- **Emits via Outbox:** **ничего на MVP** — нет downstream consumers рекомендательных событий.
- **Subscribes:** `RatingPosted(ratee_user_id)` → `invalidate_user_recommendations` (на MVP — просто truncate cache для simplicity); `EventCancelled(event_id)` → удалить cache rows для этого event_id; `UserPreferencesUpdated(user_id)` → invalidate (future-proof, событие пока не публикуется).

## Common pitfalls

- **НЕ добавлять `algorithm_version` / `embedding_vector`** в публичную сигнатуру `contracts.py` — это leakage internal деталей; ломает migration safety.
- **НЕ внедрять ML на MVP** — отвергнуто на уровне CLAUDE.md root. До 10K MAU — простая weighted sort.
- **НЕ использовать multiplicative ranking** `(rep × act × rec × prox)` — отвергнуто ADR-008 (cold-start failure).
- **НЕ забывать RLS** на `recommendations_score_cache` — leak профиля интересов = privacy violation.
- **НЕ возвращать internal models** из contracts — только `EventDTO`.
- **НЕ полагаться на cache hit** — MVP может вообще не писать в cache; service должен работать с пустой таблицей.
- **НЕ писать в cache при `use_cache=False`** — это read-only flow для preview / testing.
- **НЕ публиковать события** на MVP — нет downstream subscribers; добавится при ML.
- **НЕ забывать про anonymous** — `recommend_for_anonymous` НЕ читает из `score_cache` (нет user_id); pure compute через discovery cold_start_weights.

## Migration triggers (ML readiness)

[F: ADR-008 + `docs/risk-register.md` Operational]:
- `>10K MAU` достигнут → стартует evaluation ML (collaborative filtering / matrix factorization / LLM embeddings).
- `p95 discovery feed > 500ms` → indicator чтобы перейти на pre-computed scores в cache.
- `>30% Postgres CPU на recommendations queries` → cache priming через Procrastinate periodic-task.

## Skills relevant to this BC

- `write-rls-policy` — RLS на `recommendations_score_cache`.
- `outbox-event` — subscribers на RatingPosted / EventCancelled (только subscribe, не emit).
- `create-migration` — schema changes (add columns при появлении ML scores / reasoning).
- `write-adr` — при переходе к ML (новый ADR для algorithm choice).

## When implementing ML (future post-Pilot)

Шаги (для будущего):
1. `apps/recommendations/internal/ml/` модуль для embeddings + inference.
2. `services.py` `recommend_for_user` сначала проверяет cache, при miss → ML inference + write to cache.
3. `algorithm_version` инкрементируется (`mvp_reputation_sort_v1` → `cf_v2`).
4. Background Procrastinate task для cache priming (pre-compute топ-N для активных users).
5. A/B test через PostHog feature flag (`source=ml_v2` vs `source=mvp_v1`).
6. Новый ADR (skill `write-adr`).
