# Demo Recording Script

Status: public recording checklist
Purpose: record the 90-second hackathon demo without adding new product scope, exposing private source, or weakening safety defaults

Private engine, public proof.

For the speaker-ready version, use `docs/DEMO_90_SECOND_SCRIPT.md`.

## Freeze Gate

Record only after all checks are true:

- `main` is green.
- `bash scripts/pr_smoke.sh` passes locally.
- `python3 scripts/review_run_rehearsal_gate.py --base-url http://127.0.0.1:8080 --json` passes locally.
- `python3 scripts/demo_rehearsal.py --json` passes locally as the no-key artifact fallback.
- The visual cold-start URL works: `/`.
- Ask IA stays stage-aware for the selected ReviewRun and does not dump raw packets.
- Portkey runway shows the packet revision, BYO guardrail handoff, dry-run verdict, no Portkey Admin API call, and no policy mutation.
- ProofGraph opens on demand and is generated from the current ReviewRun, not a premade screenshot.
- Proof receipts show Support Ops, Engineering, and Security owner lanes; attaching proof does not approve until rerun.
- The script has been rehearsed at least twice.

After this gate passes, do not add product features unless a demo-blocking bug appears.

## 90-Second Talk Track

### 0-10 seconds: frame the product

Every agent demo shows the agent taking action. InferenceAtlas shows the proof packet before an agent is allowed to act.

AI movement is cross-functional. IA turns every team's proof into one packet downstream systems can trust.

### 10-20 seconds: start the ReviewRun

Open:

```text
/
```

Say:

> This is one ReviewRun. I connect a repo, IA indexes only that repo, and the agent asks for scoped access.

Click `Use demo repo` or connect GitHub, select the repo, then click `Review access`.

### 20-35 seconds: show the packet lock

Point at the generated packet state: allowed, review-required, blocked, missing proof, reviewer owners, packet id, and revision.

Say:

> IA did not approve. The packet names what is blocked, what proof is missing, and what humans need to review before this scope can move.

### 35-50 seconds: show Ask IA and proof debt

Ask:

```text
What proof is missing?
```

Say:

> Ask IA is a coach over the current ReviewRun. It knows the selected repo, packet revision, blocked claims, proof debt, and next human action. It cannot approve from chat.

Attach prepared proof for Support Ops, Engineering, and Security. Then rerun the packet.

### 50-65 seconds: show the packet delta

Say:

> Same request, new proof, new packet revision. Proof changes packet state only after rerun. The hard-blocked scopes stay blocked.

### 65-80 seconds: show downstream trust

Click `Test Portkey guardrail` and point at the Portkey runway.

Say:

> Downstream systems do not trust raw agent intent. They trust the IA Packet. Portkey reads the updated packet verdict through the BYO guardrail path. IA made no Portkey Admin API call and did not mutate policy.

### 80-88 seconds: show ProofGraph

Open the generated ProofGraph.

Say:

> This graph shows the proof path: repo request, sponsor proof, packet authority, Portkey, reviewer lanes, and zero writes.

### 88-90 seconds: close with export

Point at Copy ReviewRun packet brief or Export Portkey gate.

Say:

> The output is an exportable review artifact a human can carry into the next decision. IA names the next human action; it does not approve by itself.

## Ask IA Rehearsal Prompts

Use these prompts during rehearsal:

- Can this move?
- What proof is missing?
- What will Portkey do?
- What happens next?

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
- Portkey guardrail test is read-only in this public demo; no Admin API call is made.
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

Advanced packet fixture review remains available at:

```text
/packet?fixture=mcp_tool_blast_radius&autorun=1
```
