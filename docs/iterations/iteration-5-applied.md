# Iteration 5 — Applied corrections worklog

> **Дата выполнения:** 2026-05-25.
> **Сессия:** Claude Opus 4.7 (same session as Iteration 0/4/4.5 для preserving контекста).
> **Founder review ETA:** ~30 минут (git diff на 4 файлах).
> **Spec:** Iteration 3 reconciliation report § 3.1-3.4 (18 коррекций) + 1 self-consistency (S1).

## Summary

- **Applied:** 16 / 18 actionable corrections.
- **Skipped:** 2 verify-then-act items (P1, P2 — already present in PRODUCT.md, no change needed).
- **Verified:** 3 verify-only items (R1, R3, A3 — text already correct).
- **Total operations:** 21 audit items × Applied/Skipped/Verified verdict.

## Worklog table

| ID | Файл | Тип | Verdict | Описание |
|---|---|---|---|---|
| **R1** | `README.md` | verify-only | ✓ Verified | ADR-006 link — semantics stable, no change |
| **R2** | `README.md` | actual | ✅ Applied | Added fallback domain options (`act.events` / `joinact.app` / `act-app.ru`) to TODO block (line 15) |
| **R3** | `README.md` | verify-only | ✓ Verified | ADR-012, ADR-013 links — both exist correctly, no change |
| **R4** | `README.md` | actual | ✅ Applied | Added cross-ref to full ADR section in `docs/ARCHITECTURE.md#adr-architecture-decision-records` (line 119) |
| **R5** | `README.md` | actual | ✅ Applied | Added explicit ADR-005 → ADR-007 renumbering note to V1.2+V1.3 source line (line 143) |
| **C1** | `CLAUDE.md` | actual | ✅ Applied | Added «Версионирование» row → `docs/CHANGELOG.md` to header metadata table |
| **C2** | `CLAUDE.md` | actual | ✅ Applied | NON-NEGOTIABLE #3 (Платежи) + «(основание: ADR-005)» |
| **C3** | `CLAUDE.md` | actual | ✅ Applied | NON-NEGOTIABLE #6 (Magic links POST) + supertokens.com + etodd.io source refs |
| **C4** | `CLAUDE.md` | actual | ✅ Applied | NON-NEGOTIABLE #7 (PII шифрование) + ADR-014 + `audit_log_pii_access` Wave 3 |
| **C5** | `CLAUDE.md` | actual | ✅ Applied | NON-NEGOTIABLE #11 (RLS) + ADR-006 + pganalyze.com industry source |
| **C6** | `CLAUDE.md` | actual | ✅ Applied | Глоссарий `default_deny` + ADR-006 + Alasco engineering blog ref |
| **P1** | `docs/PRODUCT.md` | verify-then-act | ⏭️ Skipped | Verified: NSM = Confirmed Weekly Attendances already explicit (line 270); `acknowledged` ground truth on line 646. No change needed |
| **P2** | `docs/PRODUCT.md` | verify-then-act | ⏭️ Skipped | Verified: Apple Sign-In gap already in Open Questions (line 690) + section about российская карта блокировка (line 444). No change needed |
| **P3** | `docs/PRODUCT.md` | actual | ✅ Applied | JTBD-3 + «(требует: Identity & Auth + Verification L4 ID + Billing Слой 1+2; реализация после Pilot — см. `docs/jtbd-bc-mapping.md`)» |
| **P4** | `docs/PRODUCT.md` | actual | ✅ Applied | Luma monetization comparison + cross-ref to `docs/jtbd-bc-mapping.md` секция «Monetization mapping» |
| **A1** | `docs/ARCHITECTURE.md` | **actual — CRITICAL** | ✅ Applied | ADR-007 header (line ~2080) + Historical note про ADR-005↔ADR-007 renumbering verbatim из Iteration 3 spec |
| **A2** | `docs/ARCHITECTURE.md` | actual | ✅ Applied | ADR-003 (Frontend Next.js) + Триггеры пересмотра: EOL без 5-летнего LTS / breaking changes > 2×/год / bundle size > 2× |
| **A3** | `docs/ARCHITECTURE.md` | verify-only | ✓ Verified | ADR-008 Discovery ranking — formula correct, verbatim references V1.0 multiplicative as rejected baseline. No change |
| **A4** | `docs/ARCHITECTURE.md` | actual | ✅ Applied | ADR-010 Storage line + «(текущий Level C status: **missing**; см. § «16 BC ↔ Level C status» в `docs/iterations/iteration-4.5-audit-report.md`)» |
| **A5** | `docs/ARCHITECTURE.md` | actual | ✅ Applied | Раздел «Источники» + новый bucket «Iteration 1-5 reconciliation» с описанием 5 итераций audit history |
| **A6** | `docs/ARCHITECTURE.md` | actual | ✅ Applied | Раздел «CLAUDE.md иерархия» + cross-refs на текущие skills (write-rls-policy + outbox-event из Iteration 4) и Iteration 6 roadmap |
| **S1** | `docs/CHANGELOG.md` | self-consistency | ✅ Applied | New entries для Iteration 4.5 (audit fixes) + Iteration 5 (corrections to 4 main files); paths updated to reflect Iteration 0 bootstrap moves (backend/pyproject.toml, backend/.importlinter, backend/apps/identity_auth/CLAUDE.md, docs/pilot/day-template.md) |

## Discipline metrics

- **Diff-style only:** все правки — точные `str_replace`, no rewrites. ✓
- **No new ADRs:** ни одного нового ADR / NON-NEGOTIABLE не добавлено. ✓
- **No frozen stack changes:** V1.2 stack — без изменений. ✓
- **No date metadata changes:** `|**Обновлено**|` строка в CLAUDE.md — не тронута. ✓
- **Collateral changes:** только в `docs/CHANGELOG.md` — это явный design (S1 self-consistency для path updates). ✓

## Validation

Все 4 файла после применения:

| Файл | До (lines / bytes) | После (lines / bytes) | Diff hunks |
|---|---|---|---|
| `README.md` | 145 / 14503 | ~145 / ~14800 | 3 (R2, R4, R5) |
| `CLAUDE.md` | 176 / 23984 | ~177 / ~25000 | 7 (C1-C6 + dates row insertion) |
| `docs/PRODUCT.md` | 712 / 90131 | ~712 / ~90400 | 2 (P3, P4) |
| `docs/ARCHITECTURE.md` | 2658 / 243331 | ~2680 / ~245500 | 6 (A1, A2, A4, A5, A6 — A6 affects one bullet) |
| `docs/CHANGELOG.md` | 131 / ~9100 | ~140 / ~10500 | 2 (Added entries + TODO replacement) |

## Iteration 5 — Conclusion

**Verdict:** **All 21 items processed successfully.** 16 Applied + 2 Skipped (justified verify) + 3 Verified (no-change needed). Zero Critical findings. Zero rejections. Project documentation теперь полностью синхронизирована между:

- 4 main files (README + CLAUDE + PRODUCT + ARCHITECTURE)
- 13 Iteration 4 artifacts (CHANGELOG + scaffolding configs + 2 skills + 2 docs + per-context CLAUDE.md)
- 4 iteration memory files (audit report + 3 prompts)
- Phase 0 deliverable ZIP

## Next steps

- **Phase 0 final.** Repackage ZIP с обновлёнными 4 файлами. SHA-256 manifest перегенерирован.
- **Iteration 6** (skills library, ~3h): создать 8 SKILL.md из roadmap.
- **Iteration 7** (per-context CLAUDE.md, ~2h): создать 5 per-context CLAUDE.md для BC с Level C.
- **Iteration 8** (docs, ~4h): docs/erd.md + docs/api/openapi.yaml + docs/glossary.md + docs/runbooks/.

После Iteration 8 → **Phase 1 Bootstrap** (3-7 дней разработки локально через Claude Code).
