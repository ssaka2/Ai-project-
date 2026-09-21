# Ollama Request Gateway

A local TypeScript HTTP gateway for Ollama generation. Demonstrates bounded concurrency, request validation, bearer authentication, upstream deadlines, normalized responses, and a small in-memory circuit breaker.

## Run the working fixture demo

Node.js 24, no npm dependencies:

```sh
cd portfolio/ollama-request-gateway
npm test
npm run demo
```

The demo and tests start a mock Ollama endpoint and close both servers afterward. They do **not** run an AI model. Node executes erasable TypeScript directly; this project does not run a separate static type checker.

## Connect a real local model

Install and run [Ollama](https://docs.ollama.com/), and download a model appropriate for your machine. Set `OLLAMA_MODEL` to its exact installed name. In a POSIX shell:

```sh
export OLLAMA_MODEL='your-installed-model-name'
export GATEWAY_TOKEN="$(node -e "console.log(require('node:crypto').randomBytes(32).toString('hex'))")"
npm start
```

In another terminal with the same `GATEWAY_TOKEN` value:

```sh
curl http://127.0.0.1:8787/generate \
  -H "Authorization: Bearer $GATEWAY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Explain optimistic concurrency in three sentences."}'
```

The gateway forwards to `http://127.0.0.1:11434/api/generate`, with a fixed configured model and `stream: false`, following the [Ollama generate API](https://docs.ollama.com/api/generate). Live model inference is an optional integration requiring your local installation; only the mock-backed adapter is tested in CI.

## Behavior

| Condition | Result |
| --- | --- |
| Valid request | 200 with `{model, response}` |
| Wrong token | 401 |
| Missing/empty/overlong prompt | 400 |
| Request above 16 KB | 413; connection may close |
| Two active requests already in progress | 429 |
| Invalid/failed upstream response | 502 |
| Three upstream failures without a success | Circuit opens; subsequent requests get 503 |
| Upstream exceeds 30 seconds | 504 |

After a 30-second cooldown, requests can try the upstream again, subject to the concurrency limit. A success resets the breaker. Responses are capped at 1 MB; prompts at 8,000 characters. Slow request uploads are disconnected after the body deadline. `GET /health` reports process liveness and active request count, not model readiness.

## Limits

Localhost binding only; no public deployment configuration, streaming, automatic retries, persisted queue, or distributed circuit state. The breaker is intentionally simple: it permits up to the concurrency limit after cooldown. Restarting resets counters. Caller disconnects abort the upstream HTTP request and release the concurrency slot without counting as an upstream failure. Whether model computation stops depends on Ollama; the gateway cannot guarantee server-side cancellation. Tokens and prompts are not logged. The programmatic factory accepts alternate loopback origins for integration tests; clients cannot choose the upstream or model in a request.
