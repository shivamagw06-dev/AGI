# P2.3 — Ownership Intelligence

NSE Shareholding Master + SHP XBRL evidence layer for institutional ownership.

## What this is

Correct ingestion / normalization / persistence / exposure of ownership evidence that already exists on NSE. **Not** a new scoring engine and **not** a BUY/SELL generator.

## Pipeline

```text
NSE Master → Quarter Timeline → XBRL Download → XBRL Normalizer
    → Ownership Pack v2 → QoQ + Derived Intelligence → CID / Decision Engine
```

## Correct master field map

| Concept | NSE Master field |
| --- | --- |
| Promoter holding | `pr_and_prgrp` |
| Public holding | `public_val` |
| Employee trusts | `employeeTrusts` |
| XBRL detail | `xbrl` URL |

## APIs

- `GET /v1/ownership-intelligence/health`
- `GET /v1/ownership-intelligence/{ticker}`
- `POST /v1/ownership-intelligence`

## CLI

```bash
python -m ownership_intelligence TCS --xbrl-quarters 2
```

## Frozen surfaces (do not modify here)

Constitution · Governance Spec · Decision Engine formulas · Institutional Gate thresholds · Evaluation Lab · IAT · Mission Control
