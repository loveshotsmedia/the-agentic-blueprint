# Memory

<!-- BEGIN test-data-e2e -->
- 2026-10-22: Cameron mandated test-data proof for ALL software. Readiness is proven by us with test accounts and mock data run end to end on the deployed system, never by waiting for a real user or pilot. Tag every created record (`TEST-<run-id>`, `test+<run-id>@`), keep a manifest, and delete all of it after the end-to-end run passes; re-query to prove zero remain. Full rule: AGENTS.md / CLAUDE.md block `test-data-e2e`.
<!-- END test-data-e2e -->
