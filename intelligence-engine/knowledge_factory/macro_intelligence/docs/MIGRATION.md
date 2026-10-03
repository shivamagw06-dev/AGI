# Sprint 6 — IMI Migration Plan

## Scope

Additive Knowledge Factory package only. No Phase 1–7 migrations. No HD/ISI schema changes.

## Steps

1. Deploy `knowledge_factory/macro_intelligence/` package (store under `data/knowledge_factory/macro/`).
2. Run nightly: `POST /v1/knowledge-factory/macro-intelligence/run` (or `run_macro_intelligence_pipeline()`).
3. Validate dashboard: `GET /v1/knowledge-factory/macro-intelligence` — north star `institutional_macro_intelligence_coverage` ≥ 0.7.
4. Soft-consume Macro Evidence Packs / Decision Matrix from existing evidence producers (read-only).
5. Do **not** alter HD or ISI stores; company/sector links are IMI-local overlays.
6. After IMI operational, roadmap advances to **Nifty 500** (coverage scale-out), then Global.

## Rollback

Delete `KF_IMI_STORE_ROOT` (default `data/knowledge_factory/macro/`) and disable the IMI nightly step. KF Track-1 and Phases 1–7 continue unchanged.
