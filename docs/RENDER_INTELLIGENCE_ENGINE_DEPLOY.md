# Render: deploy AGIB Intelligence Engine (manual)

Cloud agent had **no Render API key / CLI**. Complete these steps in the [Render Dashboard](https://dashboard.render.com).

Repo blueprint: [`render.yaml`](../render.yaml) on `main`.  
Existing live Node API: `https://finance-news-backend-19i5.onrender.com` (do **not** create a second Node service from the blueprint’s `agib-api` entry).

Verified after PR #2 merge: Node already serves `/api/intelligence/*` and returns 503 until the Python engine is up:

```json
{"gateway":"agi-node","ok":false,"error":"fetch failed","hint":"Start intelligence-engine on INTELLIGENCE_ENGINE_URL ..."}
```

---

## Option A (recommended): manual Python service + env on existing Node

### 1. Create Python web service `agib-intelligence-engine`

1. Open [Render Dashboard](https://dashboard.render.com) → **New +** → **Web Service**.
2. Connect GitHub repo `shivamagw06-dev/AGIB` (or `agib`).
3. Set:
   - **Name:** `agib-intelligence-engine`
   - **Branch:** `main`
   - **Root Directory:** `intelligence-engine`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type:** Free (or paid if free spins down too often)
4. **Health Check Path:** `/v1/health`
5. Create the service and wait for the first deploy (green).

### 2. Env vars on the Python service

In **agib-intelligence-engine** → **Environment**:

| Key | Value |
|-----|--------|
| `APP_ENV` | `production` |
| `INTELLIGENCE_ENGINE_TOKEN` | *(same secret you will set on Node — generate a long random string)* |
| `AGIB_API_BASE_URL` | `https://finance-news-backend-19i5.onrender.com` |

Optional later: LLM / provider keys used by agents inside `intelligence-engine/`.

### 3. Wire env vars on the existing Node service

Open the existing service (**finance-news-backend** / `finance-news-backend-19i5`) → **Environment**:

| Key | Value |
|-----|--------|
| `INTELLIGENCE_ENGINE_URL` | `https://<agib-intelligence-engine>.onrender.com` (copy from the new service’s public URL; **no trailing slash**) |
| `INTELLIGENCE_ENGINE_TOKEN` | **exact same** value as on the Python service |

Save → trigger **Manual Deploy** → **Deploy latest commit** if Render does not auto-redeploy.

### 4. Verify

```bash
# Python engine
curl -sS "https://<agib-intelligence-engine>.onrender.com/v1/health"

# Node gateway proxy (should be 200 once engine is awake)
curl -sS "https://finance-news-backend-19i5.onrender.com/api/intelligence/health"
```

Expect Node JSON shaped like `{ "gateway": "agi-node", "engine": { ... }, "engineStatus": 200 }`.

> Free-tier cold starts: first call after idle may take ~30–60s; retry once if you see `fetch failed`.

---

## Option B: Blueprint from `render.yaml` (caution)

`render.yaml` defines **two** services: `agib-api` (Node) and `agib-intelligence-engine` (Python), with cross-linked `INTELLIGENCE_ENGINE_URL` / `INTELLIGENCE_ENGINE_TOKEN`.

1. Dashboard → **New +** → **Blueprint**.
2. Select repo `shivamagw06-dev/AGIB`, branch `main`, file `render.yaml`.
3. Review the plan.

**Risk:** this can create a **new** Node service named `agib-api` alongside the existing `finance-news-backend-19i5`. Prefer Option A unless you intentionally migrate DNS / `VITE_API_URL` / Hostinger secrets to the new Node URL.

If you use Blueprint only for the Python service, delete or skip the `agib-api` service creation and still set env vars on `finance-news-backend-19i5` as in Option A §3.

---

## What Hostinger does **not** cover

Frontend FTP deploy on `main` does **not** start the Python engine. Render is required for `intelligence-engine/`.
