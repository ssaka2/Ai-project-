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

Agents are **roles for manual planning**, not autonomous AI processes. You perform the work and paste results into the board. No model generation, external tools, or background execution is connected. Scheduling controls when a task can be started; it does not run a task automatically. Refresh to update scheduled availability. Times are entered in the browser's local timezone and stored in UTC.

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

Fifteen automated service/HTTP tests cover the review lifecycle, persistence after reopening the database, competing edits, timezone normalization, scheduled starts, agent changes, validation, exports, cross-origin rejection, and static assets.

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
| Follow-up | Response or next follow-up plan | Submission |
| Applications Manager | Final application report | Follow-up |

The server enforces these prerequisites. Reopening an input is blocked if dependent work has already started; reopen dependent tasks in reverse order first. Duplicate project names are rejected case-insensitively. Task completion, reassignment, notes, and project history survive restart.

**Execution boundary:** these are working coordination tools for manual tasks, not autonomous workers. There are no job-portal feeds, model calls, CV parsing/generation, or external submission integrations. The workspace never submits an application or sends a message. Team instructions require actual evidence; the software cannot independently verify a pasted receipt or applicant approval. Leave blocked tasks open. Only mark submitted after completing the application on the real portal. Add your master CV and preferences locally; do not commit personal application data to the public repository.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/state` | Workspace plus ephemeral write token |
| GET | `/api/export` | JSON snapshot without the token |
| POST | `/api/job-project` | Create a project from a unique `name`, its team roster, tasks, and handoffs atomically |
| POST | `/api/agents` | Create role; include `id` to edit |
| POST | `/api/tasks` | Create `title`, `brief`, integer `agent`, optional ISO `due` with timezone |
| POST | `/api/update` | Update task using integer `id`, current `version`, `status`, optional `result`, and optional integer `agent` |

POST requests require JSON and the `X-Office-Token` from `/api/state`. Stale versions return 409; invalid input returns 400. A result is required for review/completion, and queued tasks cannot skip straight to done. Approval is a workflow step for one local user, not independent reviewer authentication.

## Limits

Designed for one trusted local user. No accounts, TLS, public hosting, auto-refresh, task deletion, recurring schedules, model integration, or independent approver identity. Do not expose the server publicly or tunnel it to the internet. Search, board refresh, pagination, and unrelated saves preserve pending notes and assignments in memory. Reloading/closing the browser loses unsaved edits. Stale drafts retain their original version and cannot overwrite a newer task; copy their contents before using Discard local edits. The API still transfers a full task snapshot, so this is not a server-paginated solution for very large datasets. Agent edits use last-write-wins; task results use version checks. The standard-library HTTP server is for local development, not production hosting.
