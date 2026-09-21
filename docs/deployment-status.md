# Deployment status

Updated September 21, 2026. Public source code, passing CI, and a deployed service are separate states.

## Public live application

[AI Engineering Web Lab](https://sandeep-ai-engineering-lab.ssaka2.chatgpt.site) is deployed with public access. It evaluates recorded text against explicit rules and downloads reports. It does not call a language model or host the other twelve projects.

## Remaining projects

| Project | Current runtime | What hosted operation needs |
| --- | --- | --- |
| AI CareerDesk | Tested local Docker application | Production SQL Server, verified SMTP, persistent application keys, hosting and HTTPS configuration |
| MCP Knowledge Tools | Local stdio agent server | Runs alongside an MCP client; remote use requires a separately designed authenticated HTTP transport |
| AI Response Contract Lab | Local Python CLI | CLI can run locally now; live generation needs an installed Ollama model |
| Agent Memory Store | Local Python/SQLite CLI | Persistent local database; hosted multiuser access would require an authenticated API |
| Ollama Request Gateway | Local HTTP service | Reachable model runtime, model weights, credentials, private networking, and hosting resources |
| Agent Evaluation Lab | Local Python CLI | Run against recorded response files; reports can be shared as static artifacts |
| Local Knowledge Search | Local Python/SQLite CLI | Local documents and index; public use needs document access controls and a web interface |
| Support Ticket API | Local .NET HTTP service | Authentication and authorization before public writes, persistent storage, and hosting |
| Durable Job Queue | Local SQLite library/CLI | Worker process and persistent storage; not a standalone public website |
| Signed Webhook Receiver | Local Node HTTP service | Signing secret, HTTPS endpoint, hosting, and an explicitly configured sender |
| Inventory Ledger | Local Python/SQLite CLI | Persistent database; hosted access needs authentication and a web/API interface |
| Airport Analytics | Local CSV/SQLite pipeline | Input files and execution environment; not a continuously running website |

A private CareerDesk project and an empty careerdesk-web service are now prepared in the connected Railway account. Dockerfile, migration pre-deploy command, readiness checks, and restart settings are configured directly on the service. Production environment, port 8080, confirmed-account enforcement, disabled AI, and the planned /var/keys path are set without deploying. No source is connected, no deployment exists, and no persistent volume is attached yet. No production SQL Server or SMTP credentials were supplied. No model or compute workload was started.

Railway's configuration API rejected the legacy railwayConfigFile setting as deprecated. The equivalent service settings were successfully applied directly and read back. The obsolete railway.json has now been removed and the deployment guide documents the direct service configuration. No Infrastructure as Code configuration has been applied. Free-tier allowance and billing limits have not been verified. Do not expose development Mailpit, unauthenticated sample APIs, or developer database settings as a substitute for these prerequisites.

See [CareerDesk deployment configuration](railway-deployment.md) for the prepared service settings and acceptance checks. Use hosting-provider secret settings for credentials; never put them in a README or chat message.

## Prepared Railway target

- Project: CareerDesk (`1a65ce11-5170-4be2-a9dd-5df15a5fa146`)
- Environment: production (`c4193e7b-84aa-4c31-b15f-25bd9d9488ae`)
- Service: careerdesk-web (`e15a43ed-e361-40ae-ae44-6a92c6b6f674`)

Before starting: verify the account's free allowance, provide a production SQL Server connection and verified SMTP configuration through service secrets, attach persistent storage for application keys, and configure the public hostname and HTTPS proxy handling. This target is prepared, not deployed.
