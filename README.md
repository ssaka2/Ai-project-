<div align="center">

# Sai Sandeep Saka
### Backend engineering · Data systems · Practical AI tooling

C# and ASP.NET Core applications, dependable services, and tools that make AI workflows easier to inspect.

[Explore 19 projects](portfolio/README.md) · [Try the Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) · [Run CareerDesk](#start-the-full-stack) · [Verification report](docs/vm-verification-2026-10-02.md)

[![CareerDesk build](https://github.com/ssaka2/Ai-project-/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ssaka2/Ai-project-/actions/workflows/ci.yml)
[![Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml/badge.svg?branch=main)](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml)

</div>

---

## Featured engineering

| Project | What it demonstrates | Stack |
| --- | --- | --- |
| **[AI CareerDesk](#start-the-full-stack)** | Private application tracking, resume drafts, account isolation, real database and browser tests | C# · ASP.NET Core · SQL Server |
| **[Appointment Booking API](portfolio/booking-web-api/)** | Browser workflows, concurrent booking protection, restart persistence | .NET · JavaScript · Playwright |
| **[MCP Knowledge Tools](portfolio/mcp-knowledge-tools/)** | Read-only agent tools, document snapshots, source citations, protocol tests | Python · MCP |
| **[Cloud VPN API](portfolio/cloud-vpn-api/)** | Authenticated peer management, container persistence, tested WireGuard revocation | Python · Docker · WireGuard |
| **[OpenTelemetry Trace Inspector](portfolio/otel-trace-inspector/)** | Trace relationships, exact timestamp arithmetic, error and latency reports | TypeScript · Node.js |
| **[Go Health Probe](portfolio/go-health-probe/)** | Bounded concurrency, cancellation, HTTP deadlines and race tests | Go |

## Choose your route

| Interested in | Start here |
| --- | --- |
| Reviewing my work | [Five-minute project guide](docs/project-guide.md) |
| Running something immediately | [Browser Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) |
| Backend and database engineering | [CareerDesk setup](#start-the-full-stack) · [Inventory Ledger](portfolio/inventory-ledger/) · [Durable Job Queue](portfolio/durable-job-queue/) |
| AI and agent infrastructure | [Evaluation Lab](portfolio/agent-evaluation-lab/) · [Approval Queue](portfolio/agent-approval-queue/) · [Ollama Gateway](portfolio/ollama-request-gateway/) |
| Finding every project or a ready-built package | [Complete catalog](portfolio/README.md) · [Build downloads](portfolio/README.md#download-built-projects) |
| Running on a development VM | [Setup and commands](docs/portfolio-vm.md) · [Recorded verification](docs/vm-verification-2026-10-02.md) |

**19 projects, one repository.** CareerDesk is the root application; 18 independent projects live in `portfolio/`. The Web Lab is a public browser demo. Other applications run locally or on a configured development VM.

**Engineering focus:** ownership boundaries · transactions · idempotency · concurrency · recovery · observable behavior.

**Technology:** C# / .NET 10 · SQL Server · Python · SQLite · TypeScript / Node.js 24 · Go · Rust · Docker · GitHub Actions · Playwright.

## External projects to explore

- **[Agents Office](https://github.com/ajsahni/agents-office)** — an independent project by AJ Sahni / Sahni.ai. Follow the upstream README for installation and usage.
- **[Agents Office license](https://github.com/ajsahni/agents-office/blob/main/LICENSE)** — PolyForm Noncommercial 1.0.0 with Sahni.ai additional terms.

This is an external reference, not an original portfolio project or an included dependency. Agents Office is not bundled, integrated, deployed, or tested by this repository. Its additional terms restrict rebranding and bundling with another product or system.

## Evidence you can inspect

- [Application CI](.github/workflows/ci.yml) builds CareerDesk, audits dependencies, runs SQL and browser tests, and verifies Docker restart.
- [Portfolio CI](.github/workflows/portfolio.yml) tests Python 3.11–3.14 and the .NET, Node.js, Go, Rust, and VPN projects.
- [VM verification](docs/vm-verification-2026-10-02.md) records 66/66 CareerDesk tests, four booking browser configurations, and container/tunnel checks against a specific commit.
- Every project documents setup and limits. Synthetic examples work without paid model APIs; real Ollama inference needs a separately installed model.

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
| tests/AiCareerDesk.Web.Tests | Service, SQL Server, HTTP, Chromium/Firefox/WebKit tests |
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

