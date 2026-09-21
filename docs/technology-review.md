# Portfolio technology review — September 21, 2026

This update covers the repository's seven existing projects and adds one new TypeScript project. It addresses reproducible problems and extends automated verification; it is not a claim that every possible defect has been eliminated.

| Project | Review outcome / update |
| --- | --- |
| AI CareerDesk | Retained .NET 10 and Microsoft packages 10.0.12; upgraded workflow actions; re-run compilation, migration checks, advisory scan, SQL/browser tests, and Docker checks |
| Inventory Ledger | Consistent SKU trimming for movements/history; reject fractional, boolean, or oversized reorder points |
| Airport Analytics | Strict CSV parsing; preserve committed data on malformed files; report physical source lines correctly after multiline records |
| Agent Evaluation Lab | Reject duplicate JSON field names instead of silently replacing grading data |
| Local Knowledge Search | Search/evaluation fail clearly when the index file is missing; no accidental empty database is created |
| Durable Job Queue | Added token-checked renewal for unexpired leases, including protection against shortening a lease |
| Support Ticket API | Revalidated .NET 10 build, concurrent-update handling, and persisted data after restart using upgraded workflow actions |
| Signed Webhook Receiver | New Node.js 24/TypeScript project with raw-body HMAC checks, bounded replay handling, and HTTP tests |

## Runtime and maintenance choices

- .NET 10 is an active LTS release. The repository's existing 10.0.12 Microsoft packages match the [current Microsoft support table](https://dotnet.microsoft.com/en-us/platform/support/policy/dotnet-core) at review time. No package downgrade or prerelease framework migration is introduced.
- Python CI now covers 3.11, 3.12, 3.13, and 3.14. See [Python releases](https://www.python.org/downloads/).
- The new service targets Node.js 24 LTS; see the [Node release table](https://nodejs.org/en/about/previous-releases).
- Workflows use the action maintainers' documented major versions: checkout 7, setup-python 7, setup-dotnet 6, setup-node 7, and upload-artifact 7. Action updates are tested on a branch before publication.
- Dependabot is configured to check NuGet and GitHub Actions weekly and propose update pull requests. This configuration does not enable automatic merging, and it does not verify future updates before their CI runs.

## Reproduce verification

```sh
python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt -r portfolio/ai-response-contract-lab/requirements.txt
python portfolio/run_tests.py
python portfolio/support-ticket-api/verify_api.py
node --test portfolio/signed-webhook-receiver/test_server.ts
node portfolio/signed-webhook-receiver/demo.ts
```

CareerDesk additionally requires the SQL Server/browser/Docker prerequisites documented in its existing setup guide. The repository's Build and test workflow provisions those dependencies. Local Python/Node tests do not replace that full integration workflow.

The projects remain local portfolio demonstrations where documented. No external deployment, identity layer for the sample APIs, or production certification is implied by this update.

## Additional agent tooling projects

MCP Knowledge Tools uses official SDK 2.2.0, with eight checks including actual stdio client calls. Ollama Request Gateway uses Node.js 24 and native TypeScript, with seven mock-backed HTTP checks for forwarding, validation, authentication, size limits, concurrency, timeouts, and circuit recovery. The two projects bring the collection to ten including CareerDesk. Actual Ollama inference requires an installed local model and is not exercised by CI. Dependabot also checks the MCP requirement weekly.

## Follow-up verification and upgrades

Reviewed the ten-project collection and current open dependency proposals. Updated the test toolchain together: Microsoft.Playwright 1.56.0 → 1.62.0, Microsoft.NET.Test.Sdk 17.14.1 → 18.10.1, and xunit.runner.visualstudio 3.1.1 → 4.0.0. These match the three pending Dependabot proposals at review time; this is not a claim that every dependency is the newest published version.

The Ollama gateway now aborts its upstream HTTP request when its caller disconnects, releases capacity, and excludes caller cancellation from circuit-breaker failures. Its eighth test verifies prompt cancellation and a successful subsequent request. The model server controls whether computation itself stops. Python CI additionally checks installed dependency compatibility with `pip check`.

Verification covers 59 Python tests across six projects, 16 TypeScript HTTP tests, the C# ticket API checks, and CareerDesk's build, migrations, dependency advisory audit, service/SQL/browser tests, and Docker restart checks. CI is the authority for the upgraded .NET toolchain. Live cloud deployments, Gmail/Google OAuth credentials, paid AI APIs, and actual local Ollama inference are outside these fixture-backed checks.

Version references: [Playwright package](https://www.nuget.org/packages/Microsoft.Playwright/1.62.0), [.NET test SDK](https://www.nuget.org/packages/Microsoft.NET.Test.Sdk/18.10.1), [xUnit adapter release notes](https://xunit.net/releases/visualstudio/4.0.0).

## Current dependency review — twelve projects

Checked the package registries and upstream release APIs on September 21, 2026. No open dependency update PRs remained. MCP 2.2.0, jsonschema 4.26.0, MailKit 4.18.0, Microsoft packages and dotnet-ef 10.0.12, Playwright 1.62.0, .NET Test SDK 18.10.1, xunit 2.9.3, and the Visual Studio adapter 4.0.0 match the stable versions returned by their registries. The existing GitHub Actions major tags already track the current supported release majors.

Updated the local SMTP test inbox from Mailpit v1.27 to [v1.31.2](https://github.com/axllent/mailpit/releases/tag/v1.31.2) in both Docker Compose and CI. The exact patch tag keeps both environments consistent. The full workflow verifies email confirmation and password recovery against this version, plus Docker readiness and restart.

The collection now includes AI Response Contract Lab and Agent Memory Store: twelve projects, with 73 Python tests across eight suites, 16 TypeScript tests, 13 ticket API checks, and 66 CareerDesk tests. The earlier sections record prior updates and their counts at that time. Actual model inference and production deployments still require separate verification.
