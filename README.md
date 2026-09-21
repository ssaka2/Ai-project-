# Sai Sandeep Saka · Software Engineering Portfolio

**Backend applications, reliable data workflows, and practical AI tooling.**

[![CareerDesk build](https://github.com/ssaka2/Ai-project-/actions/workflows/ci.yml/badge.svg)](https://github.com/ssaka2/Ai-project-/actions/workflows/ci.yml)
[![Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml/badge.svg)](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml)

[Explore all 12 projects](portfolio/README.md) · [Run CareerDesk](#start-the-full-stack) · [Verification details](docs/technology-review.md)

| Start with | What it demonstrates |
| --- | --- |
| **AI CareerDesk** | C# / ASP.NET Core, EF Core, SQL Server, private job tracking, and resume workflows |
| **[MCP Knowledge Tools](portfolio/mcp-knowledge-tools/)** | Python agent tools, source citations, document snapshots, and actual MCP protocol tests |
| **[Ollama Request Gateway](portfolio/ollama-request-gateway/)** | TypeScript / Node.js, request cancellation, timeouts, concurrency limits, and circuit recovery |

**Technology in this repository:** C# · .NET 10 · SQL Server · Python · SQLite · TypeScript · Node.js 24 · MCP · Docker · GitHub Actions · Playwright

The root application is **AI CareerDesk**, a full-stack application for organizing IT job applications and preparing job-specific resume drafts. Eleven independent projects live in `portfolio/`.

## Portfolio projects

Explore eleven additional runnable projects in the [software engineering portfolio](portfolio/README.md):

- [Inventory Ledger](portfolio/inventory-ledger/) — transaction-safe stock movements, audit history, and retry protection.
- [Airport Operations Analytics](portfolio/airport-analytics/) — validated CSV ingestion, repeatable SQL loads, and airport performance reports.
- [Local Knowledge Search](portfolio/local-knowledge-search/) — offline BM25 retrieval with source citations and relevance checks.
- [Agent Evaluation Lab](portfolio/agent-evaluation-lab/) — recorded AI response grading, baseline regression gates, and HTML reports.
- [Support Ticket API](portfolio/support-ticket-api/) — C# REST API with persistent status history and stale-edit protection.
- [Durable Job Queue](portfolio/durable-job-queue/) — restart-safe jobs, worker leases, retry backoff, and dead letters.
- [Signed Webhook Receiver](portfolio/signed-webhook-receiver/) — Node.js 24 and TypeScript, signed requests, bounded replay protection, and HTTP tests.

- [MCP Knowledge Tools](portfolio/mcp-knowledge-tools/) — official MCP SDK, read-only document tools, citations, and stdio integration tests.
- [Ollama Request Gateway](portfolio/ollama-request-gateway/) — local model adapter with deadlines, overload protection, and circuit recovery.

- [AI Response Contract Lab](portfolio/ai-response-contract-lab/) — strict structured-output validation and a local Ollama adapter.
- [Agent Memory Store](portfolio/agent-memory-store/) — persistent context with provenance, expiration, and namespace filtering.

All eleven include automated tests, synthetic examples, and documented design decisions.
Install the MCP dependency with `python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt -r portfolio/ai-response-contract-lab/requirements.txt`. Run the Python portfolio tests with `python portfolio/run_tests.py`, and the C# API integration checks with `python portfolio/support-ticket-api/verify_api.py`.

See the [technology review and verification commands](docs/technology-review.md) for current runtime coverage and fixes.

## What you can do

- Register, confirm email, sign in, recover a password, and delete your account.
- Keep private job records with descriptions, links, notes, and status filters.
- Track dashboard counts and timestamped status changes.
- Save base resumes, create independent job-specific drafts, and download text.
- Preserve original resume/job snapshots even after editing or deleting sources.
- Optionally generate AI suggestions and skill gaps, then review before applying.
- Receive a conflict message when another session has changed a record you are editing or deleting.
- Export your account details, jobs, history, resumes, drafts, and suggestions as JSON.

AI is disabled by default. Core tracking and editing work without an API key.
The app does not import job feeds or submit applications.

## Start the full stack

Install Docker with Compose v2 and Linux container support.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
git checkout main
python3 scripts/setup.py
docker compose up --build -d --wait web
```

On Windows, replace the Python command with
`powershell -File scripts/setup.ps1`.

Open http://localhost:8080. Register with a test address, then open the
confirmation email in the local inbox at http://localhost:8025.
Sign in → save a job → save a base resume → create, edit, and download a draft.

SQL Server, the web app, migrations, and a local SMTP inbox run together.
Database data and application keys persist across restarts.
See [full setup and production configuration](docs/full-stack-setup.md)
for .NET SDK development, ports, updates, and account behavior.

For the free Azure target, start with the [read-only deployment diagnostics](docs/azure-free-deployment.md).
For Railway, see [deployment configuration and required service settings](docs/railway-deployment.md).

This is a runnable development version. Public hosting and live AI evaluation
remain release work.

## Workflow details

Choose Applied only after submitting the application yourself.
Statuses: Saved, Applied, Interviewing, Offer, Rejected, Withdrawn.
Actual status changes record their old/new value and UTC time in the same database
transaction. Saving without a status change adds no event.

Drafts start as copies of base resumes. AI suggestions remain separate until
accepted. Jobs, base resumes, drafts, and AI acceptance detect stale edits and
preserve submitted text for comparison. Open the latest record and transfer the
edits you want to keep after a conflict.

Deleting a source job or resume preserves existing draft snapshots.
Deleting a draft removes its snapshots and suggestions.
Deleting an account removes its associated records.

## Technology and structure

.NET 10, Razor Pages, Identity, EF Core, SQL Server, MailKit, xUnit,
Playwright, Docker Compose, and GitHub Actions.

| Path | Responsibility |
| --- | --- |
| src/AiCareerDesk.Web/Pages | Dashboard, jobs, resumes, drafts, review UI |
| src/AiCareerDesk.Web/Areas/Identity | Account pages and sign-in behavior |
| src/AiCareerDesk.Web/Models | Entities and validated inputs |
| src/AiCareerDesk.Web/Data | DbContext, design-time factory, migrations |
| src/AiCareerDesk.Web/Services | Owner-scoped operations, AI, SMTP |
| tests/AiCareerDesk.Web.Tests | Service, SQL Server, HTTP, Chromium tests |
| Dockerfile, compose.yaml | Local full-stack deployment |
| scripts | Local configuration setup |
| docs | Scope, setup, backlog, verification |
| .github/workflows | Build, audit, test, deployment checks |

## Verification

```sh
dotnet restore AiCareerDesk.slnx
dotnet tool restore
dotnet build AiCareerDesk.slnx --configuration Release
dotnet test AiCareerDesk.slnx --configuration Release
dotnet ef migrations has-pending-model-changes --project src/AiCareerDesk.Web
```

SQL tests require TEST_SQL_CONNECTION pointing to a disposable SQL Server database.
Browser tests additionally require RUN_BROWSER_TESTS=true, Chromium, Firefox, and WebKit installed
with the built test project's playwright.ps1 script, and Mailpit on ports
1025/8025. These tests are explicitly skipped when their prerequisites are absent.

CI provisions these dependencies, runs all tests, checks package advisories and
committed migrations, then builds and restarts the Docker stack.
See [verification results and limits](docs/verification.md).
Only use synthetic test data in disposable databases.

## Remaining milestones

1. Configure and evaluate the [optional AI provider](docs/ai-setup.md).
2. Complete manual keyboard/screen-reader review.
3. Deploy with production HTTPS/SMTP/SQL, protected persistent keys, and tested backups.

See [MVP scope](docs/mvp.md) and [implementation tasks](docs/backlog.md).
Google sign-in, feeds, PDF/DOCX processing, reminders, and automatic applications
are outside this version.

## License

No license has been selected.

