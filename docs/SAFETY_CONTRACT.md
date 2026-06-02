# Safety Contract

InferenceAtlas prepares proof packets. Humans approve decisions.

This public demo is intentionally conservative. Its job is to show the review layer before an agent receives tools, data, spend, or production access.

## Default Demo Posture

The default command:

```bash
python3 -m agent.demo
```

runs in offline deterministic mode. It does not require keys, does not call live vendors, and does not mutate external state.

Default safety state:

| Safety field | Default |
| --- | --- |
| Access approval granted | `false` |
| External writes enabled | `false` |
| Composio dry-run | `true` |
| Packet state mutation | `false` |
| Human approval required | `true` |
| Public demo posture | `review_packet_only` |

These defaults are represented in `examples/generated/support_triage_agent.packet.json` and `examples/generated/support_triage_agent.decision_brief.json`, then tested in `tests/test_decision_packet.py` and `tests/test_decision_brief.py`.

## What IA Does

InferenceAtlas creates a DecisionPacket that shows:

- source status
- approval posture
- requested capability
- tool access plan
- tool scope
- data scope
- evidence notes
- blocked claims
- missing proof
- reviewer owners
- reviewer action items
- next human validation
- safety state

The packet is meant to make review work explicit before an agent receives access.

InferenceAtlas also derives an Agent Access Decision Brief from the packet. The brief shows:

- access eligibility go/no-go
- runtime permission boundary
- access envelope
- risk register
- reviewer gates
- sponsor readiness
- safety state

The brief does not grant access. It is a skim-ready reviewer surface derived from the packet.

## What IA Does Not Do

IA does not:

- approve agent access
- grant tool permissions
- dispatch Slack, Jira, GitHub, or other external actions by default
- mutate production state
- mutate packet state in the public demo path
- certify compliance
- guarantee savings
- claim model quality lift without evaluation evidence
- claim latency, throughput, or capacity readiness without measurement
- claim procurement, security, legal, or finance approval without named reviewer evidence

## Blocked Claims Stay Visible

Unsupported claims remain blocked in the packet rather than hidden in prose.

For the support triage scenario, the default packet blocks:

- production tool-access approval
- customer-data safety claims without retention/logging proof
- Jira/GitHub/Slack write actions without rollback and off-switch proof
- compliance-readiness claims without reviewer evidence

This is the product stance: uncertainty is not erased; it becomes review work.

## Sponsor Integration Safety

### Nebius

Nebius can enrich live packet narration when keys are present. It does not own deterministic truth, approve access, or override blocked claims.

### Tavily

Tavily can add live evidence notes with source URLs and freshness status. Search results enter the packet as evidence notes, not automatic approval truth.

### Composio

Composio is used for scoped tool-access planning. The public demo keeps Composio dry-run by default and must not create tickets, post messages, change repositories, or mutate external systems unless a future operator explicitly enables live writes outside the judge-safe path.

### OpenClaw

OpenClaw can run the optional live agent loop. It must preserve the same packet safety contract: review packet first, human approval before access.

## Verification

Run:

```bash
python3 -m agent.demo
python3 -m unittest discover -s tests
```

The demo should generate the packet artifacts under `examples/generated/`, and tests should verify that approval and external writes are disabled by default.

The demo should also generate the decision brief artifacts under `examples/generated/`, and tests should verify that production access remains blocked while scoped validation review can move forward.

CI runs the same no-key safety path in `.github/workflows/smoke.yml`.

## Review Principle

Most agent demos show an agent taking action. InferenceAtlas shows the missing review layer before action: the proof packet a company needs before giving agents tools, data, spend, or production access.
