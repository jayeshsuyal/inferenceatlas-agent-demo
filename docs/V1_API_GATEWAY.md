# InferenceAtlas-v1 API gateway (Option A)

The demo harness does **not** copy `rank_configs` from [InferenceAtlas-v1](https://github.com/jayeshsuyal/InferenceAtlas-v1). Cost questions call the v1 FastAPI over HTTP when configured.

## Flow

```text
User cost question
  → parse_workload_specs (tokens/month, model bucket)
  → POST {INFERENCEATLAS_V1_URL}/api/v1/plan/llm
  → format_engine_block (deterministic table)
  → prepend to orchestrated prompt
  → LLM slot-filler only (no compare_providers / Tavily for prices)
```

If v1 is down or `INFERENCEATLAS_V1_URL` is unset, the demo uses **catalog_fallback** (`agent/catalog_token_fallback.py`) from the static CSV — same monthly math shape, labeled in the UI manifest.

## Configuration

```bash
# .env
INFERENCEATLAS_V1_URL=http://127.0.0.1:8000
INFERENCEATLAS_V1_TIMEOUT=25
```

Start v1 locally (your fork, e.g. `oasb16/InferenceAtlas-v1`), then restart `python3 -m web`.

## Health

`GET /api/health` includes `inferenceatlas_v1`:

- `configured` — URL set
- `ok` — ping succeeded (`/api/health`, `/health`, or `/`)
- `url` — base URL (no secrets)

## Cost question detection

`is_cost_question()` triggers the engine for messages mentioning `compare_providers`, `cheapest`, `pricing`, token/month volumes, or GPT-4 + tokens.

## Attachments

Skills, GitHub, and Drive context still merge into the prompt. The ENGINE block is authoritative for **monthly USD**; attachments are cited per role (access vs architecture vs strategy).
