# Design Partner Trial Kit

Status: public trial input kit
Purpose: give a CTO, Security lead, AI platform owner, or design partner a safe request shape for evaluating one agent-access workflow

Private engine, public proof.

## What This Adds

The Design Partner Brief explains the trial. This kit gives the trial an input surface.

Use these public request files:

```text
examples/requests/design_partner_trial.yml
examples/requests/support_triage_trial.yml
```

The first file is a blank template. The second file is a filled public sample for the support triage workflow used by the demo.

These files are not live secrets, customer data, or production grants. They are role-level request shapes a reviewer can inspect before the CTO wires real live-mode enrichment.

## How To Use It

1. Run the one-command judge harness:

```bash
python3 -m agent.judge
```

2. Read the Design Partner Brief:

```text
docs/DESIGN_PARTNER_BRIEF.md
```

3. Open the request template:

```text
examples/requests/design_partner_trial.yml
```

4. Fill one real agent-access workflow using role-level descriptions only.

5. Compare the filled request against the public support triage sample:

```text
examples/requests/support_triage_trial.yml
```

6. Use the public proof artifacts to evaluate the workflow:

```text
examples/generated/trust_receipt.md
examples/generated/review_room.html
examples/generated/support_triage_agent.proof_health.md
examples/generated/support_triage_trial_report.md
examples/generated/support_triage_trial.outcome_memo.md
examples/evidence/support_triage_trial/
examples/generated/support_triage_trial.evidence_replay.md
examples/generated/support_triage_agent.decision_brief.md
policy/agent_access.yml
agent/adapters/
```

7. Run the public trial sample through the offline runner:

```bash
python3 -m agent.trial examples/requests/support_triage_trial.yml
python3 -m agent.trial examples/requests/support_triage_trial.yml --write
python3 -m agent.trial_outcome_memo examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml
python3 -m agent.trial_evidence_replay examples/requests/support_triage_trial.yml --evidence-dir examples/evidence/support_triage_trial
```

## Request Shape

Every trial request should include:

- candidate agent name, owner, purpose, and requested environment
- requested tools and actions
- blocked write, admin, and production actions
- data classes described at role level
- proof debt with named owner roles
- unsupported claims that must stay blocked
- reviewer routing for Security, Engineering, Ops, Legal, and Finance
- safety defaults that keep approvals, grants, writes, and mutations disabled
- expected trial outputs and success criteria

## Safety Rules

Do not put these into the public request files:

- production credentials
- live sponsor tokens
- customer data
- private prompts
- private v1 source code
- account-specific permission grants
- write-enabled Composio actions
- autonomous approval authority

The request template preserves these defaults:

- no access approval
- no permission grant
- no external write
- no production mutation
- no packet state mutation
- Composio dry-run by default
- human approval remains required

## What A Strong Trial Request Looks Like

A strong request is specific enough to review but safe enough to keep public:

- names systems by category or vendor
- names actions as read-only, draft-only, write-capable, admin, or production-adjacent
- names data classes without including records or customer details
- names reviewer roles instead of private people
- states what proof is missing
- states what must stay blocked
- proposes one validation step before production access

## Current Boundary

This kit now includes a public offline trial runner. It parses the role-level request shape, derives a DecisionPacket and Agent Access Decision Brief, writes a design-partner trial report, and pairs the primary scenario with a Proof Health report for Packet Drift, stale assumptions, and expired reviewer gates.

The runner does not add a write-enabled live integration path, approve access, grant permissions, execute writes, mutate production, or expose private v1 source. Sanitized Nebius, Tavily, Composio, and OpenClaw outputs can be rehearsed through `examples/evidence/support_triage_trial` without weakening the deterministic packet, policy gate, proof debt, blocked claims, or human approval boundary.
