# Public Conformance Contract

Before an AI agent receives access to tools, data, spend, or production systems, a pre-permission proof packet should exist.

This document defines the public conformance contract for that packet: what must be shown, what must stay blocked, what evidence must remain visible, and how reviewer gates are represented.

InferenceAtlas v1 implements a private canonical engine. This public contract is the minimum proof surface that any agent-access review implementation should expose.

Private engine, public proof.

## Scope

This contract applies to public agent-access review artifacts in this repo. It is not the private InferenceAtlas v1 schema, production prompt contract, reviewer queue contract, or internal lane taxonomy.

The public contract is intentionally narrow:

- reviewers can inspect it
- judges can run it
- CI can validate it
- sponsor adapters can write into it
- private v1 internals stay private

## Required Packet Surface

A conforming public packet must expose:

| Field | Purpose |
| --- | --- |
| `decision` | The request question, verdict, review posture, and original user problem. |
| `approval_posture` | Production, validation, read, write, and compliance posture. |
| `requested_capability` | Requested systems/actions and their public risk levels. |
| `tool_access_plan` | Tool-level allowance, blocked actions, and required proof. |
| `tool_scope` | Read scope, write scope, and blocked-until-proven scope. |
| `blocked_claims` | Claims the packet refuses to make without proof. |
| `missing_proof` | Evidence or reviewer confirmation needed before access moves. |
| `reviewer_owners` | Owners who must review scope, policy, workflow, or safety. |
| `reviewer_action_items` | Concrete proof work assigned to owners. |
| `next_validation` | The next safe validation step. |
| `safety_state` | Non-negotiable safety defaults. |

## Required Brief Surface

A conforming public brief must expose:

| Field | Purpose |
| --- | --- |
| `decision` | Reviewer-facing verdict and next step. |
| `go_no_go` | Production access, validation review, external writes, and dry-run state. |
| `access_eligibility` | Tool-level eligibility, risk, validation allowance, and required proof. |
| `access_envelope` | What can move in validation and what stays blocked. |
| `reviewer_gates` | Required reviewer gates before access moves. |
| `safety_state` | Same safety defaults as the packet. |

## Safety Requirements

The public contract requires:

- production access is blocked
- external writes are disabled
- Composio remains dry-run by default
- human approval is required
- packet state mutation is disabled
- blocked claims remain visible
- missing proof remains visible
- reviewer gates are explicit

## Conformance Command

Validate all registered scenarios:

```bash
python3 -m agent.contract --all
```

Validate checked-in generated artifacts:

```bash
python3 -m agent.contract --all --generated-dir examples/generated
```

Expected output:

```text
Public contract: agent_access_public.v0
- support_triage_agent: OK
- read_only_analytics_agent: OK
- admin_code_fix_bot: OK
```

## Adapter Rule

Sponsor adapters must write only to public-contract fields.

| Adapter | Allowed public output |
| --- | --- |
| Tavily | Evidence notes or evidence candidates. It must not approve access. |
| Composio | Tool scope, blocked actions, dry-run action plans. It must not execute writes by default. |
| Nebius | Narration or summary projections. It must not own verdicts, safety state, or blocked claims. |
| OpenClaw | Trace steps with blocked/allowed outcomes. It must not hide blocked attempts. |

## Private Boundary

The public contract must not expose:

- exact private v1 schema names
- private lane taxonomy
- private prompts
- production routing logic
- reviewer queue internals
- customer/workspace-specific workflows
- secrets, tokens, or private source code

The bridge is:

```text
private v1 engine
  -> public conformance projection
  -> public repo artifacts / CLI / demo
```

The bridge is not:

```text
public repo = v1 source
```
