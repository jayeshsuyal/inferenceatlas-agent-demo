# Demo Transcript

Command:

```bash
python3 -m agent.demo
```

Mode:

```text
offline_deterministic
```

This no-key path is the default judge-safe run. It does not call live vendors, does not grant access, and does not mutate external state.

## Terminal Output

```text
========================================================================
InferenceAtlas Agent Demo - Offline DecisionPacket
Mode: offline_deterministic | external writes: disabled | Composio: dry-run
========================================================================

# DecisionPacket: Support Triage Agent Access

## Verdict

Do not approve production tool access yet.

Approve a scoped validation review before any production permission grant.

## Approval Posture

- production access: blocked
- validation review: allowed
- read access: candidate_after_scope_review
- write access: blocked_until_rollback_and_off_switch_proof
- compliance claims: blocked_until_named_reviewer_evidence

...

## Safety State

- Approval granted: False
- External writes enabled: False
- Composio dry-run: True
- Packet state mutation: False
- Requires human approval: True
- Public demo posture: review_packet_only

Decision brief:
- Do not grant production access.
- Runtime boundary: Should this agent be eligible for this class of access at all, and what proof is required first?

Generated artifacts:
- examples/generated/support_triage_agent.packet.md
- examples/generated/support_triage_agent.packet.json
- examples/generated/support_triage_agent.trace.json
- examples/generated/support_triage_agent.trace.md
- examples/generated/support_triage_agent.decision_brief.md
- examples/generated/support_triage_agent.decision_brief.json
```

The full packet, trace, and decision brief are checked in as generated artifacts.

## What Judges Should Notice

- The demo works without API keys.
- The output is not a generic agent chat response; it is a structured DecisionPacket plus a skim-ready Agent Access Decision Brief.
- The Decision Brief explains the core distinction: runtime permission prompts answer whether a specific action can run now; InferenceAtlas answers whether the agent should be eligible for this class of access at all, and what proof is required first.
- Approval posture is explicit: validation review can move, production access stays blocked.
- The tool access plan separates dry-run allowances from blocked write actions.
- Production access remains blocked.
- Write actions remain disabled by default.
- Composio is dry-run by default.
- Missing proof is visible instead of hidden.
- Reviewer gates are named before access is approved.
- The next step is validation, not autonomous execution.

## Generated Artifacts

| Artifact | Path |
| --- | --- |
| Markdown packet | `examples/generated/support_triage_agent.packet.md` |
| JSON packet | `examples/generated/support_triage_agent.packet.json` |
| Markdown decision brief | `examples/generated/support_triage_agent.decision_brief.md` |
| JSON decision brief | `examples/generated/support_triage_agent.decision_brief.json` |
| Markdown trace | `examples/generated/support_triage_agent.trace.md` |
| JSON trace | `examples/generated/support_triage_agent.trace.json` |

## Verification

Run:

```bash
python3 -m unittest discover -s tests
```

The tests verify the required packet shape, decision brief shape, blocked claims, safety defaults, generated JSON artifacts, and no-key demo command.
