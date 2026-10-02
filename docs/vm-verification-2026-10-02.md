# Azure VM verification — 2026-10-02

Verified source commit: `5f6ed45d610745dad8f76dd750eda0405e1d8241`.

The repository's 19 projects were installed and checked on an Ubuntu 24.04 x64 development VM in Azure Mexico Central (Standard_B2as_v2, 2 vCPU, 8 GB RAM). Checks ran sequentially. This records development verification, not a public production deployment or a guarantee of simultaneous capacity.

## Results

| Check | Result |
| --- | --- |
| Python dependency consistency and ten standalone Python project suites | PASS |
| Signed webhook receiver, Ollama gateway mock tests, OpenTelemetry trace inspector, Web Lab | PASS |
| Support Ticket API and Booking API verification | PASS |
| Go health probe: vet, race tests, build, demo | PASS |
| Rust log metrics: tests, release build, demo | PASS |
| Booking published application: Chromium, Firefox, WebKit and narrow Chromium | PASS: all four configurations |
| VPN Docker API authentication, restart persistence and revocation | PASS |
| WireGuard isolated network namespace connection and revocation | PASS |
| CareerDesk Release build and model/migration consistency | PASS |
| CareerDesk service, SQL Server and browser tests | PASS: 66 executed, 66 passed, zero skipped or failed |
| CareerDesk Docker Compose startup, login page, readiness and restart | PASS |

VM toolchains include Python 3.12, Node 24.21.0, .NET SDK 10.0.112, Go 1.27.1, Rust 1.98.1, Docker and Compose. Browser binaries and OS dependencies are installed. The Go toolchain was obtained using Go's automatic toolchain download after a direct archive transfer failed.

Detailed logs and the test result files remain under `/home/azureuser/verification/` on the VM. The checkout is `/home/azureuser/Ai-project-`. Disposable verification containers, databases and VPN namespaces were cleaned up by the test scripts.

## Access and operating limits

- Development endpoints stayed on loopback; public application and VPN access was not configured.
- The VM is intended to be deallocated when idle to conserve student credit. Start it before running projects. Disk and reserved public IP resources can still consume credit while compute is deallocated.
- Azure for Students was enabled with its spending limit **On** when checked on this date. This is not confirmation of the remaining credit balance.
- Real Ollama model inference, production HTTPS/SMTP, external VPN clients, backup restoration and all-services-at-once load were not verified.
- SSH private-key download was not confirmed. Azure Run Command was used for administration; establish verified user access before depending on SSH forwarding.

See [VM setup and per-project commands](portfolio-vm.md). Do not publish the unauthenticated development APIs directly to the internet.
