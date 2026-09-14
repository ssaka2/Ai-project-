# AI Career Desk

A C# / ASP.NET Core application for organizing IT job applications and preparing
job-specific resume drafts.

## Current features

- Email/password registration and sign-in with ASP.NET Core Identity.
- Private job records with descriptions, employer links, notes, and status filters.
- Dashboard counts and timestamped status-change history.
- Base resumes saved as plain text.
- Separate editable drafts for individual jobs.
- Immutable source-resume and job-description snapshots in each draft.
- Download saved drafts as UTF-8 text.
- SQL Server schema migrations and automated tests.

Drafts currently start as a copy of your base resume. **AI generation is not
implemented yet.** The app does not import job feeds or submit applications.

Development preview, not a deployed public release. Email confirmation/recovery,
AI integration, and production hosting remain release gates.

## Workflow

Register → save a job → save a base resume → create a draft for that job →
edit and download the draft → apply on the employer's website → update status.

Choose Applied only after submitting the application yourself.
Statuses: Saved, Applied, Interviewing, Offer, Rejected, Withdrawn.
Each actual status change records its old/new value and UTC time. Saving without
changing status creates no history entry. Repeated transitions are retained;
there is no separate application-date field yet.

Draft snapshots survive later editing or deletion of their source job/resume.
Deleting a draft removes the draft and its snapshots. Deleting a job removes
that job's status history.

## Technology

.NET 10, Razor Pages, ASP.NET Core Identity, Entity Framework Core, SQL Server,
xUnit, and GitHub Actions. AI credentials are not required for current features.

## Run locally

Install the .NET 10 SDK and provide a reachable SQL Server instance.
Windows developers may use SQL Server LocalDB. LocalDB is Windows-only.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
git checkout codex/career-desk-foundation
dotnet restore AiCareerDesk.slnx
dotnet tool restore
```

For Windows LocalDB, configure a new database:

```sh
dotnet user-secrets set "ConnectionStrings:DefaultConnection" "Server=(localdb)\\mssqllocaldb;Database=AiCareerDeskV1;Trusted_Connection=True;MultipleActiveResultSets=true" --project src/AiCareerDesk.Web
dotnet ef database update --project src/AiCareerDesk.Web
dotnet dev-certs https --trust
dotnet run --project src/AiCareerDesk.Web --launch-profile https
```

For other SQL Server installations, supply your own development connection string
through user secrets. Open https://localhost:7043 and register.

Schema changes are applied explicitly with dotnet ef database update, never at
application startup. The repository pins dotnet-ef through its local tool manifest.

### Upgrading the earlier foundation

The earlier draft used EnsureCreated with a disposable database. That switch
has been removed. Use a **new database name** for this migration-based version.
Do not run the initial migration against the old bootstrap database. If you
saved anything worth keeping, preserve that database and export the needed data
before planning a migration. No automatic deletion or conversion is performed.

## Tests

```sh
dotnet build AiCareerDesk.slnx --configuration Release
dotnet test AiCareerDesk.slnx --configuration Release
dotnet ef migrations has-pending-model-changes --project src/AiCareerDesk.Web
```

The last command requires the development connection-string configuration.
Most tests run without SQL Server. The SQL Server workflow test is explicitly
skipped unless TEST_SQL_CONNECTION points to a disposable test database.

In CI, an isolated SQL Server Developer container is started with a generated
temporary password. Tests apply and reapply migrations, register two accounts,
check real cookies/antiforgery, reject cross-account reads/writes/downloads,
verify source snapshots, and restart the application host to check persistence.
The workflow discards its container after the run.

Do not point TEST_SQL_CONNECTION at a production or personal database.
Test registration uses synthetic example.test accounts.

## Layout

| Path | Responsibility |
| --- | --- |
| src/AiCareerDesk.Web/Pages/Jobs | Job CRUD, dashboard, history |
| src/AiCareerDesk.Web/Pages/Resumes | Base resumes, drafts, snapshots, downloads |
| src/AiCareerDesk.Web/Models | Entities and validated edit inputs |
| src/AiCareerDesk.Web/Data/Migrations | Reviewed schema migration and model snapshot |
| src/AiCareerDesk.Web/Services | Owner-scoped job and resume operations |
| tests/AiCareerDesk.Web.Tests | Relational service and HTTP workflow tests |
| docs | MVP scope, backlog, and verification notes |
| .github/workflows | Build and database test automation |

## Next milestones

See [MVP scope](docs/mvp.md) and [ordered tasks](docs/backlog.md).

1. AI tailoring with a provider abstraction, truthful suggestions, and failure handling.
2. Confirmed email, password recovery, and account lifecycle checks.
3. Browser/accessibility review, deployment, backups, and production configuration.

AI drafts must preserve supplied qualifications and flag missing skills without
inventing employment, credentials, or achievements.

Google sign-in, external job feeds, PDF/DOCX import/export, reminders, and automatic
applications remain later work.

## Production readiness

Configure email delivery/confirmation, AllowedHosts, HTTPS, persistent Data
Protection keys, migration deployment, backups, and secret storage before hosting.
Email confirmation is disabled in this development preview.
Concurrent edits currently use last-write-wins; conflict detection is a backlog item.
Do not commit real resumes, credentials, or database exports or log resume bodies.

## License

No license has been selected.
