# AGI Knowledge Acquisition Platform (KAIP)

Standalone always-on service that continuously ingests institutional data, converts it into AGI’s canonical knowledge model, and publishes Knowledge Objects to the Intelligence Engine.

**Sprint 6.1** acquisition · **6.2** IKO · **6.3** ILE · **6.4** KRIG · **6.5** Operate (AKO + KFE + KCE).

KAIP does **not** perform reasoning. AKO orchestrates collectors; Ask never triggers them.

## Platform contracts

- Acquisition: [`docs/KAIP_PLATFORM_CONTRACT.md`](docs/KAIP_PLATFORM_CONTRACT.md)
- Knowledge model: [`docs/IKO_PLATFORM_CONTRACT.md`](docs/IKO_PLATFORM_CONTRACT.md)
- Learning engine: [`docs/ILE_PLATFORM_CONTRACT.md`](docs/ILE_PLATFORM_CONTRACT.md)
- Retrieval gateway: [`docs/KRIG_PLATFORM_CONTRACT.md`](docs/KRIG_PLATFORM_CONTRACT.md)
- Orchestrator: [`docs/AKO_PLATFORM_CONTRACT.md`](docs/AKO_PLATFORM_CONTRACT.md)
- Freshness + Confidence: [`docs/KFE_KCE_OPERATE_CONTRACT.md`](docs/KFE_KCE_OPERATE_CONTRACT.md)

## Pipeline

```text
Sources → AKO → Collectors → Raw Event Store → Validation
→ Canonical Normalizer → Entity Resolution → Knowledge Object Builder
→ Relationship Builder → Change Detection → Publisher → Intelligence Engine
```

Ask path (separate):

```text
Ask → KRIG → Published Knowledge → Judgment → Answer
```

## Collectors (only these)

- `YahooCollector` (adaptive; ~30s live)
- `NSEAnnouncementCollector` (adaptive; ~30s live)
- `NSEBhavcopyCollector` (once AFTER_CLOSE)
- `BSECorporateActionCollector` (adaptive; ~30 min)
- `CompanyIRCollector` (adaptive; ~10 min live)

## Operate layer (6.5) — AKO + KFE + KCE

Market sessions drive cadence. Earnings / RBI / Budget events temporarily boost polling. Overnight rebuilds run when users are quiet. Every KO carries **freshness** and **confidence** for IE.

```text
GET  /v1/ako/mission-control
GET  /v1/ako/session
GET  /v1/ako/events
GET  /v1/ako/jobs
GET  /v1/ako/telemetry
GET  /v1/ako/freshness
GET  /v1/ako/confidence
POST /v1/ako/events
POST /v1/ako/tick
GET  /v1/knowledge/freshness/{object_type}/{subject_key}
GET  /v1/knowledge/confidence/{object_type}/{subject_key}
```

## Internal knowledge APIs

```text
GET  /v1/knowledge/company/{symbol}
POST /v1/knowledge/bundle
GET  /v1/knowledge/learning/{symbol}
GET  /healthz
GET  /readyz
```

## Run locally

```bash
cd knowledge-platform
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
KAIP_SCHEDULER=false KAIP_LIVE_COLLECTORS=false uvicorn app.main:app --port 8091
```

## Tests

```bash
cd knowledge-platform
pip install -r requirements.txt
pytest -q
```

## Boundary

Intelligence Engine retrieves published Knowledge Objects / Bundles via internal APIs.  
It must never know Yahoo / NSE / BSE / Company IR exist, and must never trigger collectors.
