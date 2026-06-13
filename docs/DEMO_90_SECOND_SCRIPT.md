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

## Click-By-Click Timeline

### 0-8 Seconds: Frame

Open the main page:

```text
/
```

Show the root ReviewRun cockpit. Do not start inside the receipt, ProofGraph, or Portkey route.

Say:

> Every agent demo shows the agent taking action. InferenceAtlas shows the packet before an agent is allowed to act.

Then:

> This is the missing review layer for AI movement: what can move, what stays blocked, what proof is missing, and what downstream gates should trust.

### 8-18 Seconds: Start One ReviewRun

Click:

```text
Use demo repo
```

Say:

> I start with one repo. IA indexes only this selected repo for this ReviewRun.

Click:

```text
Review access
```

### 18-34 Seconds: Show The First Packet

Point at:

- IA verdict
- next human action
- allowed / review / blocked scope
- missing proof
- packet id and revision

Say:

> IA did not approve anything. It generated a packet: read access can move, comments need review, and admin-like scopes stay blocked.

Then:

> The important part is that raw agent intent is not trusted. The packet is the object humans and systems can inspect.

### 34-48 Seconds: Ask IA

Click or focus the floating Ask IA window.

Ask:

```text
What proof is missing?
```

Say:

> Ask IA is not a chat approval path. It is a coach over the current ReviewRun: selected repo, packet revision, blocked claims, proof owners, Portkey state, and one next human action.

### 48-62 Seconds: Attach Proof And Rerun

Open:

```text
Proof workbench
```

Select the prepared proof items:

- Support Ops
- Engineering
- Security

Click:

```text
Attach proof
```

Then click:

```text
Rerun packet
```

Say:

> Proof does not silently change the decision. The human attaches proof, then IA regenerates the packet.

Point at the delta.

Say:

> Same request, new proof, new revision. The packet is ready with gates; when Portkey reads it, the downstream result moves from Block to Allow with policy, while repo admin, org-wide write, and secrets stay blocked.

### 62-76 Seconds: Portkey Gate

Click:

```text
Test Portkey guardrail
```

Open the `Portkey` row if it is collapsed.

Point at:

- `IA Packet -> BYO Guardrail -> Portkey`
- `Block -> Allow with policy`
- packet id
- revision
- event id
- latency
- API mutation `false`
- policy mutation `false`

Say:

> Now Portkey consumes the packet-backed verdict. IA returns what this revision allows, what remains blocked, latency, event id, and mutation flags.

Point at the mutation flags.

Say:

> No Portkey Admin API call. No policy push. No GitHub write. Portkey is the enforcement gateway; IA is the packet authority.

If the `Portkey call receipt` area is visible, point at:

- `Proof status`
- `Portkey enforcement outcome`
- `Event kind`
- `Webhook verdict`
- `Mutation flags`

Say:

> If this is wired to a live Portkey dashboard, this receipt proves Portkey called IA through the BYO Guardrail webhook. If not, the local guardrail test still proves the packet-consumption contract.

### 76-82 Seconds: Hash And Receipt

In the result view, find:

```text
Portable approval receipt
```

Point at:

- packet id
- revision
- short hash
- allowed scope
- still-blocked scope

Click:

```text
Open verification
```

On the receipt page, press `Cmd + F` and search:

```text
Content hash
```

Say:

> This content hash is the packet fingerprint. Same request plus new proof creates a new revision and a new hash. The receipt can move across teams without becoming an approval.

### 82-88 Seconds: ProofGraph

Go back to the ReviewRun result tab if needed. Open the `ProofGraph` row.

Click:

```text
Open generated ProofGraph
```

Say:

> This graph is the proof path: repo request, human proof, IA Packet, Portkey, reviewer lanes, and zero writes.

### 88-90 Seconds: Close

Point at the export or review brief action.

Say:

> The output is a portable approval receipt for AI movement: safe to circulate, and clearly separate from autonomous approval.

## If Asked About Live Portkey

Use this exact answer:

> The local demo proves the BYO guardrail contract. For Portkey cloud dashboard proof, I expose this IA endpoint through a public tunnel and configure Portkey to call `/api/portkey/guardrail` with the current packet metadata. It is still read-only: no Admin API mutation and no policy push.

## If Asked Where The Hash Is

Use this exact answer:

> From the main flow, rerun the packet, find `Portable approval receipt`, click `Open verification`, then search `Content hash`. That `sha256:` value is the packet fingerprint Portkey and humans can verify.

## If Asked Where ProofGraph Is

Use this exact answer:

> ProofGraph is generated from the current ReviewRun. After Portkey, open the `ProofGraph` row and click `Open generated ProofGraph`. It is not a premade screenshot; it is generated from the run id, packet revision, proof counts, Portkey state, and zero-write safety boundary.

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
- The content hash is the packet fingerprint.
- The ProofGraph is generated from the current ReviewRun, not a screenshot.
