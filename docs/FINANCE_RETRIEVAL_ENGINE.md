# Finance Retrieval Engine (FRE)

Production-grade **intelligence acquisition** layer for AGIB.

## What FRE is

- Evidence retrieval for investment research  
- Multi-source, authority-tiered, provenance-first  
- Continuous ingestion + hybrid search + re-ranking  

## What FRE is not

- Not a chatbot  
- Not a generic web scraper UI  
- Not the reasoning / answer layer  

Downstream AGIB engines (CAE → IRP → RSP → Ask AGI / Decision Engine) consume FRE evidence.

## Soft-wire position

```text
AOI / public sources → FRE → CAE / Ask AGI (finance_retrieval) → reasoning
```

Architecture status: **v1.0.1 LOCKED** (additive only).

## Package

`intelligence-engine/app/fre/`

## Gateway

- Engine: `/v1/fre/*`
- Node BFF: `/api/intelligence/fre/*`

## Quick checks

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "$ENGINE/v1/fre/health"

curl -H "Authorization: Bearer $TOKEN" \
  "$ENGINE/v1/fre/query?q=Should%20I%20buy%20Reliance?"
```

Expect `does_not_answer: true` and a ranked `top_evidence` list with provenance.
