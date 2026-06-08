# Demo Recording Script

Status: public recording checklist
Purpose: record the 90-second hackathon demo without adding new product scope, exposing private source, or weakening safety defaults

Private engine, public proof.

## Freeze Gate

Record only after all checks are true:

- `main` is green.
- `bash scripts/pr_smoke.sh` passes locally.
- The cold-start URL works: `/packet?fixture=mcp_tool_blast_radius&autorun=1`.
- Ask IA answers the four packet-backed prompts without weird or overclaiming replies.
- Portkey export shows dry-run, no API call, false guardrail verdict, and credit limit zero.
- Sponsor Proof Run shows run id, packet reference, sponsor steps, fallback/live flags, and safety locks.
- Team Lenses show Product/Exec, Engineering, Security/Legal, Finance, Procurement, and AI Platform/Ops reading the same packet.
- The script has been rehearsed at least twice.

After this gate passes, do not add product features unless a demo-blocking bug appears.

## 90-Second Talk Track

### 0-10 seconds: frame the product

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

AI movement is cross-functional. IA turns every team's proof into one packet downstream systems can trust.

### 10-25 seconds: start the golden path

Open:

```text
/packet?fixture=mcp_tool_blast_radius&autorun=1
```

Say:

> This is one registered AI movement request. IA turns it into one IA Packet with packet id, revision, hash, verdict, blocked claims, missing proof, reviewer owners, and next human action.

### 25-40 seconds: show the packet lock

Point at the packet decision, verification, and safety state.

Say:

> IA did not approve. The packet names what is blocked, what proof is missing, and what humans need to review before this scope can move.

### 40-55 seconds: show sponsor proof

Point at Sponsor Proof Run or Sponsor Proof Trace.

Say:

> Sponsor tools collect proof around the packet. Tavily, Composio, OpenClaw, and Nebius can enrich evidence, permission diff, trace, or narration, but they cannot approve, grant, write, spend, select providers, or mutate production.

### 55-70 seconds: show downstream trust

Point at the Portkey dry-run gate export.

Say:

> Downstream systems do not trust raw agent intent. They trust the IA Packet. Portkey gets a dry-run gate artifact with no API call made and no production mutation.

### 70-85 seconds: show team lenses and Ask IA

Point at Team Lenses and ask one packet-backed prompt.

Suggested prompt:

```text
Who reviews this?
```

Say:

> Product, Engineering, Security/Legal, Finance, Procurement, and AI Platform/Ops read the same packet through different lenses. Ask IA explains the packet, but the packet remains the authority.

The four Ask IA rehearsal prompts are:

- Can this move?
- What proof is missing?
- Who reviews this?
- Can Portkey allow this spend?

### 85-90 seconds: close with export

Point at Copy IA Packet brief or Export Portkey gate.

Say:

> The output is an exportable review artifact a human can carry into the next decision. IA names the next human action; it does not approve by itself.

## Do Not Show

- `.env`
- API keys or OAuth secrets
- live sponsor tokens
- private v1 source
- customer data
- private prompts
- terminal history containing secrets
- any screen implying approval, permission grants, external writes, spend approval, provider selection, or production mutation

## Required Safety Lines

Use these lines verbatim if the demo reaches a safety boundary:

- IA did not approve. The next human action is named above.
- Sponsor tools collect proof; they do not approve, grant, write, spend, select providers, or mutate production.
- Portkey export is dry-run in this public demo; no API call is made.
- Ask IA explains the packet; it does not replace the packet.

## Backup Path

If the live browser fails, use this no-key fallback:

```bash
bash scripts/review_60.sh
python3 -m agent.judge --no-write
python3 -m agent.sponsor_proof_collector examples/requests/support_triage_trial.yml --no-write
python3 -m agent.portkey_adapter --fixture ai_spend_budget_overrun --mode dry-run --json
python3 -m agent.verify_artifacts
```

Then open:

```text
examples/generated/review_room.html
```

The backup story is the same: one packet, sponsor proof, downstream gate, team review, human export.
