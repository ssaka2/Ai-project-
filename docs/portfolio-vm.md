# Portfolio virtual machine plan

This plan runs the repository's 19 projects on a Linux x64 development VM. It does not create a VM, configure cloud billing, or publish private demonstration APIs. Some projects are CLI tools or libraries; they run on demand rather than as permanent web services.

## Provisioning inputs

Before provisioning, choose the cloud account, region, monthly budget, and an SSH public key whose private key you control. Resolve any provider account/quota warnings. Never send a private SSH key through chat or commit it.

A planning starting point is Ubuntu 24.04 LTS x64, 4 vCPUs, 8 GB RAM, and at least 80 GB disk. This is not a tested all-services-at-once capacity guarantee. Run builds and browser tests sequentially. Real Ollama inference needs a separate model/resource decision; the existing synthetic demos and mock tests do not require a model or GPU.

Allow SSH from the administrator's network. Keep development web ports on loopback and use SSH forwarding. Open VPN UDP 51820 only when intentionally setting up the WireGuard server. Public CareerDesk hosting requires the production configuration described in its setup guide, including HTTPS, SMTP, and protected persistent storage.

## Prepare the host

Install Git, Docker Engine with Compose v2, Python 3.11+, .NET 10 SDK, Node.js 24, Go 1.27, and Rust 1.98.1 through their official distribution instructions. The versions here match the repository's CI configuration at the time this guide was added; update this guide alongside toolchain changes. Install WireGuard tools only when using the VPN functionality.

Clone the repository as your normal development user:

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
python3 scripts/vm_preflight.py
```

The read-only checker emits JSON and returns 1 when required host prerequisites are missing. It does not install software, create credentials, change firewalls, or start services. Resource figures are planning hints and can reflect the host rather than container limits. A successful result does not verify projects, browser installation, VPN kernel support, network access, backups, or cloud billing.

## Install project dependencies and verify

From the repository root, create an isolated Python environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt -r portfolio/ai-response-contract-lab/requirements.txt -r portfolio/booking-web-api/requirements-browser.txt
python -m pip check
python portfolio/run_tests.py
```

This runs all ten standalone Python test suites, including the VPN management API and agent approval queue. It does not start permanent project services.

Run the other portfolio checks:

```sh
python portfolio/support-ticket-api/verify_api.py
python portfolio/booking-web-api/verify_api.py
node --test portfolio/signed-webhook-receiver/test_server.ts
node --test portfolio/ollama-request-gateway/test_gateway.ts
node --test portfolio/otel-trace-inspector/test_inspect.ts
node --test portfolio/ai-engineering-web-lab/test-evaluate.mjs
(cd portfolio/go-health-probe && go vet ./... && go test -race ./... && go build -o healthprobe . && ./healthprobe -demo)
(cd portfolio/rust-log-metrics && cargo +1.98.1 test --locked && cargo +1.98.1 build --release --locked && ./target/release/log-metrics --demo)
```

For booking's real-browser checks, follow its [verification instructions](../portfolio/booking-web-api/README.md#browser-verification). Browser binaries and OS dependencies are a separate installation. Full CareerDesk browser/SQL tests also need the disposable SQL Server and email services described in the [root verification section](../README.md#verification).

## Start the applications you need

| Project group | How to run |
| --- | --- |
| CareerDesk, SQL Server, test email | Follow [full-stack setup](full-stack-setup.md); use synthetic data and SSH forwarding for development |
| Booking Web API and browser UI | Follow [booking setup](../portfolio/booking-web-api/README.md); loopback port 5080 |
| Support Ticket API | Follow its [README](../portfolio/support-ticket-api/README.md) for service configuration and endpoints |
| VPN management API | Follow [VPN Compose setup](../portfolio/cloud-vpn-api/README.md); loopback port 8090; tunnel configuration is a separate administrative step |
| Signed webhooks and Ollama gateway | Follow each project's README; choose distinct service ports before running both together |
| Web Lab | Serve its static files locally as described in its [README](../portfolio/ai-engineering-web-lab/README.md) |
| Python tools, MCP tools, approval queue, Go/Rust CLIs, trace inspector | Run their documented entry points on demand; see the [complete catalog](../portfolio/README.md) |

Example SSH forwarding for the booking app on a remote VM:

```sh
ssh -L 5080:127.0.0.1:5080 YOUR_USER@VM_IP
```

Then open `http://127.0.0.1:5080` on the computer running SSH. The app must already be running on the VM. Do not expose the unauthenticated booking or support-ticket demo APIs publicly.

## Data and acceptance checks

Keep application databases, Docker volumes, and persistent encryption keys outside disposable build directories. Protect tokens and keys separately from Git. Before accepting the VM, verify service startup, restart persistence, each project's tests, and backup restoration. Test WireGuard connection/revocation separately using the VPN project guide; installing `wg` alone does not prove a working tunnel.

Record the VM ID, region, selected size, billing plan, source commit, and verification results after provisioning. No VM ID or deployed application URL is recorded here because this guide does not provision a server.
