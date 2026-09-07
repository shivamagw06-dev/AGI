# AGI Finance Academy v1.2

Institutional **multi-course curriculum library** — not an engine and not a summariser.

## Courses

1. **Principles of Economics (Mankiw)** — markets, policy, macro transmission
2. **Minimalist Accounting (Damodaran)** — how investors read financial statements
3. **Applied Corporate Finance (Damodaran)** — how firms create, preserve, and destroy value

These three form the intellectual foundation before Investment Valuation.

## Academy Books V1 / V2

Additive programme under `academy/books/` — personal library (PDF/EPUB/DOCX/MD) + spreadsheets become structured concepts, frameworks and formulas (never searchable PDFs, never long verbatim text). Soft-wires into FAPI, CID, KF, Ask AGI and Research Writer. See `academy/books/README.md`.

## Mission

Convert teaching sources into reusable knowledge objects so AGI understands mechanisms — capital allocation, ROIC vs WACC, leverage, payout, and M&A — without re-reading books.

## Architecture

Architecture v1.0.1 is LOCKED. Academy only expands curriculum knowledge. Soft consumers expose views for KF, KCV, EVE, IIE, VE, FLE, IRP, and FIML without modifying those packages.

## Toolkits

- Earnings Quality Score + accounting red flags
- Corporate finance decision questions (allocation, leverage, buybacks, acquisitions)
- ROIC–WACC spread as first-class value-creation logic

## Local book PDFs

Place copyrighted PDFs under `/workspace/books/` (gitignored) or set:

- `AGI_ACADEMY_MANKIW_PDF`
- `AGI_ACADEMY_DAMODARAN_PDF`
- `AGI_ACADEMY_ACF_PDF`

Never commit PDFs.
