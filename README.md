# AI Career Desk

A C# / ASP.NET Core application for saving IT opportunities and tracking applications.
Resume tailoring is planned; it is not implemented yet.

## Status

Development foundation. This branch adds a Razor Pages application, Identity accounts,
SQL Server configuration, private job CRUD, status filters, dashboard counts, and tests.

This is not yet a deployed or production-ready release. See [MVP scope](docs/mvp.md)
and the [implementation backlog](docs/backlog.md) for release gates.

## Current workflow

Register → sign in → save a job description and employer URL → update status and notes.

Each account owns its job records. Users must confirm that they submitted an application
before selecting Applied. The app does not submit applications or import live job feeds.

Statuses: Saved, Applied, Interviewing, Offer, Rejected, Withdrawn.
Current status and last-updated time are stored; full status history is planned.

## Technology

- .NET 10 / ASP.NET Core Razor Pages
- ASP.NET Core Identity with email/password accounts
- Entity Framework Core with SQL Server
- xUnit and SQLite for relational service tests
- GitHub Actions for build and test checks

## Run locally

Prerequisites: .NET 10 SDK and a reachable SQL Server instance.
Windows developers can use SQL Server LocalDB. macOS/Linux developers need a
reachable SQL Server instance; LocalDB is Windows-only.

Clone and select the implementation branch:

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
git checkout codex/career-desk-foundation
dotnet restore AiCareerDesk.slnx
```

Configure a **new, disposable development database**. For Windows LocalDB:

```sh
dotnet user-secrets set "ConnectionStrings:DefaultConnection" "Server=(localdb)\\mssqllocaldb;Database=AiCareerDeskDev;Trusted_Connection=True;MultipleActiveResultSets=true" --project src/AiCareerDesk.Web
dotnet user-secrets set "Database:InitializeDevelopmentDatabase" "true" --project src/AiCareerDesk.Web
dotnet dev-certs https --trust
dotnet run --project src/AiCareerDesk.Web --launch-profile https
```

For another SQL Server, set DefaultConnection to your own development connection
string through user secrets. Do not commit credentials. Open https://localhost:7043,
register, and select My jobs.

Development initialization uses EF Core EnsureCreated only when explicitly enabled
and the environment is Development. It creates the initial schema, but does not
update existing schemas. No migration history is committed yet. Before keeping
real data or deploying, replace this bootstrap with reviewed migrations and a
fresh database; do not mix EnsureCreated with migrations on the same database.

Email delivery and confirmation are not configured. Use synthetic test accounts
and data for now. Google sign-in and AI generation are not available.

## Build and tests

```sh
dotnet build AiCareerDesk.slnx --configuration Release
dotnet test AiCareerDesk.slnx --configuration Release
```

Tests cover ownership isolation, persistence across database contexts, status filters,
unsafe application URLs, public page rendering, sign-in redirects, and antiforgery
rejection. Service tests use SQLite and do not prove SQL Server compatibility.
A SQL Server and browser smoke test is a remaining release gate.

## Layout

| Path | Responsibility |
| --- | --- |
| src/AiCareerDesk.Web/Pages | Razor Pages and shared layout |
| src/AiCareerDesk.Web/Models | Job entity and validated edit input |
| src/AiCareerDesk.Web/Data | Identity and application database context |
| src/AiCareerDesk.Web/Services | Owner-scoped job operations |
| src/AiCareerDesk.Web/wwwroot | Responsive styles |
| tests/AiCareerDesk.Web.Tests | Service and HTTP tests |
| docs | Scope, milestones, and implementation tasks |
| .github/workflows | Build and test automation |

## Planned v0.1

- Reviewed migrations and SQL Server integration checks
- Status history
- Base resumes and separate tailored drafts
- AI tailoring with skill gaps, review, and failure handling
- Email confirmation and account recovery
- Deployment and a two-account acceptance check

AI-generated content must preserve supplied qualifications and flag missing skills.
It must never invent employment, credentials, or achievements.

Automatic job feeds, Google sign-in, document import/export, reminders, and
application automation are later work.

## Deployment gate

Configure migrations, email delivery/confirmation, HTTPS, AllowedHosts, persistent
Data Protection keys, database backups, and secret storage before hosting for users.
Do not log resume contents or commit real resumes/database exports.

## License

No license has been selected.
