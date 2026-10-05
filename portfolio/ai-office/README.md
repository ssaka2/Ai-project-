# AI Office

An original local workspace for planning and reviewing agent-assisted work. Built for this portfolio; no Agents Office source, assets, or branding were copied.

## Run

Requires Python 3.11 or newer. No runtime packages, build step, API key, or paid account.

```sh
python portfolio/ai-office/office.py
```

Open http://127.0.0.1:4521 on the same computer. On Windows, `py` can replace `python`.

1. Add or edit a named agent role and its instructions.
2. Create a task with a brief, assigned role, and optional scheduled start.
3. Start a due task, enter your result, and request review.
4. Review the result, then approve completion or send it back for revision.
5. Search the board or export the workspace as JSON.

Agents are **roles for manual planning**, not autonomous AI processes. You perform the work and paste results into the board. No model generation or external submission is connected. Configured Greenhouse discovery runs in the background when launched with the command above. Scheduling controls when a task can be started; it does not run a task automatically. Refresh to update scheduled availability. Times are entered in the browser's local timezone and stored in UTC.

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

Forty-two automated service/HTTP tests cover the review lifecycle, persistence after reopening the database, competing edits, timezone normalization, scheduled starts, agent changes, validation, exports, cross-origin rejection, and static assets.

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

**Execution boundary:** these are working coordination tools for manual tasks, not autonomous workers. Configured Greenhouse feeds and exact-CV-excerpt draft preparation are available below; model calls, document parsing, and external submission integrations are not connected. The workspace never submits an application or sends a message. Team instructions require actual evidence; the software cannot independently verify a pasted receipt or applicant approval. Leave blocked tasks open. Only mark submitted after completing the application on the real portal. Add your master CV and preferences locally; do not commit personal application data to the public repository.

## Application status desk

The Submission Team now has a structured status record per application, separate from task progress. Select an application, record its observed status and evidence (portal/email reference or access blocker), enter when it was checked, and optionally schedule the next check. The manager sees the latest record, full recorded history, and a **Check due** label after the next-check time. Refresh to recompute due labels; there is no background monitor or notification service.

Supported states: not applied, submitted, under review, interview, offer, rejected, withdrawn, unknown, and blocked. Evidence is mandatory; check times cannot be in the future or older than the previous check. Next check must follow the last check. Concurrent stale updates return 409. The latest record and all earlier records survive restart and are included in JSON export. Saving a record never changes task completion or performs an external submission.

Evidence is entered by the local user and is not independently verified. Use Unknown or Blocked when portal/email access cannot confirm a status. Do not place passwords or sign-in tokens in evidence. Unsaved status-form input survives ordinary board saves/refreshes but not a full browser reload; after a conflict, preserve your text, refresh, and reselect the application to load the latest revision.

### Plugin integration boundary

ChatGPT-connected plugins are available to the assistant in the conversation; they are not automatically installed, authenticated, or callable by this standalone Python application. GitHub is used for code and CI. Outlook Email could support reading receipts/status messages after connection; a document provider could supply the approved master CV. Authenticated runtime integrations, credential handling, and model execution are not implemented here; public Greenhouse discovery is supported. No plugin credentials or personal application records are committed to this public repository. Application teams and placement staff coordinate the workflow; adding roles does not connect external services.

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

Designed for one trusted local user. No accounts, TLS, public hosting, auto-refresh, task deletion, recurring task execution, model integration, or independent approver identity. Do not expose the server publicly or tunnel it to the internet. Search, board refresh, pagination, and unrelated saves preserve pending notes and assignments in memory. Reloading/closing the browser loses unsaved edits. Stale drafts retain their original version and cannot overwrite a newer task; copy their contents before using Discard local edits. The API still transfers a full task snapshot, so this is not a server-paginated solution for very large datasets. Agent edits use last-write-wins; task results use version checks. The standard-library HTTP server is for local development, not production hosting.


## US software candidate placement office

Create a **Candidate case** with an alias and verified intake notes. This adds twelve placement roles and twelve prerequisite-gated tasks: intake, US location preferences, employer requirement mapping, profile/portfolio preparation, skills planning, linked application pipeline, campaign review, interviews, written offer review, candidate offer decision, onboarding/actual start, and post-start support. Matching existing staff are reused without overwriting their instructions. Existing application projects remain intact.

Record candidate-approved US locations, remote/hybrid/onsite and relocation preferences; nationwide coverage is a preference to confirm, not an automatically searched feed. Each employer's requirements must be checked against verified candidate facts. Unknown authorization, sponsorship, qualifications, and availability require clarification. Team roles can be edited and tasks reassigned for each employer's needs.

When creating each application, select its **Candidate case**. Separate application workflows retain CV tailoring, QA, approval, submission receipts, and status history. A candidate can have multiple linked openings. The manager sees linked application counts and handoff progress. Continue adding openings and recording next actions after rejections; the candidate case spans the whole campaign. Intake corrections can be recorded in task notes, subject to existing review/version gates.

Select the candidate in the status desk to record intake, preparing, searching, interviewing, offer received, accepted, started, paused, withdrawn, or blocked. **Accepted and Started are separate states.** Started evidence must describe the employer, role, actual start date, and candidate confirmation. Evidence is manually entered, not independently verified. Completing every task never automatically marks a person placed. Append a new status record when circumstances change; earlier records remain in the history.

API: `POST /api/candidate-project` accepts unique `name` and required `profile` (1–5000 characters). `POST /api/job-project` additionally accepts an optional integer `candidate` identifying a placement case. `/api/application-check` validates statuses against the project kind. Candidate notes and links persist in SQLite and JSON exports. Keep personal documents private and reference them locally; never commit candidate data to GitHub.

This release provides a working manual recruiting coordination system. It does not guarantee employment or automatically search all portals, submit applications, contact employers, or arrange interviews. The configured discovery worker and CV excerpt preparation described below are automated. Those require authenticated runtime integrations and actual candidate information. Browser verification covers creating a candidate, linking an opening, saving placement status, and reload persistence; service tests cover all twelve handoffs, validation, atomic rollback, API access checks, and preservation of linked cases.


## Recurring new-job discovery and CV preparation

1. Create a candidate case, then select it under **New-job recruiting campaign**.
2. Enter up to five employer Greenhouse board tokens (from their careers board URLs), target titles, approved US location phrases, verified skills, and an accurate plain-text master CV. Confirm candidate authorization and enable discovery.
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
