# AGI Academy Books V2 — Personal Library Knowledge Ingestion

**Architecture status:** v1.0.1 LOCKED  
**Role:** Extend Academy Books only — not an engine redesign.

## Mission

Convert every book / spreadsheet in the configured personal library into **structured institutional knowledge** (concepts, frameworks, formulas, graph). Never build a searchable PDF corpus. Never retain long verbatim copyrighted text.

## Library roots (first existing wins)

1. `ACADEMY_BOOKS_DIR` / settings `academy_books_dir`
2. `/Users/shivamagarwal/Downloads/AGIB/Books` (or `books/`)
3. `/Users/shivamagarwal/Downloads/AGIB` (if books sit directly in that folder)
4. `~/Downloads/AGIB/Books` → `~/Downloads/AGIB`
5. AGIB project root `Books/` / `books/`
6. `/workspace/books`

### Cloud agents cannot see your Mac folder

Cursor **cloud** agents do **not** mount `/Users/shivamagarwal/Downloads/AGIB/Books`.
Only files under the repo (e.g. `books/`, gitignored) are visible there.

**To teach AGIB from your full Mac library, on your Mac run:**

```bash
bash scripts/sync_mac_books_to_repo.sh --ingest
```

Or manually:

```bash
rsync -av --include='*/' --include='*.pdf' --exclude='*' \
  /Users/shivamagarwal/Downloads/AGIB/Books/ \
  /path/to/AGIB/books/

cd intelligence-engine
ACADEMY_BOOKS_DIR=/Users/shivamagarwal/Downloads/AGIB/Books \
  PYTHONPATH=. python3 -m academy.books.cli ingest
```

Check reachability:

```bash
PYTHONPATH=. python3 -m academy.books.cli status
PYTHONPATH=. python3 -m academy.books.cli scan
```

Learning is persisted to `academy/books/learned/library_snapshot.json` (AGI-owned objects only — never a searchable PDF corpus).

## Supported formats

- Books: PDF, EPUB, DOCX, Markdown
- Spreadsheets: XLSX, XLS, ODS, CSV → formulas, variables, templates, named ranges

## APIs

- `GET /v1/academy/books/library` — scan
- `POST /v1/academy/books/ingest-library` — batch structured ingest + report
- `GET /v1/academy/books/ingestion-report` — latest validation report
- Plus V1 health/dashboard/ingest/package/graph endpoints

## Flags

`ACADEMY`, `ACADEMY_BOOKS`, `ACADEMY_BOOKS_V3`, `ACADEMY_FRAMEWORKS`, `ACADEMY_FORMULAS`, `ACADEMY_GRAPH`, `ACADEMY_SPREADSHEETS`

## Academy Books V3 — Institutional Knowledge Transformation

**No engine / CID / analyst / UI redesign.** Soft layer on V2.

Books already ingested → V3 upgrades *how* knowledge is represented and consumed.

**Retrieve:** knowledge, reasoning, frameworks, lessons, cases, decision rules  
**Never retrieve:** chapters, paragraphs, PDFs, verbatim book text

Pipeline:

`Books → Chapters → Concepts → Frameworks → Formulas → Mental Models → Decision Trees → Cases → Counter Cases → Reasoning Patterns → Checklists → Knowledge Graph → Analysts`

Cross-book topics (e.g. ROIC) resolve to **one** `InstitutionalKnowledgeObject` synthesizing Damodaran / Graham / Klarman / Fridson / Fisher — not five separate paragraphs.

### V3 APIs

- `GET /v1/academy/books/v3/health`
- `GET /v1/academy/books/v3/dashboard`
- `GET /v1/academy/books/v3/quality-gates`
- `POST /v1/academy/books/v3/ask` — `{question, analyst?, ticker?}`
- `GET /v1/academy/books/v3/analyst/{analyst}`

V2 `package_for_query` soft-wires a `books_v3` block. Business / Financial / Valuation IAI knowledge packs soft-consume analyst bases.

## Academy Validation Suite

Separate soft programme: **demonstrate** institutional knowledge (Levels 1–8), do not merely prove ingest.

See `academy/validation_suite/README.md` and `/v1/academy/validation/*`.

## Academy Certification Suite (ACS)

Institutional examination + merge gate (Levels 1–18). Metric = reasoning quality, not book ingest.

See `academy/certification/README.md` and `/v1/academy/certification/*`.  
Gate: `POST /v1/academy/certification/gate` — do not merge unless certification passes.

## Institutional Regression Suite (IRS)

Final gate: **Did this PR make AGIB smarter?** Frozen golden set, IQ deltas, hallucination/drift audits.

See `academy/regression/README.md` · `/v1/academy/regression/*` · `/admin/regression`

## Evidence Intelligence Layer (EIL)

Soft layer addressing ACS/IRS evidence quality: named sources, peer/history gaps, explainable confidence, decision triggers.

See `academy/evidence/README.md` · `/v1/academy/evidence/*`  
Flag: `evidence_intelligence_layer`

## Peer Intelligence Layer (PIL)

Soft comparison layer: peer resolution, history, percentiles, rankings, commentary, scorecards.

See `peer_intelligence/README.md` · `/v1/peer-intelligence/*` · `/admin/peer-intelligence`  
Flag: `peer_intelligence` / `PEER_INTELLIGENCE`

## Filing Intelligence Layer (FIL)

Soft institutional memory from official filings (statements, notes, management, guidance, risks, capital allocation). Updates PIL seed panels → live filing panels.

See `filing_intelligence/README.md` · `/v1/filing-intelligence/*` · `/admin/filing-intelligence`  
Flag: `filing_intelligence` / `FILING_INTELLIGENCE`

## Filing Diff Engine (FDI)

Soft change-detection layer: compares latest vs previous filings (financials, guidance, risks, management, capital). Answers “what changed?” — not “what does this filing say?”

See `filing_diff/README.md` · `/v1/filing-diff/*` · `/admin/filing-diff`  
Flag: `filing_diff_engine` / `FILING_DIFF_ENGINE`

## Management Intelligence Engine (MII)

Soft trust layer: credibility, guidance accuracy, execution, capital allocation, governance, communication, and Management DNA. Answers “can management be trusted?” — not “what did they say?”

See `management_intelligence/README.md` · `/v1/management-intelligence/*` · `/admin/management-intelligence`  
Flag: `management_intelligence` / `MANAGEMENT_INTELLIGENCE`

## Admin

`/admin/academy` — Books V2 panel with ingest action, spreadsheet count, ingestion report table.
