# KIP v2 — Phase 2.5 Implementation Notes

Scope, deployment activation steps, and what is intentionally deferred, so
nobody mistakes a soft-wire for a hard guarantee.

## What is fully implemented and tested

All 10 modules from the Phase 2.5 spec are real, working, deterministic
Python — no LLM is used anywhere in the extraction, validation, or answer
path (matching the rest of the AGIB accounting/analyst stack's "no
fabrication" convention):

| Module | File | What it does |
|---|---|---|
| 1. Document Intelligence Engine | `document_intelligence.py` | Section detection, paragraph segmentation, table heuristics, entity recognition, importance scoring, evidence-indexed paragraphs |
| 2. Structured Knowledge Builder | `knowledge_builder.py` | 15-category keyword/section classifier -> evidence-backed Facts |
| 3. Financial Intelligence | `financial_intelligence.py` | Regex extraction of 19 metrics with value/period/unit/currency/confidence |
| 4. Management Intelligence | `management_intelligence.py` | Speaker-attributed quote extraction, topic classification, lexicon-based sentiment |
| 5. Change Detection | `change_detection.py` | Period-over-period categorical (new/removed) and numeric (increased/decreased) deltas |
| 6. Knowledge Graph | `knowledge_graph.py` | Stable-ID entity/relationship graph (company/sector/industry/executive/customer/supplier/peer) |
| 7. Evidence Validation | `evidence.py` | Hard gate in `storage/base.py.store_fact()` — no fact is ever stored without it |
| 8. Executive Summary Generator | `executive_summary.py` | Reads only from the Fact store, never from `Document.text` |
| 9. Knowledge Retrieval | `retrieval.py` | Structured-first, embedding-fallback answer search; returns `unknown: True` rather than guessing |
| 10. Incremental Learning | `incremental.py`, `pipeline.py` | Idempotent re-ingestion, restated-report supersession, automatic cross-period change detection |

Storage is a genuine dual-backend design (`storage/base.py` is the shared
contract):

* **`storage/sqlite_store.py`** (default, active in this environment) — real
  on-disk SQLite persistence. No external services required.
* **`storage/postgres_store.py`** + **`storage/schema.sql`** — a complete
  Postgres + pgvector implementation of the same contract, using `asyncpg`
  bridged to a sync API via a dedicated event-loop thread.

## Why Postgres/pgvector is not the *active* backend here

This repo's Supabase credentials (`SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`)
are a REST/PostgREST + Auth API key pair — there is no raw `postgresql://`
connection string (host/port/user/password) available anywhere in this
environment, and no other package in this codebase has a live SQL/DDL
connection to Postgres either (confirmed: `asyncpg`/`sqlalchemy`/`pgvector`
are declared in `requirements.txt` but have zero imports anywhere else in the
repo). Every other "knowledge" package in this codebase (`knowledge_factory`,
`institutional_knowledge_layer`, `institutional_knowledge_tables`, etc.) is
similarly file/in-memory backed for the same reason.

**To activate the Postgres/pgvector backend in a real deployment:**

1. Apply `storage/schema.sql` once against the target Postgres database
   (Supabase SQL editor, `psql`, or a migration tool of your choice).
2. Set `KIP_V2_DATABASE_URL` to a `postgresql://...` connection string for
   that database (this is deliberately a separate variable from
   `SUPABASE_URL`/`DATABASE_URL`, since neither is a Postgres connection
   string in this deployment's current configuration).
3. Restart the service. `kip_v2/storage/__init__.py:get_store()` picks the
   Postgres backend automatically the moment `KIP_V2_DATABASE_URL` is set —
   no other code changes anywhere in the package.

Until then, the SQLite backend gives genuine, tested, on-disk persistence
that satisfies Core Principle 4 ("knowledge persists across sessions") in
this environment.

## Deliberately out of scope for this iteration

* **OCR itself.** Module 1 accepts already-extracted plain text (with
  optional `\f` / `[PAGE n]` page markers). Feeding a scanned document
  through an OCR engine (e.g. Tesseract) is an external ingestion-adapter
  concern — pass the OCR'd text into `ingest()` exactly like native text.
* **Neural embeddings by default.** `embeddings.py` defaults to a
  deterministic, offline "hashing trick" bag-of-words vector so tests and
  default operation never depend on a live API call. `OpenAIEmbedder` is
  wired and functional (`OPENAI_API_KEY` is present in this environment) but
  only activates when `KIP_V2_USE_OPENAI_EMBEDDINGS=1` is explicitly set —
  matching this codebase's general policy of not requiring live external
  calls for default/test behaviour.
* **Named-entity resolution against `entity_resolution` / `knowledge_graph`
  seeds.** `document_intelligence.recognize_entities()` accepts an optional
  `known_entities` dictionary so a caller can plug in
  `entity_resolution.canonical_resolver` output; wiring that integration end
  to end for every document type was left to the caller rather than baked in,
  since it depends on how each ingestion adapter sources its known-entity
  list.
* **Literal million-document load testing.** The storage/indexing design
  (evidence-hash uniqueness index, category/key/period indexes, pgvector
  ivfflat ANN index in the Postgres schema) is built for that scale, but this
  iteration validates correctness on a realistic synthetic two-period
  annual-report corpus, not a live million-document corpus.
