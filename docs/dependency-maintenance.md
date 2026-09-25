# Dependency maintenance

The repository's `.github/dependabot.yml` configures weekly update checks.

| Coverage | Location |
| --- | --- |
| GitHub Actions | `.github/workflows/` |
| NuGet application and test dependencies | Root solution |
| MCP Python SDK | `portfolio/mcp-knowledge-tools/` |
| JSON Schema validation | `portfolio/ai-response-contract-lab/` |
| Playwright browser verification | `portfolio/booking-web-api/requirements-browser.txt` |
| .NET SDK and runtime container tags | `Dockerfile` |
| Mailpit and SQL Server container tags | `compose.yaml` |

Updates are proposed as pull requests. This configuration does not automatically merge updates or deploy applications. Check the Dependabot update logs to confirm each scheduled check ran successfully; saving the configuration is not evidence that every dependency is current.

## Review an update

1. Read the dependency's release notes, including migrations and breaking changes.
2. Wait for the relevant GitHub Actions jobs to pass on the proposed commit.
3. For .NET or container changes, require CareerDesk's SQL Server, email, browser, Docker startup, and restart checks.
4. For Playwright changes, require booking tests in Chromium, Firefox, WebKit, and the narrow Chromium viewport, plus the published-package checks.
5. Merge the verified change. Keep the previous successful commit available for rollback.

.NET container minor and patch changes are grouped so SDK and runtime images can be reviewed together. Major .NET container and SQL Server upgrades require a deliberate compatibility review and are excluded from these automatic version proposals. The local `ai-career-desk:local` image is built from this repository and is excluded from Compose registry updates.

## Manual review still required

- Go and Rust toolchain versions embedded in workflow commands and documentation.
- Node.js and .NET runtime selections in workflow inputs and project target frameworks.
- Image tags embedded in shell commands, including the Mailpit test inbox in `.github/workflows/ci.yml`. Keep that version aligned when updating Compose's Mailpit image.
- Changes behind floating container tags such as `10.0` and `2022-latest`; an unchanged tag does not mean identical image contents.
- Real Ollama models, external services, deployment configuration, and production credentials.

Go Health Probe, Rust Log Metrics, and the two Node.js services currently have no third-party package dependencies. Add dependency monitoring when introducing such packages.

See [GitHub's supported ecosystems](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories) for supported update mechanisms.
