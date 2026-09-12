# AGIB Ops Coverage Observability

Shift from **building** historical infrastructure to **operating** it under real workloads.

PR sequence:

- **#295** — Continuous Gather → Learn engine  
- **#296** — Resilient historical collection + backfill  
- **#297** — Self-managing queue, living universe, hard/soft, density  
- **This change** — Mission Control ops: collector health, heat maps, reliability, index coverage, throughput, weekly audit  

## Mission Control boards

### Collector health
Per collector: Success · Last Run · Latency · Queue · Error Rate  
(NSE Bhavcopy, NSE Announcements, BSE Actions, RBI, Company IR)

### Coverage heat map
OHLCV · Financials · Corporate Actions · Annual Reports · Presentations · Transcripts · ESG · Embeddings · Shareholding

### Source reliability
Yahoo · NSE · BSE · RBI · Company IR

### Coverage by index
NIFTY 50 · Next 50 · NIFTY 500 · (SME / BSE-only placeholders until registries expand)

### Backfill throughput
Companies completed today · Years added · Documents · Extracts · ETA

### Weekly coverage audit
Runs at most every 7 days during CGL backfill. Answers:

- Missing historical periods  
- Incomplete financials  
- Failed document downloads  
- Missing embeddings  
- QA failures  
- Degraded collectors  

Then writes a **repair queue** and auto-enqueues hard-gap names (priority: Nifty 50 first).

## Focus

Avoid further architectural features until Mission Control shows, over days/weeks:

1. Backlog shrinking  
2. Coverage % rising  
3. Average depth increasing  
4. Extracts / embeddings growing  
5. Collector error rates low  
6. New listings auto-enqueued  
