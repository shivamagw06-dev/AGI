# AGI Gather Worker — keep continuous gathering + responsive Mission Control

## Problem

FSE / CGL / FAA running **inside** the uvicorn process starve Ask and Mission Control (`/mission-control/dashboard` times out at 90s+).

Mission Control itself is now **snapshot-backed** (see `docs/AGI_MC_SNAPSHOT.md`): the gather worker builds `snapshot.json`; HTTP only reads it.

## Recommended fix (default) — sidecar on the same Pro box ($0 extra)

One Render web service, **two OS processes**, **one shared disk**:

| Process | Role |
|---|---|
| `uvicorn` (HTTP) | Ask, Mission Control, APIs — gather flags **off** |
| `python scripts/gather_worker.py` | CGL + FAA + FSE — gather flags **on** |

`agib-intelligence-engine` start command:

```bash
bash scripts/start_engine.sh
```

Controlled by:

| Env | Default | Meaning |
|---|---|---|
| `AGI_GATHER_SIDECAR` | `true` | Launch gather sibling process |
| `AGI_GATHER_SIDECAR_DELAY_SEC` | `90` | Wait after boot before gather starts (keeps `/v1/health` + Mission Control responsive) |
| HTTP gather flags | `false` | Set in `render.yaml` + forced in start script |
| `AGI_ROLE=web` | set by start script | HTTP process skips in-process CGL/FAA/FSE entirely |

Gather sidecar runs under `nice -n 10` with milder batch sizes so it cannot starve uvicorn on a shared Pro instance.

### What you do in Render

1. Merge this change / sync Blueprint (or redeploy `agib-intelligence-engine`).
2. Confirm start command is `bash scripts/start_engine.sh`.
3. Leave **Pro** on `agib-intelligence-engine` (no upgrade required).
4. Keep your existing disk at `/var/data/kip` on this web service.
5. Open Mission Control — should load while logs still show FSE/CGL on the sidecar.

Verify logs contain:

```text
[start_engine] launching gather sidecar
[start_engine] launching uvicorn
gather_worker_ready
```

And `/v1/health` stays fast while gather continues.

---

## Optional — dedicated Background Worker (~$25–85/mo)

Use only if the Pro box is still CPU-saturated after the sidecar.

### Render UI steps

1. **Blueprint sync** (or create manually):
   - New service type: **Background Worker**
   - Name: `agib-intelligence-worker`
   - Runtime: Python
   - Root: `intelligence-engine`
   - Build: `pip install -r requirements.txt && python -m playwright install chromium`
   - Start: `python scripts/gather_worker.py`
   - Plan: **Standard** ($25) to start; upgrade to **Pro** if gather is heavy

2. **Disk / data (important)**  
   Render disks **cannot be shared** between services.
   - Prefer: keep disk on the **web** service + sidecar (default above), **or**
   - Attach a disk to the worker at `/var/data/kip` and set `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` on **both** so knowledge can mirror, **or**
   - Migrate the primary disk to the worker (web then relies on Supabase reload)

3. **Turn off sidecar on the web service** so gather isn’t double-running:

   On `agib-intelligence-engine` → Environment:

   | Key | Value |
   |---|---|
   | `AGI_GATHER_SIDECAR` | `false` |
   | `CONTINUOUS_GATHER_LEARN` | `false` |
   | `FAA_BACKGROUND_COLLECTOR` | `false` |
   | `KF_HD_LIVE_COLLECTORS` | `false` |

4. On `agib-intelligence-worker`, set gather **true** (Blueprint already does) and copy the same secrets (`KIP_DATA_DIR`, Supabase, tokens).

5. Redeploy both. Confirm worker logs: `gather_worker_ready` + `cgl_cycle` / FSE ingest.

---

## Do you need to buy anything?

| Goal | Buy? |
|---|---|
| Continuous gather + working Mission Control | **No** — use sidecar (default) |
| Gather on its own CPU because Pro is maxed | **Yes** — Standard (~$25) or Pro worker |
| Bigger single web plan only | **Not recommended** — same architecture problem |

No OpenAI / Gemini required.

## Node API

`CONTINUOUS_GATHER_LEARN_SCHEDULER` is **false** on `agib-api` so Node no longer POSTs heavy CGL runs into the HTTP engine (those were showing as 90–300s `userAgent=node` timeouts).
