# FIRE-03 — Business & Management Intelligence

## Architecture & Engineering Specification

### Version 1.0.0

| Field | Value |
| --- | --- |
| **Status** | Production — evidence extraction (read-only) |
| **Workstream** | FIRE-03 |
| **Package** | `intelligence-engine/business_intelligence/` |
| **Depends on** | IDI (Institutional Documents) · FKB glossary (soft refs) |
| **Frozen** | FSE · FDO · Warehouse · DME · FKB · FIRE-01 · FIRE-02 · Mission Control architecture |

> FSE answers *What are the facts?*  
> FKB answers *What do financial concepts mean?*  
> FIRE-01 answers *What changed?*  
> FIRE-02 answers *Which financial relationships explain it?*  
> FIRE-03 answers *What does management officially say about the business, strategy, risks, and opportunities?*

---

# 1. Mission

Extract, structure, and analyse qualitative business information from **official company disclosures only**.

FIRE-03 is an **evidence extraction engine**, not a text summariser.

- No BUY / SELL
- No valuation
- No forecasting
- No LLM-generated conclusions
- No blogs, analyst reports, or opinion websites

---

# 2. Official sources (priority)

1. Annual Report — MD&A  
2. Annual Report — Chairman / CEO Letter  
3. Annual Report — Business Overview  
4. Segment Reporting  
5. Risk Factors  
6. Corporate Governance Report  
7. Investor Presentations  
8. Quarterly Results Presentation  
9. Earnings Call Transcript (when officially available)

---

# 3. Output model — BusinessFact

Every extracted fact preserves:

| Field | Purpose |
| --- | --- |
| `category` | Taxonomy (profile, strategy, risk, …) |
| `statement` | Structured claim (not a paragraph summary) |
| `evidence` | Verbatim excerpt from the source |
| `page` | Page reference |
| `section` | Section / heading label |
| `document` | Document title / type |
| `document_id` | IDI document id when available |
| `reporting_period` | FY / quarter |
| `confidence` | High / Medium / Low |
| `fkb_refs` | Soft links to `knowledge.glossary(...)` |

---

# 4. Surfaces

| CLI | REST |
| --- | --- |
| `--company TCS` | `GET /v1/business-intelligence/company/{ticker}` |
| `--segments TCS` | `GET /v1/business-intelligence/company/{ticker}/segments` |
| `--strategy TCS` | `GET /v1/business-intelligence/company/{ticker}/strategy` |
| `--risks TCS` | `GET /v1/business-intelligence/company/{ticker}/risks` |
| `--guidance TCS` | `GET /v1/business-intelligence/company/{ticker}/guidance` |

Exposed packs (additive; FIRE-01/02 unchanged):

- `BusinessProfile`
- `ManagementStrategy`
- `SegmentAnalysis`
- `RiskRegister`
- `OpportunityRegister`
- `GuidanceSummary`
- `CapitalAllocationNarrative`

---

# 5. Business Intelligence Report (BIR)

1. Executive Summary  
2. Business Model  
3. Products & Services  
4. Revenue Model  
5. Segment Analysis  
6. Geographic Footprint  
7. Management Strategy  
8. Capital Allocation  
9. Risk Register  
10. Opportunity Register  
11. Management Guidance  
12. Governance Highlights  
13. Source References  

---

# 6. Mission Control (soft board)

- Business documents processed  
- Pages indexed  
- Facts extracted  
- Segment coverage  
- Risk coverage  
- Guidance extracted  
- Confidence distribution  

---

# 7. Non-goals

No recommendations · No valuation · No forecasts · No sentiment analysis · No macro interpretation · No analyst opinions · No hallucinated summaries · No inferred risks beyond disclosed text.

---

# 8. Success criteria

- Every qualitative statement is traceable to an official document.  
- Every extracted fact has page and section references.  
- Business concepts use FKB definitions (no duplicated glossary).  
- FIRE-01 and FIRE-02 remain unchanged.  
- FSE / FDO remain untouched.  
- Zero unsupported management interpretations.  
