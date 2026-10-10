# AI Office Worker Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run resumable document-preparation work in the existing office, with truthful execution status and explicit integration blockers.

**Architecture:** SQLite owns durable runs, attempts, leases, and candidate automation settings. A single dispatcher uses stable executor keys and existing business validation; model calls happen outside database transactions. Existing discovery remains the only discovery scheduler.

**Tech Stack:** Python 3.11+, stdlib SQLite/HTTP/threading, vanilla JavaScript, existing optional Ollama and Playwright verification.

**Spec:** docs/superpowers/specs/2026-10-10-ai-office-workers-design.md

## Global Constraints
- One bounded dispatcher can serve all roles; start with one model call at a time to fit the existing local environment.
- Default maximum three attempts, with retry delays of 30 and 120 seconds.
- Use a 240-second lease and renew every 30 seconds during bounded calls.
- Worker success means an artifact was produced and persisted.
- The initial foundation includes no live submission adapter and sends no applications.
- ChatGPT plugins are development/conversation capabilities, not runtime credentials for this standalone server.
- The Azure pilot is stopped and public authentication remains unresolved; this work must not start it.
- Retain Python, SQLite, vanilla JavaScript, and one trusted operator. Preserve existing data and manual workflows.

## Scope and execution
This plan implements the worker foundation. Real submission, inbox OAuth, multi-user authentication, and public deployment need separate provider-specific plans after this foundation; no compatible providers or credentials are currently established.
Do not add placeholder external adapters that report success. Display their blockers using the capability registry.
Use isolated repository work if available. The current workspace is a partial export, not a Git checkout: retrieve needed source through GitHub, preserve remote changes, publish focused commits using a fresh main SHA and expected-SHA lease. Never overwrite remote files from an unverified old export.
Run tests against exact changed source. Do not claim local changes are deployed.

## Review Focus
- A renamed/customized staff role must not silently acquire automation permissions (Task 2).
- Disabling automation while inference is in flight must prevent stale artifact persistence (Task 3).
- A database-busy error during claim must not lose work or terminate the dispatcher (Tasks 1 and 3).
- An old browser retry after another operator change must return 409, preserving the newer state (Task 4).
- Job-description HTML or model instructions must render as text and cannot trigger tools (Tasks 2 and 5).

## File map
New files under portfolio/ai-office:
- worker_store.py: additive schema, atomic transitions, attempts, settings, pagination.
- worker_registry.py: stable executor definitions, task binding, capabilities and input snapshots.
- worker_runtime.py: eligibility scan, dispatcher, heartbeat, recovery and error classification.
- test_worker_store.py, test_worker_registry.py, test_worker_runtime.py, test_worker_http.py: meaningful contract and failure tests.
- verify_workers.py: optional real-model smoke check using synthetic data and a temporary database.
Modify office.py only for initialization, validated routes, task executor bindings, and lifecycle wiring.
Modify ai_staff.py to separate preparation, generation, and guarded persistence while preserving the manual draft endpoint.
Modify app.js, workflow.js, index.html, style.css for worker status/control surfaces.
Extend verify_browser.py and README.md. No new runtime dependencies.

### Task 1: Durable run store and atomic claims
**Files:** Create worker_store.py and test_worker_store.py; modify Office initialization in office.py.

**Interfaces:** All functions receive an Office instance, open/close their own connection, and use UTC epoch seconds internally. Run records are dictionaries with id, revision, task_id, task_version, candidate_id, executor, fingerprint, state, attempts, due_at, lease_token, lease_expires_at, result_ref, error_code.
- initialize(db: sqlite3.Connection) -> None
- enqueue(office, *, task_id: int, task_version: int, candidate_id: int, executor: str, fingerprint: str, now: float) -> dict
- claim(office, *, now: float) -> dict | None
- renew(office, run_id: int, token: str, *, now: float) -> bool
- finish(office, run_id: int, token: str, *, state: str, now: float, error_code: str = "", result_ref: int | None = None) -> bool
- recover_expired(office, *, now: float) -> int
- list_runs(office, *, candidate_id: int, before_id: int | None = None, limit: int = 25) -> dict
Use CHECK constraints for states and limits, foreign keys consistent with existing connection settings, an indexed due-work lookup, and UNIQUE(executor, task_id, task_version, fingerprint). Add settings with candidate PK, enabled default false, revision default 1. Attempts have UNIQUE(run_id, attempt).
A lease-token mismatch or expired lease returns false, never success. Claim increments attempts and inserts an attempt atomically. Only read-only/draft executor kinds can auto-recover; side-effecting kinds go to unknown_outcome.

- [ ] Add unittest fixtures using temporary databases and fixed clocks; assert:
```python
self.assertEqual(enqueue_same_input_twice()[0], enqueue_same_input_twice()[1])
self.assertEqual(len(claim_concurrently_from_two_connections()), 1)
self.assertEqual(claimed["lease_expires_at"], claimed_at + 240)
self.assertFalse(finish_with_old_token())
self.assertEqual(recovered_submission["state"], "unknown_outcome")
```
Each helper belongs to the test fixture and calls the named store APIs; no fixture performs external actions. Test reopening the database preserves existing custom staff/tasks and run records. Hold a SQLite write lock and assert failed claim leaves attempts unchanged.
- [ ] Run `python -m unittest discover -s portfolio/ai-office -p test_worker_store.py -v`; verify the new tests fail because APIs are absent.
- [ ] Implement the schema and transitions, with transient retry delays 30/120 and terminal failure after attempt 3. Enforce limit 1–100 and cursor pagination.
- [ ] Run the same command; require all assertions pass, including migration repeated twice.
- [ ] Commit only this tested store slice.

### Task 2: Stable executor bindings and truthful capabilities
**Files:** Create worker_registry.py and test_worker_registry.py; modify workflow construction in office.py and draft preparation in ai_staff.py.

**Interfaces:**
- worker_registry.capabilities(office) -> list[dict]: entries key, mode, configured, reachable, execution_verified, blocker, last_run_id.
- worker_registry.prepare(office, task_id: int, executor: str) -> dict: task_id, task_version, candidate_id, executor, fingerprint, prompt, model, settings_revision.
- ai_staff.prepare_draft(office, task_id: int, version: int) -> dict
- ai_staff.persist_draft(db, prepared: dict, content: str, created: str) -> int
Persist stable executor mappings by task ID when creating new recruiting workflows. Do not infer authority from editable role names or titles. Existing tasks remain unbound until an explicit validated bind action selects cv_draft, portfolio_draft, or cover_letter_draft.
Preserve existing context hashing, manual endpoint behavior, output limits and UNVERIFIED labeling. Portfolio inputs must contain verified project references in prerequisite results; missing evidence blocks generation. Do not treat an LLM's self-review as verified factual QA.
Capabilities for submission/inbox remain unsupported; chatbot is a stored-record summary; screening is rules-based, not verified universal eligibility.

- [ ] Add tests asserting:
```python
self.assertEqual(capability("submission")["mode"], "unsupported")
self.assertFalse(capability("cv_draft")["execution_verified"])
self.assertEqual(renamed_staff_task_executor(), original_executor)
self.assertIsNone(custom_task_executor())
self.assertNotEqual(fingerprint_before_source_edit, fingerprint_after_source_edit)
```
Also test missing portfolio evidence blocks and untrusted job text cannot select a different executor.
- [ ] Run `python -m unittest discover -s portfolio/ai-office -p test_worker_registry.py -v`; confirm meaningful failures.
- [ ] Implement the registry and pure preparation/guarded-persistence split. Keep the existing manual ai_staff.draft wrapper and tests compatible.
- [ ] Run registry and test_ai_staff.py suites; require unchanged manual drafting behavior and all new tests passing.
- [ ] Commit the registry and draft refactor.

### Task 3: Scheduler, model execution, and recovery
**Files:** Create worker_runtime.py and test_worker_runtime.py; extend store finalization as needed.

**Interfaces:**
- enqueue_eligible(office, *, now: float) -> int
- run_once(office, *, now_fn: Callable[[], float], provider: Callable[[str, str], str]) -> bool
- serve(office, stop: threading.Event) -> None
The scheduler processes only explicitly bound document tasks in enabled campaigns with completed prerequisites. Start queued eligible tasks through existing validated business transitions, then prepare and enqueue the resulting task version. Never automatically approve review or completion.
Claim one run; revalidate inputs/settings/stop state; invoke existing ai_staff.generate; heartbeat using the store lease token. Finalize artifact and successful run in ONE transaction using persist_draft, current source fingerprint, settings revision, and valid lease. Store failures with safe codes.
Use the existing model lock to serialize manual and automated model work. Lock contention postpones without consuming a provider attempt. Preserve existing bounded provider timeout behavior; lease loss prevents saving even if a call returns late.
Transient network/timeouts retry; malformed output, missing model, bad credentials and invalid facts block. Database errors leave recoverable state and do not kill serve. Poll using stop.wait(1), no busy loop.

- [ ] Add fake-provider tests asserting:
```python
self.assertEqual(provider_calls_after_duplicate_ticks, 1)
self.assertEqual(retry_due_times, [start + 30, second_failure + 120])
self.assertEqual(final_run["attempts"], 3)
self.assertEqual(final_run["state"], "failed")
self.assertEqual(drafts_after_pause_during_call, [])
self.assertEqual(drafts_after_source_edit_during_call, [])
self.assertEqual(task_status_after_success, "active")
```
Test restart recovery, late lease completion, database busy recovery, missing model, truncated output, cancelled runs, and all STOP_STATES. An already durable matching draft can resolve a retried run without another inference.
- [ ] Run `python -m unittest discover -s portfolio/ai-office -p test_worker_runtime.py -v`; establish failures before implementing.
- [ ] Implement the dispatcher and guarded transaction with no network activity under a database transaction.
- [ ] Run the runtime suite; require no duplicate inference/artifacts in tested races and no background thread left alive.
- [ ] Commit the tested runtime.

### Task 4: Controls, HTTP contracts, and lifecycle
**Files:** Modify office.py; create test_worker_http.py; extend worker_store.py for settings/actions.

**Interfaces:**
- set_settings(office, candidate_id: int, enabled: bool, expected_revision: int) -> dict
- control_run(office, run_id: int, action: str, expected_revision: int) -> dict
- bind_task(office, task_id: int, executor: str, expected_version: int) -> dict
Add GET /api/capabilities and paginated GET /api/worker-runs?candidate=ID&before=ID&limit=25.
POST /api/automation-settings accepts candidate, enabled, revision.
POST /api/worker-retry and /api/worker-cancel accept id, revision.
POST /api/worker-bind accepts task, executor, version; permit binding only document tasks with candidate context.
Reuse current token, origin, size and integer validation. Reject booleans as IDs. Invalid values return 400; stale revisions 409. Unknown_outcome retry is rejected; ordinary retries require fixed blockers and unchanged inputs, otherwise create a new input-version run through scheduling. Manual retries reset attempts only with an auditable new retry cycle.
Start/stop the dispatcher alongside existing discovery at CLI startup; no worker runs merely from creating Office in tests. Keep loopback binding. Cancellation revokes the lease so late results cannot persist.

- [ ] Add HTTP tests asserting 403 without token/with foreign origin, 409 for stale settings and retry controls, 400 for boolean IDs/unsupported executors, and no resubmission for unknown_outcome. Assert disabled settings survive restart.
- [ ] Run `python -m unittest discover -s portfolio/ai-office -p test_worker_http.py -v`; confirm failures.
- [ ] Implement routes, controls, and explicit worker lifecycle; join managed threads on shutdown within bounded time and reject late commits.
- [ ] Run worker HTTP and existing test_office.py suites; require all pass.
- [ ] Commit the API/lifecycle slice.

### Task 5: Observable board and 3D staff
**Files:** Modify app.js, workflow.js, index.html, style.css, verify_browser.py.

**Interfaces:** Consume Task 4 JSON. Add one worker panel with candidate selection, enable/pause, eligible task binding, paginated history, and retry/cancel controls. Display last successful artifact separately from configured/reachable status.
Refresh while visible at most once every 5 seconds, without overlapping requests; stop on hidden page and preserve unsaved forms. Reuse existing API error handling and connection-loss behavior.
Staff activity in the 3D view derives from running run records and stable task-agent IDs; unsupported agents show blockers, not working animations.

- [ ] Extend browser tests with synthetic data: enable automation, observe persisted run status, pause during a controlled call, verify stale retry conflict, reload history, and mobile layout. Assert literal rendering of '<img src=x onerror=...>' in job/model text and no script execution.
- [ ] Run the extended browser test; confirm it fails for absent controls.
- [ ] Implement controls with textContent rendering and accessible labels; display fixed integration limitations from capabilities.
- [ ] Run `node --check portfolio/ai-office/app.js`, `node --check portfolio/ai-office/workflow.js`, and `python portfolio/ai-office/verify_browser.py`; require pass with screenshots of desktop/mobile status.
- [ ] Commit the UI slice.

### Task 6: Real execution evidence and release documentation
**Files:** Create verify_workers.py; update README.md and appropriate existing CI workflow only if it does not already discover new tests.

**Interface:** `python portfolio/ai-office/verify_workers.py` uses a temporary DB and a locally installed configured model. Creates synthetic candidate facts/job data, runs one bound document task through the dispatcher, reopens the DB, asserts one stored UNVERIFIED draft and succeeded run, and removes its temporary data. No credentials, downloads, submissions or real candidate facts.
Exit nonzero with actionable safe error if the model is unavailable; do not label a skipped smoke test passed.

- [ ] Add a smoke-check function test with injected provider to check assertions and cleanup; label it a fixture test.
- [ ] Implement the standalone real-model command and document enable/pause, blockers, bindings, retry semantics, data backup and known unavailable integrations.
- [ ] Run `python -m unittest discover -s portfolio/ai-office -v`, both JavaScript syntax checks, and the browser test against final source.
- [ ] Run the real-model smoke test if a local runtime is available. If absent, report live generation unverified and do not start the Azure VM to bypass the deployment gate.
- [ ] Review the full change against the spec, fix concrete findings, publish tested commits with a fresh remote-head lease, and inspect relevant GitHub Actions conclusions.
- [ ] Report exact test outcomes, commit links, live-model verification status, and deployment limitations. The foundation remains short of its completion definition until real generation is verified.

## Self-review
Spec coverage: persistence/retries/recovery Tasks 1/3; roles and truthful capabilities Task 2; authorization and input-version gates Tasks 2–4; UI/3D Task 5; acceptance evidence Task 6.
Explicit later deliverables: authenticated submission and reconciliation adapters, inbox OAuth/correlation, public candidate authentication, and protected deployment. Their absence must be visible in the foundation.
Interfaces use shared run keys, lease tokens, source fingerprints and task/settings revisions consistently. Operational actions preserve the existing review boundary. All five review-focus cases have owning tests.
Execution choice awaiting user review: native implementation is recommended because tasks share tightly coupled transaction and revision contracts.
