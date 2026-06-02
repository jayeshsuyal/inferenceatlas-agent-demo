# Decision Trace

1. intake: Agent request asks for GitHub, Slack, and Jira access.
2. scope_split: Read paths and write paths are separated before any approval posture is set.
3. tool_access_plan: GitHub, Slack, and Jira get scoped dry-run allowances plus blocked write actions.
4. data_scope: Customer incident context and support escalations are treated as sensitive until policy proof exists.
5. safety_gate: Production access, compliance readiness, and write-action claims remain blocked.
6. reviewer_routing: Security/Legal, Engineering, Support Ops, and conditional Finance owners are named.
7. reviewer_action_items: Each reviewer owner receives the proof task that blocks access from moving forward.
8. next_validation: A scoped dry-run pilot review is the next step, not production access.
