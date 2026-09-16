# AI Career Desk

A full-stack C# / ASP.NET Core application for organizing IT job applications
and preparing job-specific resume drafts.

## Portfolio projects

Explore two additional runnable projects in the [software engineering portfolio](portfolio/README.md):

- [Inventory Ledger](portfolio/inventory-ledger/) — transaction-safe stock movements, audit history, and retry protection.
- [Airport Operations Analytics](portfolio/airport-analytics/) — validated CSV ingestion, repeatable SQL loads, and airport performance reports.

Both include automated tests, synthetic examples, and documented design decisions.

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
