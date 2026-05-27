# Iteration 7 — Applied Per-Context CLAUDE.md Bootstrap

> **Дата:** 2026-05-27.
> **Сессия:** Claude Code (Opus 4.7) — execute напрямую (продолжение Iteration 6 в той же сессии per founder authorization).
> **Spec:** `docs/iterations/iteration-5.5-roadmap.md` § 3 step #2 — «5 per-context CLAUDE.md по образцу identity_auth».
> **Output:** 5 new `backend/apps/<ctx>/CLAUDE.md` → итого 6/6 для всех BC с готовым Level C.
> **Founder review ETA:** ~20 минут (`git diff` на 5 файлах + meta).

## Summary

- **Created:** 5/5 new per-context CLAUDE.md.
- **Total per-context CLAUDE.md:** 6/6 для BC с готовым Level C (identity_auth + events + rsvp + contacts_sharing + recommendations + localization).
- **Total lines:** 558 across 6 файлов; range 58-114; все под Anthropic ≤200 lines рекомендацию.
- **Pattern source:** `backend/apps/identity_auth/CLAUDE.md` (existing, 58 строк).

## Worklog table

| ID | File | Lines | BC | Key conventions enforced |
|---|---|---|---|---|
| C1 | `backend/apps/events/CLAUDE.md` | 73 | Events (+ Recurrence Engine) | RFC 5545 verbatim · generation horizon 21 days · UUIDv7 PKs · owner-only writes · status FSM · `recurrence_id` vs `id` |
| C2 | `backend/apps/rsvp/CLAUDE.md` | 95 | RSVP & Attendance | per-instance RSVP (НЕ auto-confirm series) · merge AFTER verify (NN #6) · phone normalize → HMAC · capacity gate ДО create · waitlist promotion atomic |
| C3 | `backend/apps/contacts_sharing/CLAUDE.md` | 114 | Contacts Sharing | bilateral consent invariant в RLS · time-gating в service-layer · django-cryptography (ADR-014, НЕ pgcrypto) · consent_record_id reference (NN #2) · channel masking в API |
| C4 | `backend/apps/recommendations/CLAUDE.md` | 111 | Recommendations | stable API contract (выживает ML migration) · NO ML on MVP (>10K MAU trigger) · weighted sum (НЕ multiplicative — ADR-008) · RLS обязательна несмотря на пустой cache |
| C5 | `backend/apps/localization/CLAUDE.md` | 107 | Localization / i18n | three strategies (messages/JSONB/translation table) · Russian four plurals (CLDR) · expression index ≠ GIN · `setRequestLocale` mandatory · no next-intl в Python |

## DoD checklist per CLAUDE.md (по identity_auth/CLAUDE.md pattern)

| DoD criterion | Result |
|---|---|
| D1: Header с cross-ref на ROOT CLAUDE.md + Level C path + sources | ✓ 5/5 |
| D2: «Context» section (1 параграф — назначение BC + scope MVP) | ✓ 5/5 |
| D3: «Entities» table (verbatim из Level C, с RLS? column + encrypted? where relevant) | ✓ 5/5 |
| D4: «Conventions» bulleted list (5-10 пунктов) с NN / ADR references | ✓ 5/5 |
| D5: «Cross-context dependencies» (Exposes / Consumes / Emits / Subscribes) | ✓ 5/5 |
| D6: «Common pitfalls» — минимум 7 «НЕ ...» пунктов | ✓ 5/5 (8-12 каждый) |
| D7: «Skills relevant to this BC» с cross-refs на `.claude/skills/` | ✓ 5/5 |
| D8: ≤ 200 строк (Anthropic recommendation) | ✓ 5/5 (range 73-114) |
| D9: Verbatim code/schema examples из Level C (RLS policies, signatures) | ✓ 5/5 |
| D10: Source-grounded `[F: ...]` где не из ARCHITECTURE.md | ✓ 5/5 (CLDR, RFC 5545, ADR refs) |

## Cross-references созданные

Каждый CLAUDE.md ссылается на:

- **ROOT** `../../../CLAUDE.md` (project-wide context).
- **Level C** в `../../../docs/ARCHITECTURE.md` (полная schema + service signatures).
- **Iteration 6 skills** для конкретных операций:
  - `events/CLAUDE.md` → `recurrence-rrule`, `outbox-event`, `write-rls-policy`, `create-migration`, `add-translation`
  - `rsvp/CLAUDE.md` → `guest-rsvp-merge`, `outbox-event`, `write-rls-policy`, `create-migration`, `auth-flow`
  - `contacts_sharing/CLAUDE.md` → `write-rls-policy`, `outbox-event`, `create-migration`, `guest-rsvp-merge` (HMAC lookup)
  - `recommendations/CLAUDE.md` → `write-rls-policy`, `outbox-event`, `create-migration`, `write-adr`
  - `localization/CLAUDE.md` → `add-translation`, `outbox-event`, `create-migration`

- **Other CLAUDE.md** (intra-domain refs):
  - `events/` ↔ `rsvp/` (capacity, EventCompleted → Ratings windows)
  - `rsvp/` ↔ `contacts_sharing/` (bilateral channel resolve post check-in)
  - `recommendations/` → `discovery` (delegation; Discovery Level C not yet drafted — Iteration 9 territory)

## Discipline metrics

- **No frozen-stack changes:** V1.2 stack untouched.
- **No new ADRs:** только references на 16 existing ADR.
- **No code generation:** только AI-instruction CLAUDE.md (для будущих сессий).
- **No PII или secrets:** все examples используют placeholders.
- **Anthropic ≤ 200 lines guideline:** max = 114 (contacts_sharing), avg = 100.
- **Consistent voice:** все 5 файлов следуют identity_auth pattern (Context · Entities · Conventions · Cross-context · Pitfalls · Skills).
- **CHANGELOG updated:** ✓ § Added (Iteration 7) per CLAUDE.md.
- **prompts/README updated:** ✓ Iteration 7 → ✅; Iteration 8 → следующий ⏳.

## Open notes / known limitations

1. **`recurrence_engine/` отдельная директория** (исторический artifact из Iteration 4) — Level C для Recurrence в Events context, не отдельный BC. `recurrence_engine/CLAUDE.md` НЕ создаём (BC stub останется без CLAUDE.md до решения о merge в Events или отдельный Level C).
2. **`discovery/`** не имеет CLAUDE.md — Level C НЕ готов (10 missing per `docs/CHANGELOG.md` TODO). Iteration 9 (post-Pilot) добавит.
3. **`groups/CLAUDE.md`** не создан — Level C missing (ADR-009 только publishing rules). Iteration 9.
4. **`notifications/CLAUDE.md`** не создан — Level C missing (только FSM ADR-010). Iteration 9.
5. **`verification/`, `moderation/`, `analytics/`, `admin_console/`, `user_profile/`, `ratings/`** — все Level C missing. Iteration 9 (post-Pilot).

## Validation

```bash
$ find backend/apps -name "CLAUDE.md"
# 6 файлов — identity_auth + 5 new
$ wc -l backend/apps/*/CLAUDE.md
#  58 identity_auth (existing)
#  73 events (new)
#  95 rsvp (new)
# 107 localization (new)
# 111 recommendations (new)
# 114 contacts_sharing (new)
# 558 total
```

## Iteration 7 — Conclusion

**Verdict:** **5/5 CLAUDE.md successfully created.** Zero rejections, zero critical findings. Per-context AI hierarchy теперь покрывает все 6 BC с готовым Level C. При работе с любым из этих 6 BC Claude Code load-нёт root + per-context CLAUDE.md + relevant skills — три уровня context отделения.

## Next steps

- **Iteration 8** (docs bootstrap, ~4h): `docs/erd.md` (Mermaid 16 BC) + `docs/api/openapi.yaml` (stub paths /auth /events /rsvp) + `docs/glossary.md` (30+ терминов) + `docs/runbooks/{deploy,rollback,db-restore}.md` + `docs/AI-WORKFLOW.md` + `SECURITY.md` root.

После Iteration 8 → **Phase 1 Bootstrap** (3-7 дней) → **Pilot Этап 0** (5-7 дней) → **ADR-007 decision gate**.

Параллельно (founder-bound, не AI-task):
- ⚙ Pre-Phase 0.1 + 0.2 РКН-уведомления (до 30 дней проверки).
- ⚙ D3 domain whois check + регистрация.
- ⚙ D1 ИП в работе.
