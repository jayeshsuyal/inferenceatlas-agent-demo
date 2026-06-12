# 90-Second Demo Script

Status: speaker-ready demo script
Purpose: run the ReviewRun demo in 90 seconds without exposing secrets, private source, or unsafe approval claims

Private engine, public proof.

## Demo Sentence

InferenceAtlas connects to one repo, generates the packet, shows what is blocked, tells the human what proof is missing, reruns the packet after proof, and lets Portkey consume the updated packet before movement. IA never approves, writes, or mutates policy.

## Before You Start

- Open `/` in the local demo.
- Keep `.env`, terminal history, API keys, OAuth pages, and private repos off screen.
- Use `Use demo repo` unless the GitHub connection is already ready and clean.
- Keep Ask IA compact. Use one prompt: `What proof is missing?`
- If live Portkey dashboard proof is not configured through a public tunnel, call it a local BYO guardrail proof, not a live cloud dashboard proof.

## Timeline

### 0-8 Seconds: Frame

Show the root ReviewRun cockpit.

Say:

> Every agent demo shows the agent taking action. InferenceAtlas shows the packet before an agent is allowed to act.

Then:

> This is the missing review layer for AI movement: what can move, what stays blocked, what proof is missing, and what downstream gates should trust.

### 8-18 Seconds: Start One ReviewRun

Click `Use demo repo`.

Say:

> I start with one repo. IA indexes only this selected repo for this ReviewRun.

Click `Review access`.

### 18-34 Seconds: Show The First Packet

Point at verdict, allowed/review/blocked scope, missing proof, packet id, and revision.

Say:

> IA did not approve anything. It generated a packet: read access can move, comments need review, and admin-like scopes stay blocked.

Then:

> The important part is that raw agent intent is not trusted. The packet is the object humans and systems can inspect.

### 34-48 Seconds: Ask IA

Open or focus Ask IA. Ask:

```text
What proof is missing?
```

Say:

> Ask IA is not a chat approval path. It is a coach over the current ReviewRun: selected repo, packet revision, blocked claims, proof owners, Portkey state, and one next human action.

### 48-62 Seconds: Attach Proof And Rerun

Open the proof workbench. Select the prepared Support Ops, Engineering, and Security proof items. Attach proof. Rerun the packet.

Say:

> Proof does not silently change the decision. The human attaches proof, then IA regenerates the packet.

Point at the delta.

Say:

> Same request, new proof, new revision. The packet is ready with gates; when Portkey reads it, the downstream result moves from Block to Allow with policy, while repo admin, org-wide write, and secrets stay blocked.

### 62-76 Seconds: Portkey Gate

Click `Test Portkey guardrail` or show the Portkey stage.

Say:

> Now Portkey consumes the packet-backed verdict. IA returns what this revision allows, what remains blocked, latency, event id, and mutation flags.

Point at the mutation flags.

Say:

> No Portkey Admin API call. No policy push. No GitHub write. Portkey is the enforcement gateway; IA is the packet authority.

### 76-86 Seconds: ProofGraph

Open the generated ProofGraph.

Say:

> This graph is the proof path: repo request, human proof, IA Packet, Portkey, reviewer lanes, and zero writes.

### 86-90 Seconds: Close

Point at the export or review brief action.

Say:

> The output is a portable approval receipt for AI movement: safe to circulate, and clearly separate from autonomous approval.

## If Asked About Live Portkey

Use this exact answer:

> The local demo proves the BYO guardrail contract. For Portkey cloud dashboard proof, I expose this IA endpoint through a public tunnel and configure Portkey to call `/api/portkey/guardrail` with the current packet metadata. It is still read-only: no Admin API mutation and no policy push.

## Do Not Say

- IA approved access.
- IA granted permissions.
- IA pushed a Portkey policy.
- IA wrote to GitHub.
- Portkey changed because IA mutated it.
- The packet replaces human approval.

## Safety Lines

- IA did not approve. The next human action is named above.
- Ask IA explains the packet; it does not replace the packet.
- Proof changes packet state only after rerun.
- Downstream systems trust the IA Packet, not raw agent intent.
- Portkey consumes the packet-backed verdict; IA does not mutate Portkey policy.
