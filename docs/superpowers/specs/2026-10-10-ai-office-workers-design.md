# AI Office persistent workers and staffing integrations
Date: 2026-10-10
Status: proposed specification; architecture approved in conversation, written specification awaiting review.
Repository baseline: ff0a7a3dac8f6e9d60d050e75fe36d565d6d46ba.
Scope: portfolio/ai-office.

## Goal and constraints
Turn the existing staffing workflow into observable, resumable work performed by real executors. Preserve the candidate's verified facts, candidate-specific duplicate protection, prerequisite gates, and existing data. Cover discovery, preparation, review, submission, and status tracking honestly: a missing connector is a blocker, not successful work.
The requested organization is three discovery agents, three document agents, three application agents, plus a manager, status tracker, candidate assistant, and recovery monitor.
Assumptions: retain Python, SQLite, vanilla JavaScript, and one trusted operator for the first release. Reuse local Ollama; no paid model, new hosting subscription, or new external account is required by this specification. This is not a promise of nationwide portal coverage or employment.

## Existing behavior
Greenhouse/Lever discovery polls configured employer boards. First successful scans establish a baseline; unseen listings are not proof of newly posted jobs.
Staff are currently editable workflow roles. Optional Ollama generation saves unverified drafts separately from task results. Task prerequisites and optimistic versions remain authoritative.
Application status is manually recorded with evidence. The chatbot summarizes stored records. No submission connector or inbox monitor is implemented.
ChatGPT plugins are development/conversation capabilities, not runtime credentials for this standalone server.
The Azure pilot is stopped and public authentication remains unresolved; this work must not start it.

## Delivery boundaries
Deliver a persistent execution foundation first, with real discovery and document-generation adapters. Keep unsupported submission and inbox capabilities visibly blocked. Follow with individually tested provider integrations; do not describe planned adapters as installed or operational.
This decomposition prevents a nominal roster of bots from being mistaken for functioning external services.
Alternative considered: migrate to a hosted agent platform. Retaining the existing application avoids a database migration and additional service costs while preserving tested workflow rules.

## Staff and executable responsibilities
| Department | Staff | Behavior and evidence |
| --- | --- | --- |
| 01 | Job collector | Fetch configured Greenhouse/Lever boards; retain source identity and observation time |
| 01 | US software screener | Apply explicit campaign criteria; unknown location or role requires review |
| 01 | Freshness and duplicate checker | Check source posting evidence and canonical requisition identity; block unresolved freshness |
| 02 | CV tailor | Generate a separate draft from verified master CV and job description |
| 02 | Portfolio tailor | Select only verified projects and links supplied by the candidate; block missing inventory |
| 02 | Cover-letter writer | Draft using verified facts; never fabricate qualifications |
| 03 | Eligibility matcher | Record requirement-by-requirement evidence and unknowns |
| 03 | Application QA | Validate completeness and factual references; candidate authorization remains separate |
| 03 | Submission agent | Call only an enabled, verified provider adapter after authorization and identity reservation |
| Operations | Manager | Schedule eligible work, report blocked handoffs, honor pause/stop |
| Operations | Status tracker | Record authenticated provider events or operator evidence; never infer rejection from silence |
| Operations | Candidate assistant | Answer from stored candidate-specific records and timestamps |
| Operations | Recovery monitor | Reclaim expired leases, enforce retry limits, surface ambiguous external outcomes |

Agent names are assignments, not process counts. Reuse matching existing roles without overwriting customized instructions. Capability mappings use stable executor identifiers, not editable display names.
One bounded dispatcher can serve all roles; start with one model call at a time to fit the existing local environment.

## Runtime design
Add an execution module and provider registry beside existing modules. Keep business validation in current service methods; workers must not bypass prerequisites or write task completion directly.
The dispatcher claims due work atomically, commits the lease, performs network/model work outside the transaction, and conditionally commits its result using the lease token and unchanged input revision.
The existing discovery loop remains the sole discovery scheduler during the first release. Its real scan outcomes feed worker health; do not run a second concurrent discovery scheduler. Moving discovery into the queue is a later explicit migration.
Eligible document tasks may enqueue after their existing prerequisites are satisfied and the campaign has automation enabled. Normal manual operation remains available when automation is off.
Worker success means an artifact was produced and persisted. It does not mean the task was approved, an application was sent, or a candidate was placed.

## Persistent records
Add additive, versioned SQLite migrations:
- worker_runs: candidate/project/task references, executor key, input fingerprint, state, attempt count, max attempts, due time, lease token, lease expiry, error code, result reference, created/updated timestamps.
- worker_attempts: run reference, attempt number, start/end, outcome, safe error code, provider receipt reference where applicable.
- automation_settings: candidate reference, enabled flag, revision, and last change time.
Enforce a unique run key on executor, task ID, task version, and input fingerprint. The fingerprint includes candidate source facts, job description, prerequisites, relevant lessons, and adapter/model version.
Use existing source identities and application_identities for requisition-level deduplication; a unique worker-run key alone does not prevent duplicate applications.
Retain old rows and migration compatibility. Store no passwords, access tokens, or CV text in operational error messages.

## States, retry, and cancellation
Run states: queued, running, retry_wait, succeeded, blocked, failed, cancelled, unknown_outcome.
Claim with BEGIN IMMEDIATE; only queued or due retry_wait records may transition to running. Claim assigns a unique lease token and increments attempts.
Default maximum three attempts, with retry delays of 30 and 120 seconds. Retry only classified transient failures. Respect provider Retry-After when supported, capped to one hour.
Missing credentials, invalid candidate inputs, unsupported adapters, authentication failures, and unmet prerequisites become blocked rather than repeated requests.
Use a 240-second lease and renew every 30 seconds during bounded calls. Late results from an expired or replaced lease cannot commit.
Expired leases for read-only discovery and draft work may retry within the attempt budget. External submissions with uncertain outcomes become unknown_outcome, requiring provider reconciliation before another attempt.
A pause prevents new claims and follow-up handoffs. Recheck campaign revision and stop conditions before provider calls and before saving results. A call already transmitted cannot be undone; record its outcome without creating further work.
Preserve the existing candidate STOP_STATES. Confirmed job start ends automated searching. Paused or withdrawn campaigns never resume implicitly.

## Submission and status boundary
The initial foundation includes no live submission adapter and sends no applications. The submission capability reports blocked with an actionable explanation.
A later adapter must document its supported service, authentication, permitted API, required fields, idempotency behavior, receipt format, and reconciliation endpoint. Generic portal/browser auto-clicking is not assumed.
Authorization must bind the candidate, requisition, exact document versions, destination, and answers. Any change invalidates authorization.
Reserve candidate plus canonical employer/requisition identity atomically before sending. Unknown identity must be reviewed rather than guessed. Retain the reservation through ambiguous timeouts; never release and blindly resend.
Mark submitted only after recording a real provider receipt. If the provider lacks safe idempotency or reconciliation, an ambiguous attempt requires operator resolution.
Future inbox tracking requires separate runtime OAuth, candidate consent, least-privilege read access, and encrypted token storage outside source control. Do not reuse ChatGPT plugin tokens.
Correlate messages using provider/reference IDs and verified destination; ambiguous matches stay unlinked. Do not send follow-up messages as a side effect.
Rejection lessons distinguish stated employer reasons from hypotheses. A rejection alone does not establish a factual cause.

## Interface and security
Expose bounded, paginated GET /api/worker-runs and GET /api/capabilities.
Add token-protected POST /api/automation-settings, /api/worker-retry, and /api/worker-cancel using expected revisions. Existing origin checks and input limits apply.
Retry is allowed only after resolving the blocker and revalidating inputs; it never bypasses unknown_outcome reconciliation.
Show each staff member's actual capability, last verified execution, current run, and blocker in both the board and 3D view. Animation must reflect stored execution state.
Separate labels for configured, reachable, execution verified, and unsupported. A healthy model inventory response is not proof generation works.
Treat job descriptions, model output, and imported messages as untrusted data. They cannot enable tools, override policy, change credentials, or authorize submissions.
The initial chatbot is for the trusted operator and uses the selected candidate's records. Public candidate chat requires separate authentication and per-candidate access enforcement before deployment.

## Verification and acceptance
- Migration preserves existing tasks, custom staff, drafts, histories, and duplicate identities.
- Competing dispatcher claims execute one logical run; restart reclaims expired work; stale lease results cannot overwrite newer output.
- Injected transient failures stop at the attempt limit; permanent errors block immediately.
- Candidate pause, stop, changed source facts, and changed task versions prevent stale downstream work.
- Existing discovery baselines and canonical duplicate checks continue to work.
- A model timeout, malformed response, or truncated response cannot become a successful draft.
- A real local model must produce a stored draft before generation is labeled execution verified. Fake-provider tests are labeled as such.
- Submission remains blocked when no adapter exists. Contract tests cover duplicate reservations and ambiguous outcomes before any live adapter release.
- Browser checks cover run states, blockers, retry/cancel, refresh persistence, and the mobile/3D view.
- Run the current AI Office unit and browser suites and repository CI for code changes; document precise results without claiming untested provider coverage.
- Deployment is a separate gate: authenticated HTTPS, existing data preservation, a verified shutdown schedule for the authorized pilot, and live smoke tests.

## Completion definition
The foundation is complete only when queued draft work survives restart, runs against the configured local model, retains factual review boundaries, and displays reliable state and blockers. Full staffing automation is incomplete until individually supported submission/status adapters and authenticated deployment are verified.
No candidate data, account credentials, external messages, cloud startup, or application submissions are part of publishing this design.
