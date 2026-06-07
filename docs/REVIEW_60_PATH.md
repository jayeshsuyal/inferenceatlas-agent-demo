# 60-Second Review Path

Private engine, public proof.

Run one command:

```bash
bash scripts/review_60.sh
```

The launcher runs the no-write judge smoke, starts the local web app, and opens:

```text
http://127.0.0.1:8080/workbench?fixture=mcp_tool_blast_radius&autorun=1
```

What the reviewer sees:

1. A public MCP/tool blast-radius fixture.
2. A generated DecisionPacket with verdict, blocked claims, and missing proof.
3. A Sponsor Proof Trace in locked order: Tavily -> Composio -> OpenClaw -> Nebius.
4. A local verification hash and reviewer routing.
5. Export actions for the review brief and verification link.

Safety contract:

- No keys required.
- Dry-run by default.
- No private v1 calls.
- No production access.
- No permission grants.
- No external writes.

The point of this path is speed, not shortcuts. It compresses the public proof harness into one inspectable review moment while preserving the same packet authority boundaries as the full repo.
