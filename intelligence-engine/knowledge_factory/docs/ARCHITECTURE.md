"""Knowledge Factory Track 1 — architecture & migration (Phases 1–7 frozen).

1. Architecture
---------------
External Sources (Yahoo, Groww, NSE, BSE, RBI, FRED, World Bank/IMF)
        │
        ▼
Knowledge Factory collectors (collect only)
        │
        ▼
Validators (entity, freshness, completeness, provenance, consistency)
        │
        ▼
Normalizers (company / sector / macro)
        │
        ▼
Derived producers (never store PE; compute from primitives)
        │
        ▼
Validated Knowledge Store (file-backed JSON under data/knowledge_factory/)
        │
        ▼
Company / Sector / Macro / Timeline Knowledge Objects
        │
        ▼
Evidence Pack publish (KF packs)
        │
        ▼
Soft adapter → Institutional Evidence Producers (existing)
        │
        ▼
AGIB Phases 1–7 (LOCKED — unchanged)

Knowledge Factory is a SOFT DATA LAYER, not a top-level reasoning engine.

2. Folder structure
-------------------
knowledge_factory/
  collectors/{yahoo,groww,nse,bse,rbi,fred,world_bank}/
  validators/
  normalizers/
  producers/{valuation,accounting,business_quality,risk,sector,macro,timeline,portfolio}/
  schedulers/
  store/
  objects/
  fixtures/
  adapter.py
  production.py
  schema.py

3. Database schema
------------------
File-backed validated store (no Neo4j; no new graph DB):
  data/knowledge_factory/
    raw/{source}/*.json
    validated/{kind}/{ENTITY}.json
    objects/{company|sector|macro|portfolio}/{ID}.json
    packs/{ENTITY}.json
    reports/{coverage|daily}.json

Envelope fields: entity, timestamp, source, freshness, coverage, quality, provenance, payload.

4–6. Object schemas
-------------------
See knowledge_factory.objects.compile:
  - company_knowledge_object
  - sector_knowledge_object
  - macro_knowledge_object

7. Daily pipeline
-----------------
run_daily(): collect → validate → normalise → derive → update objects →
publish packs → coverage report.

8. Validation rules
-------------------
knowledge_factory.validators.pipeline.validate_dataset
Rejects missing / duplicate / conflicting / stale / placeholder / disallowed sources.

9. Acceptance tests
-------------------
tests/test_knowledge_factory.py

10. Migration plan
------------------
a. Deploy KF package alongside IE (same process initially; independent module).
b. Nightly scheduler calls run_daily().
c. Soft-wire already prefers KF validated points in institutional_evidence.historical.
d. When KF unavailable / Yahoo down: existing derived/seed evidence remains valid.
e. Never allow frameworks to call collectors/raw APIs.
f. Expand live collectors behind KF_LIVE_* env flags without touching Phases 1–7.
"""
