# Decision memo: replacement для `django-cryptography-django5`

> **Статус:** Proposal awaiting founder decision. НЕ commit-нутое решение — итоговый ADR-014 update появится после выбора пути.
> **Дата:** 2026-05-28.
> **Источник проблемы:** [`docs/research/phase-1-prep-findings-2026-05-28.md`](./phase-1-prep-findings-2026-05-28.md) § R6.
> **Текущий ADR:** [ADR-014 — Field-level encryption for PII](../ARCHITECTURE.md#adr-014--field-level-encryption-for-pii) (Accepted 2026-05-24).
> **Связь с NN:** NON-NEGOTIABLE #7 (PII encrypted at rest), NN #11 (RLS-таблицы).

-----

## 1. Проблема

Текущая зависимость `django-cryptography-django5>=2.0` (в `backend/pyproject.toml`):

- **Last release:** v2.2 — **2024-06-04**. Прошло ~2 года.
- **Classifiers:** `Django :: 5.0` (НЕ 5.1, НЕ 5.2). Python 3.8-3.12.
- **Repo activity:** мёртв; maintainer не реагирует на issues.
- **Зачем форк:** оригинальный `django-cryptography` от Brad Pitcher застрял на Django 4.x; `-django5` был форк для совместимости с Django 5.0. С тех пор Django 5.1 / 5.2 LTS вышли — форк не обновили.

**Риск для Act:**

- Django 5.2 LTS (наш стек) **не** в supported-list. Может работать или сломаться на model meta API changes.
- При следующем bump Django (5.2 → 6.0 LTS в 2028+) — гарантированно сломается без активного maintainer.
- Security CVE в `cryptography` (transitive) — без maintainer фиксы не прилетят.

**Окно для замены:**

- В коде сейчас **4 placeholder TextField** в `apps/identity_auth/models.py` (User.primary_email, User.phone_e164, OAuthIdentity.provider_uid) и `apps/rsvp/models.py` (GuestRSVP.contact_value).
- **Шифрование ещё не подключено** — это W1 scope (Phase 1.4 написала только `TextField` placeholder).
- Persisted data = 0 (миграции ещё не запущены).
- **Стоимость замены сейчас = только code/ADR change.** После W1 + production data — потребуется backfill task.

-----

## 2. Кандидаты

| # | Подход | LOC custom | Maintenance | Security model |
|---|---|---|---|---|
| **A** | `cryptography` (PyCA) + custom `EncryptedField` | ~50 | PyCA maintains `cryptography` (≥ 2 maintainers, monthly releases) | Fernet (AES-128-CBC + HMAC-SHA256) ИЛИ AES-256-GCM на выбор |
| **B** | `django-encrypted-model-fields` | 0 (drop-in) | Active fork (verify по PyPI dates) | Fernet only |
| **C** | Stay with `django-cryptography-django5`, pin tight + flag risk | 0 | Stale, риск растёт | Fernet |
| **D** | Yandex Lockbox direct API (KMS-only, no local DEK) | ~30 | Yandex maintains; vendor lock-in tighter | Encrypt/decrypt каждый раз через API call |
| **E** | Envelope encryption (DEK + KEK) самостоятельно | ~100 | Custom impl, стандартный паттерн | DEK в app, KEK в Lockbox; данные с encrypted DEK alongside |

-----

## 3. Анализ кандидатов

### A. `cryptography` (PyCA) + custom `EncryptedField` — **RECOMMENDED**

**Описание:** ~50 LOC custom Django field в `apps/core/crypto/fields.py`. Использует `cryptography.fernet.Fernet` (или `AESGCM`). Master key поступает из Yandex Lockbox через startup-hook в `apps/core/crypto/keys.py`.

**Reference impl (примерно):**

```python
# apps/core/crypto/fields.py
from cryptography.fernet import Fernet
from django.conf import settings
from django.db import models

class EncryptedField(models.TextField):
    description = "Transparent Fernet encryption"

    def _get_fernet(self) -> Fernet:
        return Fernet(settings.PII_ENCRYPTION_KEY)

    def get_db_prep_save(self, value, connection):
        if value is None:
            return None
        return self._get_fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        return self._get_fernet().decrypt(value.encode()).decode()

    def to_python(self, value):
        if value is None or value == "":
            return value
        # Heuristic: encrypted blobs are base64; plain text decode fails fast
        try:
            return self._get_fernet().decrypt(value.encode()).decode()
        except Exception:
            return value
```

**Pros:**
- `cryptography` PyCA — gold standard Python crypto. Активно поддерживается (релизы каждый месяц).
- Не зависит от стороннего maintainer'а одного человека.
- Django-version-agnostic: будет работать на 5.2, 6.0, 6.2 LTS.
- Полный контроль над key rotation, AEAD выбором (Fernet vs AES-GCM), keyring management.
- Поддерживает все usage patterns из ADR-014 (encrypted field + HMAC lookup).

**Cons:**
- ~50 LOC код в `apps/core/crypto/` — нужно maintain (но это standard pattern, не uniquely complex).
- Нужно написать `MultiFernet`-style keyring для ротации ключей (~20 дополнительных LOC).

**Maintenance burden:** низкий — Fernet API стабилен с 2012; PyCA не меняет.

**Security:** equivalent с django-cryptography-django5 (тот же Fernet под капотом).

---

### B. `django-encrypted-model-fields` (или аналог)

**Описание:** Drop-in замена. Verify maintenance перед commit.

**Risk:** research findings R6 не верифицировал maintenance status этого package; нужен additional check (last release date, GitHub stars, opened issues). Может быть так же stale как django-cryptography-django5.

**Pros:**
- 0 custom LOC.
- Похожий API на django-cryptography (transparent wrapper).

**Cons:**
- Зависим от внешнего maintainer (тот же риск, что довёл нас до текущей проблемы).
- Меньше контроля над rotation / keyring / cipher choice.

---

### C. Stay with `django-cryptography-django5` + flag risk

**Описание:** Не менять; повысить attention в monitoring.

**Pros:**
- 0 work сейчас.

**Cons:**
- Технический долг копится. На Django 6.0 LTS (2028) гарантированно сломается.
- Если CVE в `cryptography` транзитивно — fixes придут с задержкой.
- Compliance signal: NN #7 + 152-ФЗ ст. 19 (защита ПДн) требует «принять все необходимые меры». Stale package — слабая позиция при РКН-аудите.

**Verdict:** не рекомендуется. Откладывает проблему.

---

### D. Yandex Lockbox direct API (KMS-only)

**Описание:** Каждое encrypt/decrypt — API call в Lockbox. Никаких local keys.

**Pros:**
- Ключ никогда не покидает Lockbox.
- HSM-like security model.

**Cons:**
- **Latency catastrofic.** ~100ms per call × N полей × M запросов. Discovery feed (20 events × 5 PII fields) = 10 seconds на список.
- Cost: Yandex берёт за call (~1₽/1000 calls; 1M MAU × 10 calls/user/day = 10k₽/день).
- Vendor lock-in tighter — миграция с Yandex стоит больше.

**Verdict:** не подходит для transactional usage. Хорош для bootstrap-time decryption (один call при startup для master key), не для per-field per-request.

---

### E. Envelope encryption (DEK + KEK)

**Описание:** Master KEK в Lockbox. Data Encryption Keys (DEKs) — random per-row или per-table, хранятся в БД рядом с encrypted data, зашифрованы через KEK. App fetch'ит KEK при startup → расшифровывает DEKs by demand → расшифровывает data DEK'ом.

**Pros:**
- Industry-standard pattern (AWS KMS, Google Cloud KMS все так делают).
- KEK rotation не требует backfill всех data (только re-encrypt DEKs).
- Per-row DEK даёт хорошую isolation.

**Cons:**
- ~100 LOC код + сложнее design.
- Overkill для MVP scale (<1M rows).
- Можно мигрировать с Option A → Option E позже без data backfill (only DEK structure change).

**Verdict:** хороший long-term path, но overkill для phase 1. Можно зарезервировать как Triggers пересмотра для ADR-014.

-----

## 4. Recommendation

**Option A — `cryptography` (PyCA) + custom `EncryptedField`.**

Обоснование:
1. **Maintenance ownership:** PyCA — формальная организация (Python Cryptographic Authority); 5+ maintainers; релизы каждый месяц. vs stale solo-maintainer fork.
2. **Django-version-agnostic:** работает на 5.2, 6.0, 6.2 LTS без зависимости от форкера.
3. **Manageable scope:** ~50 LOC в `apps/core/crypto/fields.py` — стандартный pattern, не unique complexity.
4. **Security equivalent:** Fernet (AES-128-CBC + HMAC-SHA256) под капотом — тот же что в django-cryptography.
5. **Migration path к envelope (Option E)** open: Option A не блокирует переход на envelope в Phase 5+ если scale потребует.
6. **Окно нулевой миграции:** delete до W1 = только code change; после W1 + production data = backfill task на existing rows.

**Не рекомендуется:**
- B (drop-in replacement) — тот же риск, что довёл до текущей проблемы.
- C (status quo) — kicking the can.
- D (Lockbox direct) — performance unacceptable.
- E (envelope) — overkill сейчас, рассмотреть в Triggers пересмотра.

-----

## 5. Migration plan (если Option A approved)

### Phase 1 (sub-task — ~2 hours):
1. Create `apps/core/crypto/__init__.py` + `fields.py` (~50 LOC EncryptedField) + `keys.py` (~20 LOC Fernet keyring management).
2. Add `cryptography>=43.0` в `pyproject.toml` dependencies (PyCA `cryptography` library).
3. Remove `django-cryptography-django5>=2.0` из dependencies.
4. Update `apps/identity_auth/models.py`: 3 поля (`primary_email_encrypted`, `phone_e164_encrypted`, `provider_uid_encrypted`) → `EncryptedField()` (если W1 ready), либо TextField placeholder с TODO.
5. Update `apps/rsvp/models.py`: 1 поле (`contact_value_encrypted`) аналогично.

### Phase 2 (W1 sprint integration):
6. Wire Yandex Lockbox client в `apps/core/crypto/keys.py` (fetch master Fernet key on startup; fail-fast если отсутствует в prod).
7. Add key rotation skill / management command (`apps/core/management/commands/rotate_pii_key.py`).

### Phase 3 (Triggers пересмотра в ADR-014):
8. При scale >10M rows ИЛИ regulatory requirement — мигрировать на envelope (Option E). Backward-compatible via `MultiFernet` keyring.

### Phase 4 (Update docs):
9. Edit `docs/ARCHITECTURE.md` ADR-014 (Status: Accepted (revised 2026-XX-XX)); добавить Triggers пересмотра entry; обновить «Decision» секцию.
10. Update affected `apps/<ctx>/CLAUDE.md` (rsvp, contacts_sharing): «django-cryptography» → «apps.core.crypto.EncryptedField».
11. Update CHANGELOG.

### Total effort:
- Code change: 2 часа
- ADR + docs update: 30 минут
- **= ~2.5 часа AI work** (founder review separate)

**No data migration needed** — delete до W1 = greenfield.

-----

## 6. Open questions для founder

| # | Question | Default `[В]` |
|---|---|---|
| Q1 | Approve Option A (cryptography + custom field)? | **YES** (рекомендация memo) |
| Q2 | Использовать Fernet (legacy compat) ИЛИ AES-256-GCM (modern AEAD)? | **Fernet** — equivalent security для use case, проще migration с django-cryptography в будущем если нужно |
| Q3 | Key rotation period? | **1 год** (как в текущем ADR-014); реализовать через `MultiFernet` keyring |
| Q4 | Готов делать ADR-014 update в этом же PR (#6) или отдельный PR? | **Отдельный PR** — ADR change должен быть atomic, отдельный для аудит-trail |
| Q5 | Sub-task сейчас (code change в apps/core/crypto/) или wait до W1? | **Сейчас** — окно нулевой миграции, no production data; меньше merge conflicts |

-----

## 7. Risk если NOT to act

- **Probability:** medium-high. Django 5.2 stack может работать с stale package, но при первом minor bump Django/python — fail.
- **Impact:** high. PII encryption — non-negotiable (NN #7). Поломка W1 = блокер для всего MVP.
- **Detection:** late (W1 sprint вряд ли поймает; production incident вероятен).
- **Recovery cost:** если data already в БД encrypted с stale package → migration через decrypt-old + encrypt-new = N×latency, downtime window.

vs

- **Стоимость действия сейчас:** ~2.5 часа AI + founder approval. Zero risk (no data).

**Recommendation:** execute сейчас.

-----

*End of memo. Founder reply (approve/reject/modify) → next action.*
