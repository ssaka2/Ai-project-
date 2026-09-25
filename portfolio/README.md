# Software engineering portfolio

19 projects in one repository, covering backend services, relational data, document retrieval, AI evaluation, browser interfaces, and systems tooling. CareerDesk lives at the root; the other 18 projects have their own folders below. Bundled examples use synthetic data and can run locally without paid services.

[Open the live Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) · [Download built projects](#download-built-projects) · [Local setup](#quick-start)

[![Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml/badge.svg)](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml)

| Project | Stack | Engineering focus |
| --- | --- | --- |
| [AI Career Desk](../README.md) | C#, ASP.NET Core, EF Core, SQL Server | Account isolation, resume workflows, application tracking |
| [Inventory Ledger](inventory-ledger/) | Python, SQLite, SQL | Atomic updates, idempotent requests, concurrent writers |
| [Airport Analytics](airport-analytics/) | Python, CSV, SQLite, SQL | Validated ingestion, repeatable loads, operational metrics |
| [Local Knowledge Search](local-knowledge-search/) | Python, SQLite FTS5, BM25 | Offline retrieval, source citations, relevance evaluation |
| [Agent Evaluation Lab](agent-evaluation-lab/) | Python, JSONL, HTML | Response/trace checks, budget limits, regression gates |
| [Support Ticket API](support-ticket-api/) | C#, .NET 10, ASP.NET Core | REST endpoints, optimistic concurrency, persistent history |
| [Durable Job Queue](durable-job-queue/) | Python, SQLite | Worker leases, retries, idempotency, dead letters |
| [Signed Webhook Receiver](signed-webhook-receiver/) | TypeScript, Node.js 24, HMAC | Signature verification, replay protection, bounded request handling |
| [MCP Knowledge Tools](mcp-knowledge-tools/) | Python, MCP SDK 2.2 | Read-only tools, structured results, resources, stdio |
| [Ollama Request Gateway](ollama-request-gateway/) | TypeScript, Node.js 24 | Local inference adapter, deadlines, concurrency, circuit breaker |
| [AI Response Contract Lab](ai-response-contract-lab/) | Python, JSON Schema, Ollama | Model contracts, response validation, HTTP adapter |
| [Agent Memory Store](agent-memory-store/) | Python, SQLite | Persistent context, provenance, expiration, lexical recall |
| [AI Engineering Web Lab](ai-engineering-web-lab/) | JavaScript, static hosting | Interactive recorded-response checks and downloadable reports |
| [Go Health Probe](go-health-probe/) | Go 1.27, HTTP | Bounded concurrency, deadlines, cancellation, race tests |
| [Rust Log Metrics](rust-log-metrics/) | Rust 1.98.1 | Validated TSV ingestion, error rates, p95 latency, release binary |
| [Appointment Booking Web API](booking-web-api/) | ASP.NET Core, JavaScript, Python client | REST service, browser UI, concurrent booking protection, persistence |
| [Cloud VPN Management Web API](cloud-vpn-api/) | Python, SQLite, Docker, WireGuard | Authenticated peer registry, configuration export, tunnel and revocation checks |
| [Agent Approval Queue](agent-approval-queue/) | Python, SQLite | Human-review state, exact argument binding, expiry, atomic consumption |
| [OpenTelemetry Trace Inspector](otel-trace-inspector/) | TypeScript, Node.js 24, OTLP/JSON | Nanosecond precision, trace relationships, p95 and error reports |

## Download built projects

Open [Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml), choose a successful run on **main**, and scroll to **Artifacts**. GitHub sign-in may be required. These are workflow downloads, not GitHub Releases.

| Artifact | Contents | Runtime or platform |
| --- | --- | --- |
| `booking-web-api-release` | Booking API, browser assets, Python client, and run instructions | ASP.NET Core Runtime 10; tested on Linux |
| `go-health-probe-linux` | Compiled health-check command | Linux x64 |
| `rust-log-metrics-linux` | Compiled log analysis command | Linux x64 |
| `agent-evaluation-python-3.13` | Sample evaluation reports | Browser or text editor |
| `booking-browser-results` | Browser screenshots, traces, and server log | Screenshots open directly; traces use Playwright |

Extract an artifact before use. The booking package expires after 30 days; browser evidence expires after 14 days. Pick a newer successful run if an older download has expired. Follow the project README for startup commands and prerequisites; the booking package includes its README.

The [Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) is the publicly hosted browser demo. Downloading these other artifacts does not deploy a public service.

## Quick start

Install Python 3.11 or newer. Eight Python projects use only the standard library; MCP Knowledge Tools additionally requires the pinned MCP SDK. AI Response Contract Lab requires the pinned jsonschema dependency. Support Ticket API additionally requires the .NET 10 SDK. Knowledge Search also requires SQLite built with FTS5, which is verified by its tests.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt -r portfolio/ai-response-contract-lab/requirements.txt
python portfolio/run_tests.py
python portfolio/airport-analytics/pipeline.py portfolio/airport-analytics/sample_flights.csv --db :memory:
```

These commands verify local projects; GitHub repository links do not launch a hosted application. To run CareerDesk in a browser, follow the [Docker setup](../README.md#start-the-full-stack) and open `http://localhost:8080` on the same computer.

Run the C# API integration checks separately:

```sh
python portfolio/support-ticket-api/verify_api.py
python portfolio/booking-web-api/verify_api.py
```

Both require the .NET 10 SDK. Booking also has [cross-browser verification instructions](booking-web-api/#browser-verification).

The webhook project requires Node.js 24. Run `node --test portfolio/signed-webhook-receiver/test_server.ts`.

Each project has its own entry point, test suite, setup instructions, design decisions, and limitations. They can be extracted into separate repositories without depending on CareerDesk.

## Review guide

- Inventory: follow `move()` from request validation to the database transaction; inspect the concurrent-sales test.
- Analytics: inspect `validate()`, the upsert, and `report.sql`; compare cancellation and on-time denominators.
- CareerDesk: review owner-scoped services and SQL Server integration tests.
- Knowledge Search: inspect snapshot replacement, line citations, literal query handling, and ranking evaluation.
- Evaluation Lab: compare the synthetic baseline and candidate, then inspect case-level regressions and the HTML report.

## Current AI engineering themes

The retrieval and evaluation projects demonstrate retrieval and agent evaluation, motivated by [contextual retrieval engineering](https://www.anthropic.com/engineering/contextual-retrieval) and [agent evaluation practices published in January 2026](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). These are topic choices, not a claim that these repositories appear on GitHub Trending.

The portfolio workflow tests all ten Python projects on Python 3.11, 3.12, 3.13, and 3.14 and publishes downloadable example evaluation reports as workflow artifacts. A separate job builds the Support Ticket API and runs 13 HTTP integration checks. AI CareerDesk has its own .NET/SQL Server/browser/Docker workflow.

These are portfolio demonstrations. No production use, performance benchmarks, or business impact is claimed. No license has been selected; the parent repository's licensing status applies.

MCP Knowledge Tools and Ollama Request Gateway add agent tool integration and local inference infrastructure, inspired by current agent-development themes on [GitHub Trending](https://github.com/trending) (reviewed September 21, 2026). Run the gateway checks with `node --test portfolio/ollama-request-gateway/test_gateway.ts`. Its CI uses a mock endpoint; real generation requires a separately installed Ollama model. Both TypeScript projects have dedicated Node.js 24 CI jobs.

Additional AI projects cover structured outputs and persistent agent memory. Both have runnable demos and automated tests. Contract Lab validates a synthetic response by default; optional Ollama generation requires a separately installed model. See each README for commands and limits.

Go Health Probe and Rust Log Metrics add compiled backend and systems tooling. Their CI jobs build Linux executables, run real local demos, and publish downloadable artifacts. Each README includes local build instructions. These are two more project folders in the same repository, not separate repositories or hosted services.
