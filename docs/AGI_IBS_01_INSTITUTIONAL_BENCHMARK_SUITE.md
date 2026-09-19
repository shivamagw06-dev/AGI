# IBS-01 — AGI Institutional Benchmark Suite

## Permanent institutional benchmark framework

| Field | Value |
| --- | --- |
| **Status** | Production — AGI Intelligence Core benchmarks |
| **Workstream** | IBS-01 |
| **Package** | `intelligence-engine/institutional_benchmarks/` |
| **Brand** | **AGI** |
| **Pass** | ≥ 85 / 100 |
| **Release gate** | Average ≥ 85 · hallucinations 0 · broken provenance 0 · unsupported 0 · consistency failures 0 |

> IBS is AGI’s equivalent of **pytest for intelligence**.

---

## Design principle

| Layer | Owns |
| --- | --- |
| FSE | Facts |
| FIL | Disclosures |
| FKB | Financial knowledge |
| FIRE | Deterministic reasoning |
| Offices | Orchestration |
| CW | Company experience |
| IST | Individual institutional cases |
| **IBS** | **Entire AGI Intelligence Core across real-world benchmarks** |

IBS is **not** an intelligence engine, Office, Company Workspace, or validation fixture.

The purpose of IBS is not to prove AGI reaches the same conclusion as other research houses.

The purpose is to prove that AGI consistently produces traceable, evidence-backed, internally consistent, institutional-quality research from raw evidence, across many sectors, companies and market environments.

IBS validates the entire AGI Intelligence Core across real-world institutional benchmark scenarios.

---

## Categories

BANKING · IT · PHARMA · INDUSTRIALS · ENERGY · CONSUMER · FINANCIAL_EVENTS · MACRO

Examples: Kotak RBI · Yes Bank Turnaround · HDFC Merger · TCS · Reliance · ITC · COVID 2020 · Rate Hikes …

---

## Pipeline

Raw Evidence → Evidence Graph → FIRE → IO/CW → Institutional Report → Benchmark Evaluation

**Raw evidence only. No fixture answers. No pre-written research.**

---

## Historical blind mode

`--historical-cutoff 2024-05-15` hides every document published after the cutoff, then generates the report under real information constraints.

---

## Consistency

Related questions (e.g. Explain Kotak / Why not HDFC? / Own ICICI instead?) must remain internally consistent or fail with `CONSISTENCY_FAILURE`.

---

## CLI

```bash
python -m institutional_benchmarks --list
python -m institutional_benchmarks --case KOTAK_RBI
python -m institutional_benchmarks --sector BANKING
python -m institutional_benchmarks --run-all
python -m institutional_benchmarks --historical-cutoff 2024-05-15 --case KOTAK_RBI
```

## API

- `GET /v1/institutional-benchmarks`
- `GET /v1/institutional-benchmarks/{case}`
- `POST /v1/institutional-benchmarks/run`
- `POST /v1/institutional-benchmarks/run-all`
- `GET /v1/institutional-benchmarks/dashboard`
