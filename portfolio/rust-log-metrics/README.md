# Rust Log Metrics

A dependency-free command-line analyzer for HTTP service logs. Reads a strict tab-separated format, groups by service, and produces JSON request counts, server-error rates, mean latency, and nearest-rank p95 latency.

## Run

Install stable Rust with Cargo, then:

```sh
cd portfolio/rust-log-metrics
cargo test --locked
cargo build --release --locked
cargo run --release --locked -- --demo
cargo run --release --locked -- sample.tsv
```

Use `-` as the input path to read stdin. The compiled executable is `target/release/log-metrics` (`.exe` on Windows). The demo uses synthetic data and performs the actual aggregation.

Input has this exact header and three tab-separated columns:

```text
service	status	latency_ms
api	200	20
api	503	100
worker	200	40
```

Use literal tab characters. Status must be 100–599, latency an unsigned integer, and service names 1–64 ASCII letters, digits, underscores, or hyphens. Blank records and additional columns are rejected. Malformed data produces a line-numbered error and exit code 2, with no partial JSON report. Files are limited to 10 MiB. Successful analysis exits 0 even when server errors are present; this is a report, not an SLO policy gate.

HTTP 5xx responses count as server errors; 4xx responses do not. Error rate is between 0 and 1. p95 uses the nearest-rank definition, and means are rounded to three decimals. An unsigned 128-bit accumulator prevents overflow when summing valid 64-bit latency values. Service names are restricted so generated JSON is safe to serialize. Output order is deterministic.

Six tests cover grouping, p95, malformed rows, headers, large latency values, and Windows line endings. CI builds a release executable and checks demo output.

The input and latency samples are held in memory; the 10 MiB input cap makes this a small-log tool, not a streaming big-data engine. It does not parse arbitrary CSV, JSON, or web-server log formats. It contains no network service, storage daemon, or paid dependency.

Rust adds memory-safe systems programming and compiled data tooling to the portfolio. See the [official stable Rust release](https://blog.rust-lang.org/releases/latest/) for current toolchain activity; CI pins Rust 1.98.1. No popularity ranking or production deployment is claimed.
