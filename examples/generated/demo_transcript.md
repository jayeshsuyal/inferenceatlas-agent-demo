# Demo Transcript

Status: checked-in judge path
Mode: `offline_deterministic`
Purpose: show the full no-key review flow a judge or AI reviewer should see

This transcript is the public demo path. It does not call live vendors, request secrets, grant access, execute external writes, or expose private v1 source.

## Command Path

```bash
python3 -m agent.judge
python3 -m agent.demo
python3 -m agent.review --list
python3 -m agent.contract --all
python3 -m agent.gate --all
python3 -m agent.adapters --all
python3 -m agent.trust
python3 -m agent.review_room
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m unittest discover -s tests
```

## 1. One-Command Judge Harness

Command:

```bash
python3 -m agent.judge
```

Expected output signal:

```text
# InferenceAtlas Judge Harness

- mode: offline_deterministic
- live keys required: False
- external writes enabled: False
- approval granted: False
- private source exposed: False

## Scenario Matrix

| support_triage_agent | VALIDATION_ALLOWED_WITH_GATES | True | False |
| read_only_analytics_agent | VALIDATION_ALLOWED_WITH_GATES | True | False |
| admin_code_fix_bot | BLOCKED | False | False |

## Access Speed Layer

The packet is the speed layer: safe requests move faster, risky requests are routed, critical requests are blocked immediately.

| support_triage_agent | proof_routed_scoped_validation | immediate | False |
| read_only_analytics_agent | fast_lane_scoped_validation | immediate | False |
| admin_code_fix_bot | blocked_fast | immediate | False |
```

Review signal: a judge or AI reviewer can run one command and see scenario spread, access-speed routing, public contract status, sponsor adapter safety, and the artifact checklist without needing secrets or live integrations.

## 2. No-Key DecisionPacket Demo

Command:

```bash
python3 -m agent.demo
```

Expected output signal:

```text
========================================================================
InferenceAtlas Agent Demo - Offline DecisionPacket
Mode: offline_deterministic | external writes: disabled | Composio: dry-run
========================================================================

# DecisionPacket: Support Triage Agent Access

## Verdict

Do not approve production tool access yet.

Approve a scoped validation review before any production permission grant.
```

Safety signal:

```text
## Safety State

- Approval granted: False
- External writes enabled: False
- Composio dry-run: True
- Packet state mutation: False
- Requires human approval: True
- Public demo posture: review_packet_only
```

Generated scenario artifacts:

```text
examples/generated/support_triage_agent.packet.md
examples/generated/support_triage_agent.packet.json
examples/generated/support_triage_agent.trace.json
examples/generated/support_triage_agent.trace.md
examples/generated/support_triage_agent.decision_brief.md
examples/generated/support_triage_agent.decision_brief.json
```

## 3. Scenario Spread

Command:

```bash
python3 -m agent.review --list
```

Expected output:

```text
Available scenarios:
- support_triage_agent: Read GitHub issues, summarize Slack incident channels, and create Jira draft tickets.
- read_only_analytics_agent: Read aggregate product usage tables, inspect saved dashboards, and summarize internal business metrics.
- admin_code_fix_bot: Push code fixes to production repositories, change organization security settings, and trigger workflows.
```

Review signal:

- low-risk read-only analytics can move into gated validation
- support triage can move into scoped validation while production stays blocked
- admin/prod-write code fixing is blocked before validation

## 4. Public Contract

Command:

```bash
python3 -m agent.contract --all
```

Expected output:

```text
Public contract: agent_access_public.v0
- support_triage_agent: OK
- read_only_analytics_agent: OK
- admin_code_fix_bot: OK
```

Review signal: the public proof surface is not just prose. It is a runnable contract over the generated packet and decision brief artifacts.

## 5. Policy Gate

Command:

```bash
python3 -m agent.gate --all
```

Expected output signal:

```text
# Policy Gate: support_triage_agent

- decision: VALIDATION_ALLOWED_WITH_GATES

# Policy Gate: read_only_analytics_agent

- decision: VALIDATION_ALLOWED_WITH_GATES

# Policy Gate: admin_code_fix_bot

- decision: BLOCKED
- reason: Critical/admin/prod-write access is blocked until Security and Engineering review remove or explicitly approve the risky scopes.
```

Review signal: IA does not flatten risk. The same review engine relaxes for low-risk read-only access, permits gated validation for scoped support access, and blocks critical admin/prod-write access.

## 6. Sponsor Adapter Contracts

Command:

```bash
python3 -m agent.adapters --all
```

Expected output:

```text
Sponsor adapter contracts:
- composio: dry_run_planned | would_execute=False | can_approve_access=False
- tavily: evidence_candidates_planned | would_execute=False | can_approve_access=False
- nebius: deterministic_narration_fallback | would_execute=False | can_approve_access=False
- openclaw: trace_contract_planned | would_execute=False | can_approve_access=False
```

Review signal: sponsor integrations are represented as contracts in the packet flow. They do not approve access, grant permissions, or mutate external state by default.

## 7. Trust Receipt And Review Room

Command:

```bash
python3 -m agent.trust
python3 -m agent.review_room
```

Expected output:

```text
examples/generated/trust_receipt.md
examples/generated/trust_receipt.json
examples/generated/review_room.md
examples/generated/review_room.json
examples/generated/review_room.html
```

Highest-signal artifacts:

```text
examples/generated/trust_receipt.md
examples/generated/review_room.md
examples/generated/review_room.html
docs/REVIEW_ROOM_WALKTHROUGH.md
examples/generated/review_room.desktop.jpg
```

Review signal:

- Trust Receipt joins scenario spread, permission envelope, proof debt, reviewer routing, sponsor runtime plan, policy gate status, and safety state.
- Review Room gives judges one skim surface.
- Static Review Room HTML works without a web app, keys, scripts, or external assets.
- Walkthrough and screenshot give a CTO or founder a safe recording path.

## 8. Design Partner Trial Runner

Command:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
```

Expected output signal:

```text
# Design Partner Trial Report

## Access Speed Lane

- lane: proof_routed_scoped_validation
- decision time: immediate
- highest risk: high

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
- mutates production: False
```

Generated trial artifacts:

```text
examples/generated/support_triage_trial_report.md
examples/generated/support_triage_trial_report.json
examples/generated/support_triage_trial.packet.md
examples/generated/support_triage_trial.packet.json
examples/generated/support_triage_trial.decision_brief.md
examples/generated/support_triage_trial.decision_brief.json
```

Review signal: the repo can now run a role-level design-partner request through the same deterministic packet and brief machinery without secrets, approvals, grants, writes, or private v1 exposure.

## 9. Design Partner Outcome Memo

Command:

```bash
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
```

Expected output signal:

```text
# Design Partner Outcome Memo: support_triage_trial

## Decision

- outcome: scoped_validation_only
- access speed lane: proof_routed_scoped_validation
- production access: False
- permission grants: False
- external writes: False

## Safety Boundary

- approves access: False
- grants permissions: False
- executes external writes: False
```

Generated outcome artifacts:

```text
examples/generated/support_triage_trial.outcome_memo.md
examples/generated/support_triage_trial.outcome_memo.json
```

Review signal: the design-partner trial now ends in a meeting-ready can-move/stays-blocked memo without granting access.

## 10. Unit Tests

Command:

```bash
python3 -m unittest discover -s tests
```

Expected output:

```text
....................................................................
----------------------------------------------------------------------
Ran 112 tests in 1.xs

OK
```

Review signal: tests cover packet shape, decision brief shape, rules engine behavior, scenario spread, public contract, policy gate, dry-run sponsor adapters, Trust Receipt, Review Room HTML, design-partner trial runner, walkthrough artifacts, manifest routing, and private-boundary guardrails.

## What Judges Should Notice

- The demo works without API keys.
- The output is not a generic agent chat response; it is a structured DecisionPacket, decision brief, Trust Receipt, and Review Room.
- The engine produces materially different postures for low, medium/high, and critical access requests.
- The policy gate blocks critical/admin/prod-write access.
- Sponsor adapters are dry-run contracts and cannot approve access.
- The design-partner trial runner accepts a role-level request and derives a report, packet, and brief.
- Production access remains blocked.
- External writes remain disabled.
- Composio remains dry-run by default.
- Missing proof is visible instead of hidden.
- Reviewer gates are named before access can move.
- The next step is human validation, not autonomous execution.
- Private v1 is represented through public proof artifacts, not source exposure.

## Private Boundary

This public repo does not expose:

- private v1 source code
- private prompts
- customer data
- production routing logic
- private reviewer queues
- live sponsor tokens
- account-specific tool grants

Private engine, public proof.

## Generated Artifacts

| Artifact | Path |
| --- | --- |
| Markdown packet | `examples/generated/support_triage_agent.packet.md` |
| JSON packet | `examples/generated/support_triage_agent.packet.json` |
| Markdown decision brief | `examples/generated/support_triage_agent.decision_brief.md` |
| JSON decision brief | `examples/generated/support_triage_agent.decision_brief.json` |
| Markdown trace | `examples/generated/support_triage_agent.trace.md` |
| JSON trace | `examples/generated/support_triage_agent.trace.json` |
| Trust Receipt | `examples/generated/trust_receipt.md` |
| Review Room Markdown | `examples/generated/review_room.md` |
| Review Room HTML | `examples/generated/review_room.html` |
| Review Room walkthrough | `docs/REVIEW_ROOM_WALKTHROUGH.md` |
| Review Room screenshot | `examples/generated/review_room.desktop.jpg` |
| Trial report | `examples/generated/support_triage_trial_report.md` |
| Trial report JSON | `examples/generated/support_triage_trial_report.json` |
| Trial packet | `examples/generated/support_triage_trial.packet.md` |
| Trial packet JSON | `examples/generated/support_triage_trial.packet.json` |
| Trial decision brief | `examples/generated/support_triage_trial.decision_brief.md` |
| Trial decision brief JSON | `examples/generated/support_triage_trial.decision_brief.json` |
| Trial outcome memo | `examples/generated/support_triage_trial.outcome_memo.md` |
| Trial outcome memo JSON | `examples/generated/support_triage_trial.outcome_memo.json` |
