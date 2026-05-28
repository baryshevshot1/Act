# Transactional Outbox (ADR-016) — единственный канал cross-context коммуникации.
# Mutation основной таблицы + запись в outbox_event в одной транзакции.
# Procrastinate worker poll-ит и доставляет subscribers (≤5s, at-least-once).
