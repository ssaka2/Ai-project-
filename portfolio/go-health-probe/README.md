# Go Health Probe

A concurrent command-line health checker for trusted HTTP endpoints. Produces ordered JSON results and exits nonzero when any endpoint is unhealthy. Useful for service readiness checks in deployment pipelines.

## Run

Install Go 1.26 or newer, then:

```sh
cd portfolio/go-health-probe
go test -race ./...
go vet ./...
go build -o healthprobe .
./healthprobe -demo
./healthprobe -workers 4 -timeout 2s http://localhost:8080/health/ready
```

On Windows use `healthprobe.exe`. The demo starts a real disposable HTTP server, checks it, prints JSON, and stops it. No running external service is needed for the demo or tests.

- A bounded worker pool checks at most 32 endpoints simultaneously, preserving input order in output.
- Every request has a timeout. Cancellation propagates through the request context.
- Only 2xx responses are healthy. Redirects are reported without following them.
- Responses are closed without loading their bodies. Inputs are limited to 1,000 URLs.
- Exit 0: all healthy; exit 1: an endpoint failed; exit 2: invalid arguments or output failure.

Six tests exercise status handling, output ordering, redirects, timeout, cancellation, worker limits, and invalid inputs. CI also runs the race detector and builds the executable.

This is an operator CLI, not a public URL-scanning API. Only check endpoints you own or are authorized to test. Results include URLs and network errors; do not use URLs containing tokens or publish sensitive internal addresses. It does not provide monitoring history, scheduled checks, authentication management, or TLS bypasses. A 2xx response alone does not prove business functionality.

Go adds compiled backend tooling and concurrency to the portfolio. The [Go release notes](https://go.dev/doc/go1.26) document the supported language baseline; CI uses the current stable release family. This project is independently implemented, not a claim of market ranking or production adoption.
