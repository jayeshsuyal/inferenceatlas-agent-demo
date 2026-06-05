# InferenceAtlas-v1 API gateway (Option A)

The demo harness does **not** copy `rank_configs` from [InferenceAtlas-v1](https://github.com/jayeshsuyal/InferenceAtlas-v1). Cost questions call the v1 FastAPI over HTTP when configured.

## Flow (preferred — v1 copilot E2E)

```text
User cost question + shell context (skills, GitHub, Drive, uploads)
  → POST {INFERENCEATLAS_V1_URL}/api/v1/ai/copilot
  → v1: parse_workload_text → rank_configs → rank_catalog_offers → LLMRouter.explain
  → demo returns v1 reply directly (no demo LLM re-summarization)
```

## Fallback (v1 copilot unavailable)

```text
User cost question
  → parse_workload_specs (tokens/month, model bucket)
  → POST {INFERENCEATLAS_V1_URL}/api/v1/plan/llm
  → format_engine_block (deterministic table)
  → prepend to orchestrated prompt
  → demo LLM slot-filler only (no compare_providers / Tavily for prices)
```

When v1 is live, `POST /api/v1/ai/copilot` runs the full product pipeline. `POST /api/v1/plan/llm` returns the deterministic bundle only:

- `rank_configs` deployment plans (score, risk, GPU, monthly USD)
- `engine_summary` (deterministic narrative — not LLM)
- `get_provider_compatibility` diagnostics
- `rank_catalog_offers` per-token catalog ranking (GPT-4o baselines)

If v1 is down or `INFERENCEATLAS_V1_URL` is unset, the demo uses **catalog_fallback** (`agent/catalog_token_fallback.py`) from the static CSV — same monthly math shape, labeled in the UI manifest.

## Configuration

**Demo** (`.env` in `inferenceatlas-agent-demo`):

```bash
INFERENCEATLAS_V1_URL=http://127.0.0.1:8000
INFERENCEATLAS_V1_TIMEOUT=25
```

**v1 server** (separate process — keys for `LLMRouter` parse/explain):

```bash
cd InferenceAtlas-v1
cp .env.example .env   # set OPENAI_API_KEY and/or ANTHROPIC_API_KEY
source venv/bin/activate
uvicorn inference_atlas.api_server:app --host 127.0.0.1 --port 8000
```

v1 loads `InferenceAtlas-v1/.env` automatically when `python-dotenv` is installed.
Without keys, copilot still returns deterministic engine + catalog tables.

Start v1, then restart `python3 -m web` in the demo repo.

## Health

`GET /api/health` includes `inferenceatlas_v1`:

- `configured` — URL set
- `ok` — ping succeeded (`/api/health`, `/health`, or `/`)
- `url` — base URL (no secrets)

## Cost question detection

`is_cost_question()` triggers the engine for messages mentioning `compare_providers`, `cheapest`, `pricing`, token/month volumes, or GPT-4 + tokens.

## Attachments

Skills, GitHub, and Drive context still merge into the prompt. The ENGINE block is authoritative for **monthly USD**; attachments are cited per role (access vs architecture vs strategy).
