# Support Ticket API

A C#/.NET 10 minimal API for a local support desk. Create tickets, filter and page through them, change status, review history, and reject stale concurrent edits. Tickets persist in a JSON snapshot across application restarts.

## Run

Install the .NET 10 SDK. From this directory:

```sh
dotnet run --project SupportTickets.csproj
```

The API defaults to `http://127.0.0.1:5081`. Open that URL for the route list, or create a synthetic ticket:

```sh
curl -i http://127.0.0.1:5081/tickets -H 'Content-Type: application/json' -d '{"title":"Login fails","description":"Synthetic demo ticket"}'
```

Use the returned ID in later requests. For example, send `{"status":"InProgress","expectedVersion":1}` with PATCH to `/tickets/<id>/status`.

The default storage file is `data/tickets.json`, relative to the working directory. Set the `TICKET_DATA_PATH` environment variable to an absolute path to use a consistent location. Stop the application before manually editing or moving its data.

## API contract

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Readiness after the snapshot has loaded |
| `POST /tickets` | Required title (1–120 trimmed characters), description (0–2000 characters); returns 201 and Location |
| `GET /tickets?status=Open&offset=0&limit=20` | Optional exact status filter, nonnegative offset, limit 1–100 |
| `GET /tickets/{id}` | Ticket details and history; 404 if absent |
| `PATCH /tickets/{id}/status` | Required valid status and expectedVersion; stale edits return 409 with current ticket |

Status values are `Open`, `InProgress`, and `Closed`. Closed tickets must be reopened before moving to InProgress. A no-op status request with the current version leaves both version and history unchanged. Every actual change increments the version and appends a UTC history event in the same snapshot.

## Verify

Requires Python 3.11+ as well as .NET 10:

```sh
python verify_api.py
```

The verifier builds the real API, launches it on a temporary loopback port, and performs 13 HTTP checks, including invalid inputs, filtering, competing edits, history, and persistence after restart. It uses a disposable data file and shuts down its child process. GitHub Actions runs this separately from the Python portfolio tests.

## Design decisions and limits

- A process-wide lock serializes changes; expected versions stop stale edits overwriting each other.
- Each write serializes a new snapshot to a temporary file, flushes it, and moves it over the previous file before publishing the in-memory state. Failed writes do not publish the new in-memory state.
- The service uses only the ASP.NET shared framework; no extra NuGet dependencies are required.
- This is a **single-process, local demonstration**. Multiple processes must not share a snapshot file. It rewrites the entire collection per change, has no retention policy, and is not suitable for large datasets.
- No authentication or authorization is implemented. Keep it on loopback with synthetic data. Production work would require identity, roles, a transactional database, backups, rate limits, and monitoring.
- A successful health response does not continuously test storage writability. Crash/power-loss durability depends on the filesystem; the design is not a substitute for a database transaction log.

No license has been selected; the parent repository's licensing status applies.
