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
python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt
python portfolio/run_tests.py
python portfolio/support-ticket-api/verify_api.py
node --test portfolio/signed-webhook-receiver/test_server.ts
node portfolio/signed-webhook-receiver/demo.ts
```

CareerDesk additionally requires the SQL Server/browser/Docker prerequisites documented in its existing setup guide. The repository's Build and test workflow provisions those dependencies. Local Python/Node tests do not replace that full integration workflow.

The projects remain local portfolio demonstrations where documented. No external deployment, identity layer for the sample APIs, or production certification is implied by this update.

## Additional agent tooling projects

MCP Knowledge Tools uses official SDK 2.2.0, with eight checks including actual stdio client calls. Ollama Request Gateway uses Node.js 24 and native TypeScript, with seven mock-backed HTTP checks for forwarding, validation, authentication, size limits, concurrency, timeouts, and circuit recovery. The two projects bring the collection to ten including CareerDesk. Actual Ollama inference requires an installed local model and is not exercised by CI. Dependabot also checks the MCP requirement weekly.
