# CLAUDE.md

Strictly follow all rules, roles, and constraints defined in ./AGENTS.md before doing anything in this repository.

<!-- BEGIN test-data-e2e -->
## Prove software with test data, then delete the test data (Cameron, 2026-10-22: every agent, every model, every repo)

Cameron: "whenever we are building software, we are to test it through and through with TEST
data so that we can ensure that the software is functioning properly. We can NEVER know how
someone would use the software in real time but we can create mock data and test accounts to
ensure the functionality of the software is doing what it needs to do. Whenever the tests are
proven and functional and verified end-2-end, we must delete the test data."

1. **We prove readiness; customers do not.** Never make "ready", "launch-ready" or "ready to
   market" depend on a real user, pilot family or client trying it first. Create test accounts
   and realistic mock data, then run every user journey end to end yourself. A readiness verdict
   cites that end-to-end evidence; "no real user has tried it" is never the reason for "not ready".
2. **End to end means the deployed system**: real sign-in with test accounts, real screens, API,
   database, background jobs and outbound channels (sends go to Cameron's test bench:
   sandbox@dartix.ai, +14707753567, cameron@dartix.ai). Cover every role, the happy path, edge
   cases and error paths. Unit tests and local runs alone are not proof.
3. **Tag everything you create** so it can be found and removed: test emails like
   `test+<run-id>@dartix.ai` (or the repo's documented test domain), names starting
   `TEST-<run-id>`, and every created ID written to a run manifest
   (`work/test-data/<run-id>.json` or the handoff STATUS).
4. **Delete it once proven.** After the end-to-end run passes, delete every record, account,
   file, storage object, calendar event, CRM contact and provider object (Twilio, Vapi,
   ElevenLabs, Stripe, Resend and the like) that the run created, in dependency order. Re-query
   to prove zero remain and put that count in the completion report. Delete only what is in the
   manifest; never touch real customer data.
5. **A failed run keeps its test data** until the fix is proven (it is the evidence), then
   deletes it. Test data left behind is an open item under the reporting contract.
6. **Standing test-bench accounts stay** (the sandbox@dartix.ai advisor and any documented demo
   account); the data each run creates inside them is deleted.
7. Creating and deleting your own tagged test data, including in production, is routine work
   under the approval scope and needs no approval. Real-customer data, schema migrations and
   destructive changes to anything outside the manifest keep their existing gates.
<!-- END test-data-e2e -->
