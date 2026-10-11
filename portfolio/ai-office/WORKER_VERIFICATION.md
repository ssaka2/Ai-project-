# Worker foundation verification — 2026-10-11

This release adds persistent local document workers. It does not add a live submission or inbox adapter, and it is not deployed to the Azure pilot.

## Verified locally
- 122 AI Office unit/service/HTTP tests passed.
- Original Chromium workflow and the new worker Chromium workflow passed using Playwright 1.51.0 headless Chromium.
- app.js, workflow.js and workers.js syntax checks passed.
- Synthetic worker smoke test verified one durable UNVERIFIED draft and unchanged task approval state after reopening its temporary database.
- No real candidate facts or external application submissions were used in these tests.

The existing GitHub AI Office browser job now invokes both browser workflows. Repository CI conclusions must be read from GitHub Actions for the actual published commit; local results are not CI results.

## Independent review and fixes
A fresh reviewer identified four important issues. Regression tests reproduced each before the fix:
1. Maximum-length stored drafts could fail cache reuse due to their display prefix. Matching artifacts are now resolved by source digest before raw-output validation.
2. Large individually valid input fields could silently strand tasks. Oversized combined context now records a context_too_large blocker.
3. Database lock contention could revive an expired lease. Renewal and completion account for time waiting on the write lock.
4. 3D status depended on the other panel's candidate and history page. Current status now has an independent aggregate API and polling path.

A further browser-disconnect test verifies that cancelled polling responses do not produce an unhandled server error. Lease finalization and artifact persistence are atomic, including expiry between validation and commit.

## Release limits
The real-model command exited with AI runtime not configured. Live Ollama inference, factual quality, throughput and the deployed worker lifecycle remain unverified. Start the local model and run verify_workers.py before labeling the worker foundation operational on a host.

Submission, inbox tracking, protected public hosting, and authenticated candidate accounts remain separate work. No employment or universal job-site coverage guarantee is made.

Deferred minor review finding: capability reachability and per-staff last-success diagnostics remain limited. Null reachability means unknown, not healthy.

## Implementation decisions
- Used a verified isolated git export because this workspace was not a repository checkout; GitHub remains the authoritative remote history.
- Kept the existing validated task-start transition. Pausing can leave a task active, but invalidates pending worker output.
- Required explicit verified project inventory for portfolio drafting rather than inferring it from arbitrary notes.
- Kept worker UI logic in a separate workers.js asset.
- Used Playwright 1.51.0 locally after the latest browser archive download failed; CI verifies its own configured browser version.
- Preserved the stopped VM and recorded live-model/deployment limitations instead of starting cloud resources.
