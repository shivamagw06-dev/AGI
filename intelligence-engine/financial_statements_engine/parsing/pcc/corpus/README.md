# Production Certification Corpus (Golden Dataset)

Immutable, manually verified reference filings for FSE parser / schema / validation certification.

**Rules**

- `expected/` is reference truth — never overwritten by parser output
- Candidates from freezes go to `results/candidates/` (or store under `FSE_STORE_ROOT/parsing/pcc/candidates/`)
- Promotion into `expected/` requires human review

See `docs/FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md`.
