# Institutional Regression Suite (IRS) V1

**Primary question:** Did this pull request make AGIB smarter?

**Architecture status:** v1.0.1 LOCKED  
Soft final gate after Certification (ACS). No engine / UI / provider / ACS / Academy redesign.

## Architecture position

Books → Academy → Analysts → Committee → CIO → Research Writer → **ACS** → **IRS** → Release Report → Production

## Frozen golden set

`golden_set/v1/` is **immutable**. Never edit prior versions; create `v2/` for changes.

## Merge policy

Blocked if Overall IQ decreases, core reasoning decreases, critical hallucinations rise, analyst drift rises, certification fails, recommendation policy violated, or golden benchmark floor fails.

## APIs

- `GET /v1/academy/regression/health`
- `GET /v1/academy/regression/dashboard`
- `POST /v1/academy/regression/run`
- `POST /v1/academy/regression/gate`
- `GET /v1/academy/regression/quality-gates`
- `GET /v1/academy/regression/history`
- `GET /admin/regression` — soft admin surface

## Flag

`institutional_regression_suite` / `INSTITUTIONAL_REGRESSION_SUITE`

## Soft-wire: Evidence Intelligence Layer

IRS dashboard includes an additive `evidence_intelligence` block from `academy.evidence.production.soft_slice_for_irs` (no IRS redesign).

See `academy/evidence/README.md` · `/v1/academy/evidence/*`

## Soft-wire: Peer Intelligence Layer

IRS dashboard includes an additive `peer_intelligence` block from `peer_intelligence.production.soft_slice_for_irs` (no IRS redesign).

Rule checked conceptually: no generic standalone conclusions where peer evidence exists.

See `peer_intelligence/README.md` · `/v1/peer-intelligence/*`

## Soft-wire: Filing Intelligence Layer

IRS dashboard includes an additive `filing_intelligence` block from `filing_intelligence.production.soft_slice_for_irs`.

Rule: company conclusions and historical trends should originate from validated filings when available; peer panels refresh after FIL ingest.

See `filing_intelligence/README.md` · `/v1/filing-intelligence/*`

## Soft-wire: Filing Diff Engine

IRS dashboard includes an additive `filing_diff` block from `filing_diff.production.soft_slice_for_irs`.

Rule: every new filing should generate a Filing Diff Report; material changes must be evidence-linked; cosmetic wording must not be flagged as material.

See `filing_diff/README.md` · `/v1/filing-diff/*`

## Soft-wire: Management Intelligence Engine

IRS dashboard includes an additive `management_intelligence` block from `management_intelligence.production.soft_slice_for_irs`.

Rule: guidance accuracy, credibility, capital allocation and governance must update from filings; no subjective opinion without evidence.

See `management_intelligence/README.md` · `/v1/management-intelligence/*`
