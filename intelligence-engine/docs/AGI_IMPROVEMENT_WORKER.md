# Ask AGI Investment Intelligence Improvement Worker

This worker implements a controlled evaluation loop; it does not retrain OpenAI model weights.

## Railway service

Create a separate background worker using `intelligence-engine/railway.improvement.toml`. Do not replace the web service or gather worker.

Required environment variables:

- `AGI_ENGINE_URL`: Ask AGI engine base URL.
- `OPENAI_API_KEY`: evaluator project key; never stored in reports.

Safe defaults:

- 100 questions per assigned session.
- 10-question batches.
- concurrency 2, hard maximum 8.
- six-hour maximum runtime.
- no code modification, merge, deployment, database migration, or trading.

Optional controls:

- `AGI_IMPROVEMENT_QUESTION_LIMIT`: use the validated ramp 100 → 250 → 500 → 1000 → 2500.
- `AGI_IMPROVEMENT_BATCH_SIZE`
- `AGI_IMPROVEMENT_CONCURRENCY`
- `AGI_IMPROVEMENT_RUNTIME_HOURS`
- `AGI_EVAL_MODEL`, `AGI_EVAL_REASONING`, `AGI_EVAL_TIMEOUT_SEC`
- `AGI_IMPROVEMENT_MAX_MODEL_CALLS` (hard default: 100)
- `AGI_EVAL_INPUT_USD_PER_MILLION`, `AGI_EVAL_OUTPUT_USD_PER_MILLION` for cost reporting
- `AGI_IMPROVEMENT_OUTPUT_DIR` (mount persistent storage at `/data`)

Run a no-cost local preview:

```bash
python -m agi_improvement_engine.worker --count 100
```

Execute explicitly:

```bash
python -m agi_improvement_engine.worker --count 100 --execute --endpoint https://your-engine.example
```

Outputs are append-only `evaluations.jsonl` records and a per-session dashboard under `reports/`. Answers are traces, not factual memory. Only independently evaluated learning events may inform a proposed repair, and meaningful investment-logic changes must remain unmerged for human review.
