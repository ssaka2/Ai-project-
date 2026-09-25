# OpenTelemetry Trace Inspector

A dependency-free TypeScript command-line analyzer for OTLP/JSON trace exports. It reports per-service error counts and p95 span duration, plus observed trace duration and missing-parent warnings. Nanosecond timestamps are parsed as `BigInt`; reports retain exact duration values as decimal strings.

## Why this project

Observability matters for distributed APIs and agent pipelines. This tool demonstrates OTLP ingestion, exact timestamp arithmetic, trace graph validation, and honest handling of partial exports. It implements a documented subset of the [OTLP JSON format](https://opentelemetry.io/docs/specs/otlp/) and accepts the structure used in [OpenTelemetry trace file exports](https://opentelemetry.io/docs/specs/otel/protocol/file-exporter/).

## Run

Requires Node.js 24, which runs this erasable TypeScript directly. No npm installation is needed.

```sh
cd portfolio/otel-trace-inspector
npm test
npm run demo
node inspect.ts sample.json > report.json
```

The synthetic sample contains one agent request, retrieval, and an errored model-response span. Expected output: 3 spans, 1 trace, 1 error, and observed trace duration `5000000` nanoseconds (5 ms).

For your export:

```sh
node inspect.ts /path/to/trace.json > report.json
```

Exit status is 0 for valid input and 1 for invalid input or file errors. A valid trace containing an error span still exits 0: the analyzer succeeded, even though the observed operation failed. CI uploads the sample report as `otel-trace-report`.

## Input contract

- One JSON object with `resourceSpans`, containing `scopeSpans` and `spans` arrays.
- Nonzero hexadecimal trace IDs (32 characters) and span IDs (16 characters), case insensitive.
- Start/end timestamps as decimal uint64 strings. Numeric timestamps are rejected to prevent precision loss.
- Numeric status codes: 0 unset, 1 OK, 2 error. Missing status defaults to unset.
- `service.name` from resource attributes, or `unknown_service` when absent.
- Up to 10,000 spans and a 5 MiB CLI input file. Empty exports are valid. Unknown fields are ignored.

This is not a complete OTLP validator or receiver. Protobuf, gzip, JSONL, numeric timestamps, and streaming collector ingestion are not implemented. Convert those formats into a supported single JSON export first.

## Report semantics

`observedDurationNs` is the latest observed end minus the earliest observed start in a trace. Overlapping spans are not summed. It is not critical-path analysis and may understate the complete request when spans are missing. `p95SpanDurationNs` uses nearest-rank p95 over spans belonging to a service, not per-request latency. Error counts include only status code 2, not unset status.

Missing parents produce warnings because sampling or partial exports can omit spans. Duplicate IDs within one trace and parent cycles fail validation. The same span ID may appear in different traces. Cross-service clock skew is not corrected. Reports omit arbitrary span attributes and operation names, but trace IDs and service names may still be sensitive.

## Verification

Nine tests cover nanosecond precision, overlapping durations, p95 and error counts, missing parents, duplicate/cyclic relationships, invalid data, empty exports, trace separation, and CLI success/failure. The CLI sample also runs in CI. Node runs the TypeScript through built-in type stripping; this project does not claim separate static type checking.

No collector, dashboard server, model provider, or cloud account is required. This is an offline analysis tool, not a hosted monitoring platform.
