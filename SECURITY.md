# Security Policy — Act

> Responsible disclosure + security posture overview для проекта Act.
> Maintained by founder (DPO). Last updated: 2026-05-27.

## Reporting a Vulnerability

**Email:** `security@act.app` *(placeholder — заменить на final домен после Phase 0.5 регистрации)*

При reporting укажите:
1. **Описание** — что нашли, как воспроизвести.
2. **Impact** — какие данные / users / системы под угрозой.
3. **Severity estimate** (your view): Critical / High / Medium / Low.
4. **PoC** (proof-of-concept) — minimal reproduction steps.
5. **Suggested fix** (опционально).

**Encrypted reports:** PGP key — TBD после Phase 1.

### Response timeline

| Severity | Acknowledge | Initial assessment | Fix target |
|---|---|---|---|
| Critical (data breach / auth bypass / RCE) | < 24 hours | < 48 hours | < 7 days |
| High (privilege escalation / sensitive data exposure) | < 48 hours | < 5 days | < 30 days |
| Medium (XSS, CSRF, misconfiguration) | < 5 days | < 14 days | < 90 days |
| Low (information disclosure без impact) | < 14 days | Best-effort | Next release cycle |

**Founder is solo** — response times reflect realistic capacity. P0 incidents (data breach) take priority over feature work.

## Scope

### In scope

- Web app: `act.app` (production, после Phase 0.5) + `staging.act.app`.
- API: всё под `/api/v1/*` (см. `docs/api/openapi.yaml`).
- Authentication flows: Telegram OIDC, magic-link, OAuth, phone OTP.
- RLS policies: tenant isolation, cross-tenant leaks.
- PII handling: encrypted at rest, audit log, secure transmission.
- Telegram Bot interactions (если активны, после Phase 5+).

### Out of scope

- **Third-party services:** Yandex Cloud platform vulns (report to Yandex), Telegram platform vulns (report to Telegram).
- **Social engineering attacks** на founder personally или users.
- **Physical security** Yandex Cloud DCs.
- **DDoS** (handle через Yandex CDN + Coolify rate limiting).
- **Spam** в публичных endpoints (handle через application-level rate limiting).
- **Recently-disclosed CVEs** в dependencies (< 7 дней до first patch release) — патчим в порядке release cycle.

## Severity Definitions

| Level | Examples |
|---|---|
| **Critical** | Authentication bypass; SQL injection; mass PII exposure; RCE; cross-tenant RLS leak; secrets exposed in repo |
| **High** | Privilege escalation; single-user PII leak; cookie hijacking; CSRF на sensitive actions; auth flow exploitation |
| **Medium** | Stored XSS limited scope; Open redirect; broken access control affecting non-PII |
| **Low** | Reflected XSS requiring user interaction; information disclosure (e.g. version banner); rate limit bypass |

## Security Posture

### Compliance frameworks

- **152-ФЗ** (Russian Data Protection Act) — primary regulatory framework.
  - ст. 18: первичная обработка ПДн в РФ (Yandex Cloud RU region).
  - ст. 9 ред. 156-ФЗ от 24.06.2025: отдельный документ согласия (НЕ вложенный чекбокс).
  - ст. 12: ТППД (cross-border) — отдельное opt-in для Telegram (ОАЭ).
  - ст. 22: регистрация оператора ПДн в РКН (БЛОКЕР для production).
- **OWASP Top 10:2025** — mapping в `docs/ARCHITECTURE.md` § OWASP.
- **WCAG 2.2 AA** — accessibility baseline.

### Security controls (implemented or planned)

| Control | Status | Reference |
|---|---|---|
| TLS 1.3 only (HSTS preload) | Phase 1.8 (Coolify) | A02 OWASP |
| Argon2id password hashing | Django 5.2 default | A07 |
| Session: HttpOnly, Secure, SameSite=Strict | Phase 1.4 | A07 |
| CSP без `unsafe-inline` для scripts | Phase 1.4 | A05 |
| Row-Level Security (FORCE + RESTRICTIVE `default_deny`) | All user-attributed tables | A01 — RLS Operational Constraints |
| Field-level PII encryption (django-cryptography + Yandex Lockbox) | Phase 1.4+ | A02 — ADR-014 |
| Audit log PII access (`audit_log_pii_access`) | Wave 3 (planned) | A09 — 152-ФЗ ст. 7 |
| Magic link POST-only (not GET) | Phase 1.4 | NN #6 — supertokens.com pattern |
| Rate limiting (3/15min/IP, 10/h/email) | Phase 1.4 | A07 |
| HMAC token comparison (constant-time) | Phase 1.4 | A07 — timing attack prevention |
| import-linter (architectural boundaries) | Pre-Phase 1 ✓ | A04 — secure design |
| `act_admin` BYPASSRLS только для admin + ОБЯЗАТЕЛЬНЫЙ audit log | Phase 1.4 | A01 + 152-ФЗ |
| Secrets scanning (gitleaks) в CI | Phase 1.2 | A05 — secret management |
| Sentry self-hosted (не SaaS) | Phase 1 | 152-ФЗ ст. 18 |
| LGTM stack для observability self-hosted | Phase 1 | 152-ФЗ ст. 18 |
| Cookie consent UI (3 levels) | Wave 3 / Phase 1.5 | 152-ФЗ ст. 9 |
| Privacy Policy на `/privacy` | Pre-Phase 0.3 | 152-ФЗ ст. 18.1 |
| Отдельный документ согласия | Pre-Phase 0.4 | NN #2 — 152-ФЗ ст. 9 |
| OWASP dependency scanning | Phase 1.6 (GHA) | A06 |
| Cross-context isolation (Outbox, not Django signals) | ADR-016 | A04 — secure architecture |

### Known limitations

- **Apple Sign-In** не доступен (требует foreign юр.лицо для Apple Developer Program) — deferred до Phase 6+.
- **Google Sign-In** — Google Cloud Billing не принимает РФ-карты — deferred.
- **PWA / Telegram Mini App only** до Phase 6+ — no native iOS App Store distribution.
- **Real-time features** deferred — на MVP только polling 30s (NN #8).
- **ML personalization** deferred до >10K MAU.

## Disclosure Policy

**Coordinated disclosure preferred:**
1. Report → acknowledge → triage → fix → release → public disclosure.
2. **Embargo period:** до release fix (max 90 days для High/Critical).
3. **Public disclosure:** post-fix через `docs/security/advisories/YYYY-NN-short-name.md` с timeline.

**Vendor disclosure** (если vuln в third-party dep): coordinate with upstream maintainer первым; следовать их disclosure policy.

## Hall of Fame

Security researchers, который ответственно reported vulnerabilities:

| Date | Reporter | Severity | Summary |
|---|---|---|---|
| — | — | — | None yet — Act is pre-launch |

Reporters получают:
- Public acknowledgment в этом разделе (если согласны).
- Reference letter для security CV (founder подпишет).
- **No monetary bounty** на MVP (соло-фаундер ИП — нет budget). Reconsider после Series A / monetization Слой 2+.

## Out-of-bounds (NOT acceptable)

- Testing on production users без their consent.
- DDoS / volumetric attacks для «testing».
- Phishing / social engineering founder или users.
- Publishing vulns ДО embargo period expires.
- Data exfiltration (даже для PoC) — use minimal sample.

Violation любого = report игнорируется + потенциальные legal consequences.

## Resources

- **152-ФЗ checklist** → `docs/ARCHITECTURE.md` § Compliance Baseline (ADR-012).
- **OWASP mapping** → `docs/ARCHITECTURE.md` § OWASP Top 10:2025.
- **Risk register** → `docs/risk-register.md`.
- **ADR-014** (PII encryption) → `docs/ARCHITECTURE.md` § ADR-014.
- **Deploy checklist** (compliance + technical gates) → `.claude/skills/deploy-check/SKILL.md`.
- **Per-context security notes** → `backend/apps/<ctx>/CLAUDE.md` § Common pitfalls.

## Update history

| Date | Change |
|---|---|
| 2026-05-27 | Initial SECURITY.md (Iteration 8 docs bootstrap) |
