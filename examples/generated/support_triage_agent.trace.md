# Decision Trace

1. intake: Agent request asks for GitHub, Slack, and Jira access.
2. scope_split: Read paths and write paths are separated before any approval posture is set.
3. data_scope: Customer incident context and support escalations are treated as sensitive until policy proof exists.
4. safety_gate: Production access, compliance readiness, and write-action claims remain blocked.
5. reviewer_routing: Security/Legal, Engineering, Support Ops, and conditional Finance owners are named.
6. next_validation: A scoped dry-run pilot review is the next step, not production access.
