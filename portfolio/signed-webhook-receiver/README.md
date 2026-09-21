# Signed Webhook Receiver

A TypeScript HTTP service running directly on Node.js 24 LTS. Verify HMAC-SHA256 signatures against raw request bytes, reject stale or future timestamps, detect duplicate events, and bound the memory used by its replay cache. No external runtime packages are required.

## Run a complete local demo

Install Node.js 24. From this directory:

```sh
npm test
npm run demo
```

The demo creates a temporary loopback server with a random secret, submits the same synthetic event twice, prints `202` then `409`, and shuts down. It makes no requests to external services.

For a persistent local server, set `WEBHOOK_SECRET` to a random secret of at least 32 bytes, then run `npm start`. Keep it outside source control. The service binds to `127.0.0.1:5082`; use `PORT` to change the port. `GET /health` reports readiness.

## Signing contract

POST JSON to `/webhooks`, with these headers:

| Header | Value |
| --- | --- |
| `Content-Type` | `application/json` |
| `X-Event-Id` | 1–100 letters, digits, underscores or hyphens |
| `X-Timestamp` | Integer Unix time in seconds |
| `X-Signature` | Lowercase hexadecimal HMAC-SHA256 |

The signed bytes are `timestamp + "." + eventId + "." + rawBody`. Use the exported `sign()` function as an example sender. The JSON body must be an object with a `type` identifier such as `ticket.created`; other fields are accepted but not acted upon.

This is a project-specific protocol, not a drop-in implementation of Stripe, GitHub, or another provider's signing scheme.

## Behavior

- Signatures use constant-time comparison after validating hex length and format.
- Timestamps must be within 300 seconds of server time, including the boundary.
- Payloads are limited to 64 KiB by default.
- A valid event ID is reserved until its original timestamp's acceptance window closes. An invalid request does not reserve an ID.
- The replay cache holds at most 1000 IDs by default. It rejects new events with 503 when full rather than evicting still-valid replay protection.
- Accepted requests return 202, duplicates 409, invalid signatures 401, malformed events 400, oversized bodies 413, and unsupported content types 415.

## Tests and limits

Eight HTTP/unit tests cover concurrent duplicates, tampered bytes, old/future timestamps, boundary timing, malformed bodies, body limits, cache limits, and startup validation.

The service acknowledges validation only: it does not persist or dispatch business events. Replay memory resets on restart and is not shared across processes. For production use, add a transactional event store, durable delivery, TLS, secret rotation, rate limiting, and deployment-specific authentication. Never treat this local demonstration as a complete payment or production webhook system.

Node runs these `.ts` files using native type stripping; this project does not run a separate TypeScript compiler/type-checker. Runtime input validation and integration tests remain explicit. See [Node TypeScript support](https://nodejs.org/api/typescript.html) and [supported Node releases](https://nodejs.org/en/about/previous-releases).

No license has been selected; the parent repository's licensing status applies.
