# Sprint 7 — IDQ Migration Plan

## Scope

Additive top-level package `decision_quality/`. No Phase 1–7, KF, HD, ISI, or IMI code changes.

## Steps

1. Deploy `intelligence-engine/decision_quality/`.
2. Store root: `IDQ_STORE_ROOT` (default `data/decision_quality/`).
3. Run: `POST /v1/decision-quality/run` or `run_decision_quality_pipeline()`.
4. Validate: `GET /v1/decision-quality/dashboard` — north star operational.
5. Soft-read IOI lifecycle later (optional); fixtures provide deterministic corpus.

## Rollback

Delete IDQ store directory and disable `/v1/decision-quality/*` routes. Reasoning and KF unchanged.

