# Ask AGI Investment Intelligence Improvement Worker

Controlled evaluation loop for Ask AGI. This is **evaluation-driven self-improvement**, not OpenAI model-weight training.

## Architecture

```text
agi-improvement-worker (Railway, no public URL)
        |
        |  POST /v1/ui/search  (concurrency 2, bounded retries)
        v
agib-intelligence-engine  (healthy path — no agib-api required)
        |
        v
AGI research / retrieval / reasoning
        |
        v
independent OpenAI evaluator
        |
        v
append-only JSONL + Supabase persistence
```

The worker **never** starts the AGI web server and **never** runs on Render.

## Required endpoint

`scripts/improvement_worker.py` calls the intelligence engine directly:

```text
POST {AGI_ENGINE_URL}/v1/ui/search?question=...&ticker=...
```

It does **not** call `agib-api`. Point `AGI_ENGINE_URL` at your healthy `agib-intelligence-engine` public or private Railway URL.

Preflight check: `GET {AGI_ENGINE_URL}/v1/health`

## Railway service: agi-improvement-worker

Create a **separate** background worker. Do not replace `agib-intelligence-engine`, `agib-intelligence-worker`, or `agib-api`.

| Setting | Value |
|---|---|
| Service name | `agi-improvement-worker` |
| Root directory | `intelligence-engine` |
| Config file | `railway.improvement.toml` |
| Builder | Dockerfile |
| Start command | `python scripts/improvement_worker.py` |
| Public networking | **OFF** |
| Replicas | **1** |
| Volume (recommended) | mount at `/data` |

`agib-api` may remain paused or failing — it is not in this dependency chain.

## Environment variables

Required for live runs:

| Variable | Purpose |
|---|---|
| `AGI_ENGINE_URL` | Base URL of `agib-intelligence-engine` (or use `INTELLIGENCE_ENGINE_URL`) |
| `OPENAI_API_KEY` | Independent evaluator only; never stored in reports |

Recommended defaults for first live run:

| Variable | Value |
|---|---|
| `AGI_IMPROVEMENT_QUESTION_LIMIT` | `100` |
| `AGI_IMPROVEMENT_CONCURRENCY` | `2` |
| `AGI_IMPROVEMENT_BATCH_SIZE` | `10` |
| `AGI_IMPROVEMENT_MAX_RETRIES` | `3` |
| `AGI_ASK_TIMEOUT_SEC` | `70` |
| `AGI_IMPROVEMENT_OUTPUT_DIR` | `/data/agi-improvement` |

Optional:

| Variable | Purpose |
|---|---|
| `AGI_IMPROVEMENT_SMOKE_TEST` | `1` → 10-question smoke run |
| `AGI_IMPROVEMENT_DRY_RUN` | `1` → generate questions only, no API spend |
| `INTELLIGENCE_ENGINE_TOKEN` | Bearer token if engine auth is enabled |
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | Durable append-only persistence |
| `AGI_EVAL_MODEL`, `AGI_EVAL_TIMEOUT_SEC` | Evaluator model settings |
| `AGI_EVAL_INPUT_USD_PER_MILLION`, `AGI_EVAL_OUTPUT_USD_PER_MILLION` | Cost reporting |

## Ramp stages (do not skip)

```text
100 → 250 → 500 → 1,000 → 2,500/day
```

Promote only after acceptable error rate, answer quality, evaluator success, latency, engine load, and OpenAI cost.

## Operational sequence

1. Verify `agib-intelligence-engine` is online (`/v1/health`).
2. Create `agi-improvement-worker` with variables above.
3. Mount `/data` volume for local JSONL backup.
4. Run smoke: `AGI_IMPROVEMENT_SMOKE_TEST=1` (10 questions).
5. Run live: `AGI_IMPROVEMENT_QUESTION_LIMIT=100`, concurrency `2`.
6. Watch logs for `[agi-improvement-dashboard]` JSON summary.

## Outputs

Local/volume (append-only):

- `evaluations.jsonl`
- `learning_events.jsonl`
- `reports/<session-id>.json`

Supabase (when configured):

- `agi_improvement_sessions`
- `agi_improvement_evaluations`
- `agi_improvement_learning_events`

## Local commands

Dry run (no spend):

```bash
python -m agi_improvement_engine.worker --count 100
```

Execute against local engine:

```bash
AGI_ENGINE_URL=http://127.0.0.1:8100 \
OPENAI_API_KEY=sk-... \
python -m agi_improvement_engine.worker --count 10 --execute --concurrency 2
```

Railway entrypoint:

```bash
python scripts/improvement_worker.py
```

## Safety

The worker must not trade, auto-merge PRs, auto-deploy material logic, mutate production schemas, or treat AGI answers as ground truth.

Failures produce diagnosis records (`DIAGNOSIS_REQUIRED`) for human-reviewed fixes — not automatic answer regeneration.
