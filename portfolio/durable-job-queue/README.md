# Durable Job Queue

A small SQLite-backed worker queue that demonstrates the failure handling behind background processing: retry-safe submission, exclusive claims, expiring leases, exponential backoff, and a dead-letter state.

## Run

Python 3.11+, standard library only. From this directory:

```sh
python jobs.py enqueue demo-001 word_count "hello durable background jobs"
python jobs.py work
python jobs.py list
python -m unittest discover -v
```

The first work command returns a result with four words. Repeating the enqueue command returns the same job ID and does not enqueue duplicate work. Using the same key with a different payload, kind, or attempt limit is rejected. Keys remain reserved even after completion.

Use `python jobs.py --db another.db ...` to select another database. The default is `jobs.db`. Supported handlers are `word_count`, `sha256`, and `fail`; handlers run locally and do not execute arbitrary commands or make network requests.

To inspect the failure path without waiting for retries:

```sh
python jobs.py enqueue failure-001 fail "synthetic failure" --max-attempts 1
python jobs.py work
python jobs.py list
```

This job moves to `dead`. With the default three attempts, failures retry after 2 then 4 seconds. Run `work` again once the retry is due; the command processes at most one ready job and exits, so it does not install a daemon or scheduler. If other ready jobs exist, they may be selected first.

## State and ownership

| State | Meaning / next action |
| --- | --- |
| `pending` | Eligible when available_at is reached |
| `running` | A worker holds a unique token and a 30-second lease |
| `succeeded` | Result committed by the current worker before lease expiry |
| `dead` | Attempt limit reached through failures or expired leases |

SQLite `BEGIN IMMEDIATE` serializes claims. Each claim increments the attempt count. A completion must present the current token before expiry. When another worker recovers an expired job, the previous token cannot modify its state. Expired jobs are recovered during the next claim, not by a separate sweeper. Application failures back off exponentially, capped at 60 seconds; expired leases become immediately eligible unless attempts are exhausted.

## Guarantees and tradeoffs

Persistence survives process restart. Worker recovery permits **at-least-once execution attempts**, not exactly-once side effects or guaranteed success: a handler can finish its work and crash before recording completion. Real handlers must make external effects idempotent. The example handlers are pure computations.

Eleven tests cover persistence, competing workers, duplicate keys, stale and expired tokens, retry timing, dead-letter transitions, double completion, and input validation. Test clocks are supplied directly to queue functions, so retry tests do not sleep.

This is a local prototype: no automatic heartbeat scheduler, remote broker, dashboard, authentication, retention policy, metrics backend, or dead-letter replay command is included. Handlers must finish within the lease. SQLite allows one writer at a time and is not a distributed queue. Wall-clock changes can affect lease timing. Job payloads and results are stored in plaintext; the examples use synthetic text.

CLI usage/input failures exit 2. A processed job that failed its handler still produces a valid queue result and exits 0; inspect the returned state or the job listing to see retries/dead letters.

No license has been selected; the parent repository's licensing status applies.

Long-running custom handlers may call `renew(db, id, token, lease_seconds=30)` before expiry. Renewal checks ownership, cannot revive expired jobs, and never shortens the current lease. The built-in short handlers do not schedule heartbeats.
