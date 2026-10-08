# AI Office

An original local workspace for planning and reviewing agent-assisted work. Built for this portfolio; no Agents Office source, assets, or branding were copied.

## Run

Requires Python 3.11 or newer. No runtime packages, build step, API key, or paid account.

```sh
python portfolio/ai-office/office.py --open
```

The command starts the Python API, SQLite workspace, and discovery worker and opens http://127.0.0.1:4521 on the same computer. Keep the process running. Omit `--open` on a headless server.

**Static hosting is not a running office.** GitHub source pages, GitHub Pages, and opening `index.html` cannot execute the Python backend. The UI now checks for a valid API response, disables workspace controls while disconnected, and offers Retry connection. Relative asset URLs allow this explanation to load in a subdirectory preview. A phone cannot access a different computer using its own localhost address. The Azure pilot is currently deallocated; no live public office is available. Public multi-user hosting still requires authentication, TLS, and a production deployment.

 On Windows, `py` can replace `python`.

1. Add or edit a named agent role and its instructions.
2. Create a task with a brief, assigned role, and optional scheduled start.
3. Start a due task, enter your result, and request review.
4. Review the result, then approve completion or send it back for revision.
5. Search the board or export the workspace as JSON.

Agents are **roles for manual planning**, not autonomous AI processes. You perform the work and paste results into the board. Optional local Ollama draft generation is supported; external submission is not connected. Configured Greenhouse/Lever discovery runs in the background when launched with the command above. Scheduling controls when a task can be started; it does not run a task automatically. Refresh to update scheduled availability. Times are entered in the browser's local timezone and stored in UTC.

## Included

- Responsive queued / active / review / done board and debounced title/brief search. Initially renders at most 25 cards per column; Show more reveals the next 25. Search covers all loaded tasks, including hidden cards.
- Twelve default staff roles: Research, Builder, Reviewer, Planner, Frontend Engineer, Backend Engineer, QA Engineer, Security Reviewer, Data Analyst, DevOps Engineer, Technical Writer, and Support Specialist.
- Per-staff open task counts and reassignment with version checks and recorded history. Existing databases gain specialist roles once; custom roles and renamed staff are preserved.
- SQLite WAL mode allows reads alongside writes. The UI groups tasks once and uses indexed in-memory staff lookup.
- Editable agents, instructions, task notes, and human review transitions.
- SQLite persistence and atomic event history; recent 200 events displayed/exported.
- Conflict detection so stale sessions cannot overwrite newer task edits.
- JSON export of agents, all tasks, and recent activity (no import yet).
- Loopback-only HTTP service, same-origin writes, ephemeral write token, bounded input, explicit static-file allowlist, and a restrictive content security policy.

Data is in `office.sqlite3` beside the server by default, ignored by Git. Use `--db /path/to/office.sqlite3` and `--port 4521` to override. Parent directories must exist. Stop the server before copying the database for backup. Restart with the same file to resume. Exports include task briefs/results: store them privately if they contain private data.

## Tests

```sh
python -m unittest discover -s portfolio/ai-office -v
node --check portfolio/ai-office/app.js
```

Sixty-six automated service/HTTP tests cover the review lifecycle, persistence after reopening the database, competing edits, timezone normalization, scheduled starts, agent changes, validation, exports, cross-origin rejection, and static assets.

Optional real browser verification:

```sh
python -m pip install -r portfolio/booking-web-api/requirements-browser.txt
python -m playwright install chromium
python portfolio/ai-office/verify_browser.py
```

GitHub Actions runs service tests on the portfolio Python matrix and the browser workflow on Chromium. The browser test checks agent creation, the full task lifecycle, reload persistence, search, and mobile overflow, staff reassignment, draft preservation, and bounded rendering of a board with 80 additional tasks. No latency benchmark or speedup percentage is claimed.

## First project: Job Application Operations

Use **Create application workflow** and give each opening a unique project name (company, role, and job reference). This creates eight specialist teams when needed and nine linked tasks, with a project filter and manager progress view. Existing staff instructions are preserved when a matching team name exists.

| Team | Deliverable | Prerequisite |
| --- | --- | --- |
| Applications Manager | Applicant preferences and verified CV | None |
| Job Discovery | Current opening, source URL, job description, duplicate check | Preferences |
| Eligibility | Requirements, fit, missing facts | Opening |
| CV Tailoring | Fact-based tailored CV | Eligibility |
| Cover Letter | Fact-based letter draft | Eligibility |
| Application QA | Reviewed package and recorded applicant approval | CV and letter |
| Submission | Actual submission receipt or an unresolved blocker | QA |
| Submission (same team) | Verified application status, evidence source, time checked, and next check date | Submission |
| Applications Manager | Final application report | Follow-up |

One Submission Team owns both applying and status checking. The Follow-up Team remains available for separately assigned outreach tasks. On upgrade, queued status tasks still assigned to the default Follow-up Team move to their application’s submission owner; existing notes are retained. In-progress, completed, and custom-assigned status tasks are preserved and can be reassigned manually.

The server enforces these prerequisites. Reopening an input is blocked if dependent work has already started; reopen dependent tasks in reverse order first. Duplicate project names are rejected case-insensitively. Task completion, reassignment, notes, and project history survive restart.

**Execution boundary:** these are working coordination tools for manual tasks, not autonomous workers. Configured Greenhouse/Lever feeds and exact-CV-excerpt draft preparation are available below; optional local model calls are supported, but document parsing and external submission integrations are not connected. The workspace never submits an application or sends a message. Team instructions require actual evidence; the software cannot independently verify a pasted receipt or applicant approval. Leave blocked tasks open. Only mark submitted after completing the application on the real portal. Add your master CV and preferences locally; do not commit personal application data to the public repository.

## Application status desk

The Submission Team now has a structured status record per application, separate from task progress. Select an application, record its observed status and evidence (portal/email reference or access blocker), enter when it was checked, and optionally schedule the next check. The manager sees the latest record, full recorded history, and a **Check due** label after the next-check time. Refresh to recompute due labels; there is no background monitor or notification service.

Supported states: not applied, submitted, under review, interview, offer, rejected, withdrawn, unknown, and blocked. Evidence is mandatory; check times cannot be in the future or older than the previous check. Next check must follow the last check. Concurrent stale updates return 409. The latest record and all earlier records survive restart and are included in JSON export. Saving a record never changes task completion or performs an external submission.

Evidence is entered by the local user and is not independently verified. Use Unknown or Blocked when portal/email access cannot confirm a status. Do not place passwords or sign-in tokens in evidence. Unsaved status-form input survives ordinary board saves/refreshes but not a full browser reload; after a conflict, preserve your text, refresh, and reselect the application to load the latest revision.

### Plugin integration boundary

ChatGPT-connected plugins are available to the assistant in the conversation; they are not automatically installed, authenticated, or callable by this standalone Python application. GitHub is used for code and CI. Outlook Email could support reading receipts/status messages after connection; a document provider could supply the approved master CV. Authenticated runtime integrations, credential handling, and model execution are not implemented here; public Greenhouse/Lever discovery is supported. No plugin credentials or personal application records are committed to this public repository. Application teams and placement staff coordinate the workflow; adding roles does not connect external services.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/state` | Workspace plus ephemeral write token |
| GET | `/api/export` | JSON snapshot without the token |
| POST | `/api/application-check` | Append status evidence with integer `project`, current check-id `revision` (0 initially), `status`, `evidence`, timezone-aware `checked_at`, optional `next_check` |
| POST | `/api/job-project` | Create a project from a unique `name`, its team roster, tasks, and handoffs atomically |
| POST | `/api/agents` | Create role; include `id` to edit |
| POST | `/api/tasks` | Create `title`, `brief`, integer `agent`, optional ISO `due` with timezone |
| POST | `/api/update` | Update task using integer `id`, current `version`, `status`, optional `result`, and optional integer `agent` |

POST requests require JSON and the `X-Office-Token` from `/api/state`. Stale versions return 409; invalid input returns 400. A result is required for review/completion, and queued tasks cannot skip straight to done. Approval is a workflow step for one local user, not independent reviewer authentication.

## Limits

Designed for one trusted local user. No accounts, TLS, public hosting, auto-refresh, task deletion, recurring task execution, or independent approver identity. Do not expose the server publicly or tunnel it to the internet. Search, board refresh, pagination, and unrelated saves preserve pending notes and assignments in memory. Reloading/closing the browser loses unsaved edits. Stale drafts retain their original version and cannot overwrite a newer task; copy their contents before using Discard local edits. The API still transfers a full task snapshot, so this is not a server-paginated solution for very large datasets. Agent edits use last-write-wins; task results use version checks. The standard-library HTTP server is for local development, not production hosting.


## US software candidate placement office

Create a **Candidate case** with an alias and verified intake notes. This adds twelve placement roles and twelve prerequisite-gated tasks: intake, US location preferences, employer requirement mapping, profile/portfolio preparation, skills planning, linked application pipeline, campaign review, interviews, written offer review, candidate offer decision, onboarding/actual start, and post-start support. Matching existing staff are reused without overwriting their instructions. Existing application projects remain intact.

Record candidate-approved US locations, remote/hybrid/onsite and relocation preferences; nationwide coverage is a preference to confirm, not an automatically searched feed. Each employer's requirements must be checked against verified candidate facts. Unknown authorization, sponsorship, qualifications, and availability require clarification. Team roles can be edited and tasks reassigned for each employer's needs.

When creating each application, select its **Candidate case**. Separate application workflows retain CV tailoring, QA, approval, submission receipts, and status history. A candidate can have multiple linked openings. The manager sees linked application counts and handoff progress. Continue adding openings and recording next actions after rejections; the candidate case spans the whole campaign. Intake corrections can be recorded in task notes, subject to existing review/version gates.

Select the candidate in the status desk to record intake, preparing, searching, interviewing, offer received, accepted, started, paused, withdrawn, or blocked. **Accepted and Started are separate states.** Started evidence must describe the employer, role, actual start date, and candidate confirmation. Evidence is manually entered, not independently verified. Completing every task never automatically marks a person placed. Append a new status record when circumstances change; earlier records remain in the history.

API: `POST /api/candidate-project` accepts unique `name` and required `profile` (1–5000 characters). `POST /api/job-project` additionally accepts an optional integer `candidate` identifying a placement case. `/api/application-check` validates statuses against the project kind. Candidate notes and links persist in SQLite and JSON exports. Keep personal documents private and reference them locally; never commit candidate data to GitHub.

This release provides a working manual recruiting coordination system. It does not guarantee employment or automatically search all portals, submit applications, contact employers, or arrange interviews. The configured discovery worker and CV excerpt preparation described below are automated. Those require authenticated runtime integrations and actual candidate information. Browser verification covers creating a candidate, linking an opening, saving placement status, and reload persistence; service tests cover all twelve handoffs, validation, atomic rollback, API access checks, and preservation of linked cases.


## Recurring new-job discovery and CV preparation

1. Create a candidate case, then select it under **New-job recruiting campaign**.
2. Enter up to five employer board tokens (plain Greenhouse tokens or lever:company), target titles, approved US location phrases, verified skills, and an accurate plain-text master CV. Confirm candidate authorization and enable discovery.
3. Keep `python portfolio/ai-office/office.py` running. It checks due campaigns every 30 seconds, with a 15-minute interval between scans. **Check due boards now** runs due scans without bypassing this interval. Refresh the UI to see background results.
4. The first successful scan of each board records existing openings as a baseline. Only unseen job-post IDs from later scans produce queue entries. A failed first scan never establishes a baseline. Repeated scans do not duplicate a candidate/board/job ID.
5. Each new opening receives a draft containing relevant **exact CV excerpts and the complete unchanged master CV**, then a title/location/skill keyword screen. This is deterministic preparation, not AI rewriting or a finished ATS-optimized CV. Full employer requirements, authorization/sponsorship, seniority, salary, and application questions still require review.
6. Matching entries are **Blocked**, explaining the missing submission connector and review requirements. Filtered entries show reasons and remain available for inspection. No entry is marked applied and no message or application is sent. Copy an approved draft into a linked application workflow to complete the existing submission/status process.

**New means newly observed since baseline**, not a verified posting date. The public provider returns an update date rather than a reliable original posting date; an old opening newly added to a board can appear. Edits to an existing ID do not trigger another package. Deduplication is per candidate, board, and post ID, not semantic deduplication across employer boards or reposted IDs. These are stored snapshots: verify the opening is still available before acting. Only configured employers are covered, not all job sites. Location matching is literal; use specific US phrases and review ambiguous remote listings. A keyword match does not establish eligibility.

An **interviewing** candidate continues discovery. Recording **accepted, started, paused, or withdrawn** stops discovery for that candidate. Disabling the campaign also stops it. Resume by updating the candidate status and enabling the campaign; the next due cycle resumes. Acceptance stops new searching to avoid unwanted applications while onboarding, but does not mark the candidate placed. Completed tasks never control campaign status automatically.

Saving changed preferences invalidates existing blocked packages as **Needs review**; their original drafts remain for audit and are not silently overwritten. Previously filtered jobs are not automatically reconsidered. Optimistic campaign revisions prevent stale edits; changes during a network request discard that request's results. Source failures are recorded and retried next cycle. Network reads use a fixed HTTPS provider, validated board tokens, disabled redirects, timeouts, and a response-size limit. No credentials are required for public reads or stored by this feature.

API additions: `POST /api/campaign` accepts integer `candidate`, current integer `revision` (0 initially), comma-separated `boards`, `titles`, `locations`, `skills`, plain-text `resume`, boolean `enabled`, and `consent: true`. `POST /api/discover` checks due campaigns. Both use the existing local token/origin protection. Snapshots/exports now include campaigns and job records, including private CV text; keep exports private. The queue shows the newest 50 non-baseline records; exports include all records. The CLI starts the worker; importing `make_server` alone does not start background scans.

Provider reference: https://docs.greenhouse.io/job-board.html. Public job-list reads are unauthenticated. Application submission requires an employer Job Board API key and job-specific form validation; GitHub access does not provide that authorization. No automatic submission or email/status-monitoring connector is included. Tests use provider fixtures; they do not claim a real employer submission or guaranteed provider availability.


## Duplicate application protection

Job discovery deduplication alone does not prevent two differently named application projects from representing the same opening. Before submission, use **Duplicate protection** to register the candidate case, the employer's canonical domain, and its stable requisition ID. Use the same employer requisition across portals; a portal-specific posting ID may differ. The server normalizes domain case/`www.`/trailing dots and requisition Unicode/case/whitespace.

A database uniqueness constraint reserves `(candidate, employer, requisition)` for one project, inside an immediate write transaction. A second project receives HTTP 409 and the existing project ID, including for concurrent requests. Repeating the same registration on the original project is safe. Different candidates or requisitions remain permitted. Registered identities cannot be silently changed or reset after rejection/withdrawal; continue using the original project. A repeat status observation appends history to that same application, not a second application.

Existing projects remain intact. Unregistered application projects cannot start submission work or record submitted/under-review/interview/offer/rejected/withdrawn statuses until registered. Unknown, blocked, and not-applied notes remain available. Historical statuses are preserved, not retrospectively verified. The UI labels missing protection, and JSON export includes all registered identities.

API: `POST /api/application-identity` with integer `project`, integer `candidate`, `employer` domain and `requisition` reference; requires existing local write authorization. Registration links a standalone application to its candidate, but cannot move an already-linked application to another candidate.

Verification covers concurrent registration, cross-portal normalized identities, retry safety, persistence, separate candidates/requisitions, blocked legacy submission, HTTP authorization/409 responses, and browser-visible duplicate rejection. This protects records in this workspace; it cannot discover previous applications made elsewhere, resolve duplicated candidate cases/employer aliases, or identify reposted jobs with changed requisition IDs. Record previous applications against the same candidate and stable identity before proceeding. No automatic submission connector exists, so no live external application history has been audited and no real-world zero-duplicate guarantee is claimed.


## Candidate staff chat

Use **Chat with your office** to select a candidate and any staff role. Ask about status, next checks, blockers, CV work, or interviews. Optionally select one linked opening. Each reply reads current saved records in the same database transaction: candidate status, up to 20 application summaries, evidence references and checked-at timestamps, next checks, duplicate-protection blockers, and (for next-step questions) up to eight open tasks with the selected staff prioritized. Discovery counts are explicitly separate from submissions. Unsupported questions receive a records summary and supported-topic guidance, not invented advice.

This is a deterministic **automated records assistant**, not an AI model, live employee, or portal/inbox monitor. No API key is needed. Staff selections affect attribution/responsibility and task ordering; they do not create independently running people. Unknown or missing status stays unknown. Chat cannot submit applications, message employers, update statuses, or schedule interviews. Saved replies describe records at reply time and can become stale; ask again for a fresh summary.

Conversation history persists by candidate/staff, survives reload, and is included in JSON export. The UI shows the most recent 20 exchanges for the selected conversation. Replies filter linked records to the selected candidate and reject an application from another candidate. HTML is displayed as text. API: `POST /api/staff-chat` with integer `candidate`, integer `agent`, optional integer `project`, and `question` (1–2000 characters), using the local write token/origin protection.

**Access boundary:** this is still a single trusted local workspace. The candidate selector is not authentication; the operator can view all candidates and exports contain all chats. There are no separate candidate accounts, remote candidate portal, private multi-user permissions, live staff messaging, or notifications. Do not expose this server online. A secure candidate-facing service needs authentication and server-side authorization before separate candidates can access it privately.

Tests verify unknown-status handling, evidence/timestamps, candidate and application scoping, read-only application behavior, all staff roles, validation, persistence, HTTP authorization, and browser conversations with two staff roles.


## Reliability verification — October 5, 2026

The expanded suite has 66 service/HTTP tests. Additional regression coverage checks extreme timestamp conversion, oversized/negative IDs, non-ASCII write tokens, deeply nested JSON recovery, malformed discovery input, stopped campaign scan metadata, atomic rollback after a malformed job, concurrent discovery exclusion, and rejected source redirects. Invalid requests return controlled errors instead of disconnecting the client. A paused campaign no longer updates its last-scan timestamp without a source request.

During a save, form controls and board navigation are disabled to prevent edits from being silently cleared when the response arrives. Older refresh responses cannot replace state from a newer save. Browser verification checks this lock and its release, literal rendering of HTML-like chat messages, and the existing candidate, application, duplicate protection, staff chat, persistence, and mobile flows. This is functional verification using synthetic candidate data and feed fixtures; no live applications or employer inbox checks are performed.


## Staff role audit

All 30 built-in roles are covered by `test_roles.py`: assignment, reassignment, full review/completion lifecycle, persisted chat, and restart persistence. Both templates are checked stage by stage for the correct owner and dependency edges. Case-only team renames now reuse the same staff record and preserve customized instructions when new workflows are created. Chat explicitly reports the selected role’s open-task count, including zero, and staff cards identify manual execution. See [ROLE_AUDIT.md](ROLE_AUDIT.md) for each role’s scope and limits.


## Rejection review and corrective checks

See [STAFFING_PLAN.md](STAFFING_PLAN.md) for the full workflow, named responsibilities, current automation, and remaining integrations. The new panel records rejection reviews with a staff owner, reason basis (employer feedback, hypothesis, or unknown), source/reason, and corrective action. No reason is inferred automatically. Chat reports pending reviews and lesson counts.

A candidate's latest rejected application observations require review before the next template submission task can start. After reviewing them, record a corrective check for the next application against all current lessons; a newer lesson invalidates the previous check. The server enforces this in the same write transaction as task start. It does not send an application, automatically edit the CV, or verify that a human followed the instructions. Existing active tasks and factual status observations are not blocked. Reviews/checks persist and are included in private exports.

API: `POST /api/rejection-review` with integer `check_id`, integer staff `owner`, `basis`, required `reason`, and `corrective_action` (each up to 4000 characters). `POST /api/application-preflight` with integer `project`, integer `owner`, current maximum review ID for that candidate as `review_revision` (0 without lessons), and required `evidence` (up to 4000 characters). An application must have registered duplicate protection. Stale lesson revisions and duplicate reviews return 409. Both endpoints require the existing local token and origin checks. The UI shows up to 30 lessons and 10 checks; exports retain all records.


## Optional AI drafting for every staff role

Active task cards now have **Generate AI draft**. The local Ollama adapter sends the assigned role, saved task brief/notes, prerequisite results, the same candidate's configured master CV, and rejection lessons to an installed model. It saves the response as an **unverified draft**, separately from task results, status observations, and application receipts. All 30 built-in roles support this drafting interface. Submission/status roles can generate preparation instructions only; the model has no external action tools.

Install Ollama on the computer running this office and install a model suitable for that computer. Set `AI_OFFICE_MODEL` to the exact installed model name before starting:

```sh
AI_OFFICE_MODEL='your-installed-model-name' python portfolio/ai-office/office.py
```

Start a task, save its notes, and request the draft. Review its factual claims and use the existing result/review flow. Requests go only to `http://127.0.0.1:11434/api/generate`, with proxy use and redirects disabled, a 45-second socket timeout and a response-size cap. No model is bundled or downloaded automatically. A configured name does not prove the model is installed or responsive. Missing configuration/failures return an error without changing task state. Only one inference request runs at a time in this process. Inference may continue in Ollama after a client timeout; no automatic retry occurs.

Repeated requests reuse a draft only when its task version, source-context fingerprint, model, and system instructions still match. If saved task/context changes during generation, the response is discarded. Old drafts are marked with their task version and remain in exports. Unsaved notes must be saved or discarded first. Drafting does not complete tasks, approve CVs, submit applications, read email, or guarantee employment. System instructions discourage unsupported claims, but model factual accuracy is **not guaranteed**; review remains required. No self-modifying agent or automatic model training is implemented.

The adapter and all-role drafting paths are tested with fixtures, including timeout, bad output, missing configuration, duplicate generation, changed-task rejection, and candidate-context isolation. Live model quality and throughput have not been tested here because Ollama/model configuration is absent. Browser CI verifies the missing-runtime path rather than claiming real inference. Protocol: https://docs.ollama.com/api/generate.


### Draft freshness correction

AI drafts now store a SHA-256 fingerprint of their source context, model, and system instructions. A changed CV, staff instructions, prerequisites, or rejection lessons prevents reuse of an older draft, even when the task version is unchanged. Save the task to create a new version before regenerating. Legacy drafts with no fingerprint remain readable but are not trusted as current. This verifies source consistency, not the factual accuracy of model output.


## Interactive 3D office workflow

The office map uses CSS perspective and raised station cards to show ten workflow stages: intake, profile/fit, discovery, CV tailoring, quality review, apply/track, learn/retry, interview, offer/start, and candidate success. It needs no 3D library, remote asset, GPU API, or extra package. Select a station to see its purpose and staff owner; select a candidate to view recorded task counts, actual assigned staff, candidate status and pending rejection reviews. Task links filter and scroll to the existing board. The route legend explicitly shows rejection returning to fit/tailoring/QA.

With no candidate selected, the view is a blueprint, not simulated activity. Stage counts reflect saved task completion, never proof of submission, an interview, or placement. The diagram groups template tasks by their titles; custom standalone tasks are available on the board and are not automatically classified into stations. Up to 15 matching tasks appear in the stage detail. Default station leads are shown when no tasks are assigned; otherwise the actual owners are listed.

Keyboard-operable station buttons expose selection with `aria-pressed`. A flat-view toggle is available; mobile and reduced-motion layouts remove perspective automatically. The scene is a stylized 3D workflow, not a free-orbit virtual office or animated employee simulation. Browser verification covers station selection, candidate scoping, rejection details, task navigation, toggling, and mobile overflow.

## Three-department recruiting workflow

Create a candidate case, then use **Three-department recruiting office** with the original HTTPS job URL and full job description. This creates ten dependent tasks assigned to nine staff:

| Department | Staff | Output |
| --- | --- | --- |
| 01 Source jobs | Job Feed Collector; US Software Job Screener; Job Freshness and Duplicate Checker | Verified source, US software scope, posting freshness and duplicate check |
| 02 Tailor documents | CV Tailoring Team; Portfolio Tailoring Team; Cover Letter Team | Three independent drafts from verified candidate facts and the same job description |
| 03 Match, finalize & apply | Eligibility Team; Application QA Team; Submission Team | Fit review after all drafts, approved package, real submission evidence and status follow-up |

The first three 3D stations show these departments. Existing candidate cases and older application workflows remain supported. Submission still requires registered candidate/employer/requisition identity and the existing rejection-lesson checks.

This is a coordination template with optional local AI drafting, not nine autonomous portal integrations. The active discovery implementation supports configured public Greenhouse and Lever boards. It does not cover every job portal or automatically interpret all-US/all-software queries. Freshness must be verified from posting evidence; newly observed does not necessarily mean newly posted. Unknown fit or freshness should leave the task open. Task completion is an operator attestation, not automated factual validation. No external submission or inbox connector is active; keep submission tasks open until an actual permitted submission and receipt exist. Model drafts require review. No placement guarantee is offered.

## Lever job discovery

Campaign board tokens now accept `lever:company` for an employer using Lever's global public job board API. Existing plain tokens still select Greenhouse; `greenhouse:company` is an equivalent alias. Use actual employer tokens, not these placeholder examples. Up to five boards total can be configured. Source documentation: https://github.com/lever/postings-api .

Lever requests use its fixed HTTPS API host, reject redirects, and read up to ten pages of 100 postings, with a 5 MB per-response limit. Malformed responses, repeated IDs or page-limit exhaustion reject the whole source scan; partial results cannot establish a baseline. Requirements lists, work arrangement and employment type are retained in the description. No job application POST is implemented.

Each source has its own first-scan baseline and ID deduplication. Newly observed does not prove newly posted; publication date and US remote eligibility still need review. Cross-portal submission deduplication continues to require the canonical employer/requisition identity. Adapter tests use fixtures; they do not demonstrate a running live employer campaign. Existing candidate data and Greenhouse keys are preserved.

## Discovery-to-office handoff

Keyword-matched new-job queue entries now have **Create workflow from this opening**. This copies the stored candidate link, complete description, URL, source location and first-observed timestamp into the nine-staff, ten-task workflow. It never marks freshness, fit, approval or submission as verified.

A transactional source-to-project link prevents duplicate workflow creation from repeated clicks or concurrent requests. Existing links remain visible after restart. Baseline, filtered and outdated `needs_review` entries cannot be promoted; stopped candidate searches are blocked. This is source-record deduplication: cross-portal applications still require canonical employer/requisition registration before submission. No applications are sent by this action.

## Office readiness check

Use **Check AI readiness** to distinguish missing configuration, unreachable Ollama, a missing model, invalid inventory, and a locally listed model. The check uses Ollama's documented `GET /api/tags` endpoint on `127.0.0.1:11434`, disables proxies/redirects, times out after three seconds and caps the response at 250 KB. It is exposed through the office's token-protected `POST /api/readiness` route.

The check never generates text, downloads a model or changes tasks. A listed model does not prove inference works: start a task and generate a draft to verify that separately. Job source access requires a real campaign scan. Automatic submission and inbox tracking remain unconnected. API reference: https://github.com/ollama/ollama/blob/main/docs/api.md .

## Private always-on pilot

See [the Linux/Azure deployment guide](deploy/README.md) for a restricted systemd service and SSH-only access. Run `python3 verify_pilot.py` on the host to detect missing dependencies, then use `--test-model --board ACTUAL_EMPLOYER_TOKEN` for a synthetic inference and live feed checks. A successful connectivity check is not certification of staffing readiness. No VM is provisioned by these files.
