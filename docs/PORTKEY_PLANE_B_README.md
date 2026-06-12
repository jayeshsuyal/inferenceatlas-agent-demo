# Portkey Plane B — Optional BYOK Gateway Shell

Status: optional power surface (separate from ReviewRun governance)  
Purpose: let consumers connect **their** Portkey account while IA remains the packet authority

Private engine, public proof.

## Two planes — do not mix them

| | Plane A (main demo) | Plane B (this doc) |
|---|---------------------|-------------------|
| **Surface** | ReviewRun cockpit, `/api/portkey/guardrail` | `/portkey/signin` |
| **Auth** | Shared webhook bearer token (`PORTKEY_GUARDRAIL_TOKEN`) | User's Portkey API key (BYOK) |
| **IA calls Portkey?** | No | Yes — inference proxy only |
| **Mutates Portkey policy?** | No | No |
| **Packet authority** | Yes | Unchanged |

Plane A stays **non-mutating**. Plane B is an optional gateway shell for customers who want to route test traffic through their own Portkey gateway without giving InferenceAtlas a shared Portkey key.

## Consumer-ready path

1. **Customer has a Portkey account** — [app.portkey.ai](https://app.portkey.ai) → Settings → API key.
2. **Customer deploys or subscribes to IA** — `python3 -m web` locally or a hosted URL.
3. **Customer opens Plane B** — top nav **Connect PortKey** → `/portkey/signin`.
4. **Customer pastes their API key** — session-scoped only; never written to `.env`.
5. **Customer configures Plane A guardrail** — export setup sheet; point Portkey BYO Guardrail at IA with packet metadata.
6. **IA remains source of truth; Portkey stays enforcement** — packets govern; Portkey guardrails and gateway enforce at request time.

## Authentication options

### API key BYOK (supported)

Paste your Portkey account API key on `/portkey/signin`. IA verifies it with a minimal `chat/completions` call, stores it in the browser session file on the server, and uses it only for Plane B proxy requests.

Docs: [Portkey authentication](https://portkey.ai/docs/api-reference/inference-api/authentication)

### OAuth “Login with Portkey” (not available)

Portkey does not expose third-party OAuth for embedders. Users sign into Portkey's dashboard to obtain an API key.

### JWT enterprise (not self-serve)

JWT auth is an enterprise add-on (JWKS, scoped tokens, user identity). Contact Portkey sales.

Docs: [JWT authentication](https://portkey.ai/docs/product/enterprise-offering/org-management/jwt)

## API surface

All routes are **separate** from ReviewRun coach/chat. They do not change packet state.

```bash
# Status + consumer path
GET /api/portkey/plane-b/status?session_id=<session>

# Connect (verifies key live)
POST /api/portkey/plane-b/connect
{"session_id":"<session>","api_key":"pk-..."}

# Disconnect
POST /api/portkey/plane-b/disconnect
{"session_id":"<session>"}

# Optional inference proxy (user's key)
POST /api/portkey/plane-b/chat
{
  "session_id":"<session>",
  "model":"gpt-4o-mini",
  "provider":"@openai-prod",
  "messages":[{"role":"user","content":"Say this is a test"}]
}

# Export Plane A guardrail setup merged with Plane B status
GET /api/portkey/plane-b/guardrail-setup?session_id=<session>&public_base_url=https://your-ia.example.com&format=markdown
```

## Safety boundary (always)

Every Plane B response includes:

- `governance_shell_unchanged: true`
- `plane_a_guardrail_non_mutating: true`
- `portkey_policy_mutation_allowed: false`
- `portkey_admin_api_called: false`
- `packet_mutation_allowed: false`
- `external_writes: false`
- `secrets_returned: false`

Plane B proxies **inference** only. It does not push Portkey Admin API policies, mutate packets, or approve access.

## Multi-tenant SaaS

Hosting **one** IA instance for **many** customers requires architecture work not included in this demo:

- Per-tenant `PORTKEY_GUARDRAIL_TOKEN` (or JWT) for webhook auth
- Packet and ReviewRun isolation per tenant
- Session tenancy and data residency boundaries
- Separate public base URLs or path-based tenant routing

Single-tenant / self-hosted BYOK is consumer-ready today.

## Local run

```bash
pip install -e ".[web]"
python3 -m web
```

Open:

- Main governance shell: [http://127.0.0.1:8080/](http://127.0.0.1:8080/)
- Plane B sign-in: [http://127.0.0.1:8080/portkey/signin](http://127.0.0.1:8080/portkey/signin)

Optional env:

```bash
PORTKEY_GATEWAY_URL=https://api.portkey.ai/v1
PORTKEY_PLANE_B_DEFAULT_MODEL=gpt-4o-mini
```

## Tests

```bash
python3 -m pytest tests/test_portkey_plane_b.py -q
```

## YAML analogy

- **Portkey** = runtime gateway (Kubernetes API server)
- **IA packets** = review artifact (`deployment.yaml`)
- **Plane A guardrail** = controller reconciling live requests against packet revisions
- **Plane B** = optional `kubectl proxy` using **your** credentials — helpful, not required for governance

Plane B makes InferenceAtlas a comfortable shell around Portkey without replacing Portkey or breaking the non-mutating governance demo.
