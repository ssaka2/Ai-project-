# Full-stack setup

## Start with Docker

Install Docker with Compose v2 and Linux container support, and allow at least
4 GB of memory for SQL Server and the web application. Images target linux/amd64;
ARM machines require emulation.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
git checkout codex/ai-resume-tailoring
python3 scripts/setup.py
docker compose up --build -d --wait web
```

Windows PowerShell users can replace the Python command with:
`powershell -File scripts/setup.ps1`.

Open http://localhost:8080. Register with a synthetic address such as
you@example.test, open http://localhost:8025, and follow the confirmation link
in the local inbox. Sign in, add a job, save a resume, and create an editable draft.
Password recovery messages also arrive in the inbox. Mailpit captures messages
locally; it does not deliver them to external addresses.

The setup script generates a random local database password in the ignored
.env file and keeps an existing file intact. Do not commit this file.
SQL Server and application keys persist in Docker volumes.
`docker compose down` stops the stack while keeping those volumes.
Do not add `-v` unless you intend to erase this local database and its keys.

For port conflicts, set WEB_PORT or MAILPIT_PORT in .env before starting.
The app and inbox bind to the loopback interface. This Compose file is a local
development setup, using SQL Server Developer edition and development HTTP.

## Database updates

The migrate container applies the committed EF migrations before the web
container starts. Application startup never creates or migrates the database.
After pulling changes, rebuild and recreate the stack:

```sh
docker compose down
docker compose up --build -d --wait web
```

Back up valuable data first. Databases created by the earlier EnsureCreated
prototype require a separate data migration; do not apply the initial migration
to those databases. Use a new database for that prototype upgrade.

Liveness: GET /health/live. Readiness: GET /health/ready returns 200 only when
SQL Server is reachable and all committed migrations have been applied.
Health responses contain no connection details.

## Develop with the .NET SDK

Install .NET 10 and configure a development SQL Server connection with user secrets:

```sh
dotnet restore AiCareerDesk.slnx
dotnet tool restore
dotnet user-secrets set "ConnectionStrings:DefaultConnection" "<development SQL Server connection string>" --project src/AiCareerDesk.Web
dotnet user-secrets set "Email:Enabled" "true" --project src/AiCareerDesk.Web
dotnet user-secrets set "Email:Host" "127.0.0.1" --project src/AiCareerDesk.Web
dotnet user-secrets set "Email:Port" "1025" --project src/AiCareerDesk.Web
dotnet user-secrets set "Email:Security" "None" --project src/AiCareerDesk.Web
dotnet user-secrets set "Email:FromAddress" "career@example.test" --project src/AiCareerDesk.Web
docker run --rm -d --name career-dev-mail -p 127.0.0.1:1025:1025 -p 127.0.0.1:8025:8025 axllent/mailpit:v1.27
dotnet ef database update --project src/AiCareerDesk.Web
dotnet dev-certs https --trust
dotnet run --project src/AiCareerDesk.Web --launch-profile https
```

Open https://localhost:7043. Windows LocalDB is supported as the connection
string's server; it is not available on Linux or macOS.

## Account behavior

Email confirmation is required by default. Startup rejects missing SMTP settings.
Confirmation and recovery tokens expire after one hour; successful password
reset invalidates the reset token. Five failed password attempts lock the account
for fifteen minutes. Use the resend-confirmation link if the original email fails.

Account → Personal data → Delete removes the account and its jobs, status
history, resumes, drafts, and suggestions through database cascades. Existing
backups retain their contents until the backup retention period expires.
Identity's personal-data download concerns account fields; download saved resume
drafts separately before deleting an account.

## Optional AI

AI stays disabled until you supply AI_ENABLED=true, AI_MODEL, and AI_API_KEY in
.env. Recreate the web container after changing configuration.
See [AI setup](ai-setup.md) for consent, limits, and required synthetic evaluations.
Core workflows do not require an AI key.

## Before public hosting

Use a production deployment configuration with HTTPS, an explicit AllowedHosts
list, trusted proxy configuration when applicable, a production SQL Server
edition/service, and a least-privileged application database login. Run the
migration bundle as a separate deployment task with schema permissions.

Set ASPNETCORE_ENVIRONMENT=Production. Configure Email__Enabled, Email__Host,
Email__Port, Email__FromAddress, and provider credentials Email__Username and
Email__Password through the hosting secret store. Use Email__Security=StartTls
or SslOnConnect; unencrypted SMTP is rejected in production. Do not expose Mailpit.

Persist Data Protection keys with appropriate access controls and encryption at
rest; persist the database, automate backups, and demonstrate a restore.
Keep old images and a database backup for rollback; rolling back an image does
not roll back its schema. Choose hosting and validate domain/HTTPS behavior before
opening registration publicly. Live hosting and live AI quality remain separate
release checks.
