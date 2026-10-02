# A five-minute tour

[Portfolio home](../README.md) · [All 19 projects](../portfolio/README.md)

Start with the area closest to your interests. Each link leads to runnable code and project-specific instructions.

| Area | Read first | Look for |
| --- | --- | --- |
| .NET application engineering | [CareerDesk services](../src/AiCareerDesk.Web/Services/) and [tests](../tests/AiCareerDesk.Web.Tests/) | Owner-scoped queries, concurrency conflicts, preserved resume snapshots, SQL and browser verification |
| API design | [Booking API](../portfolio/booking-web-api/) | Booking conflict behavior, HTTP client, browser error recovery, persistence across restarts |
| Reliable background work | [Durable Job Queue](../portfolio/durable-job-queue/) | Worker leases, retries, idempotency and dead-letter behavior |
| AI tool integration | [MCP Knowledge Tools](../portfolio/mcp-knowledge-tools/) | Real MCP client/server interaction, read-only tools and source citations |
| Agent safety controls | [Agent Approval Queue](../portfolio/agent-approval-queue/) | Argument-bound approvals, expiration and atomic one-time consumption |
| Infrastructure | [VPN API](../portfolio/cloud-vpn-api/) | Authentication, generated configuration, namespace tunnel and revocation tests |
| Systems and observability | [Go Health Probe](../portfolio/go-health-probe/) · [Rust Log Metrics](../portfolio/rust-log-metrics/) · [Trace Inspector](../portfolio/otel-trace-inspector/) | Concurrency, validated input, exact durations and useful diagnostics |

## Try and verify

1. Choose a project and read its README for prerequisites.
2. Run its synthetic demo or download a [CI build artifact](../portfolio/README.md#download-built-projects).
3. Run the documented tests and inspect failure cases.
4. Read its design decisions and limitations before adapting it.

For the full .NET application, use the [Docker quick start](../README.md#start-the-full-stack). For browser-only exploration, open the [Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site).

## Verification scope

[GitHub Actions](https://github.com/ssaka2/Ai-project-/actions) shows checks for individual commits. The [Azure VM report](vm-verification-2026-10-02.md) is a dated development-environment result. Neither implies that every service is publicly deployed, that real model output has been evaluated, or that production load and backups have been tested.
