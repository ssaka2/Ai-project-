# Decoy Lab

A local, educational decoy web server with a live event dashboard. It demonstrates what reconnaissance, login guessing, secret-file probes, path traversal, and injection-like requests look like in server telemetry. Everything is synthetic. It does not replicate your production application, execute exploits, or reproduce an operating-system compromise.

## Run

Requires Python 3.11 or newer; no third-party packages, accounts, or API keys.

1. Extract this folder.
2. Open a terminal inside `decoy-lab`.
3. Run `python app.py` (or `python3 app.py`; on Windows, `py app.py`).
4. Open **http://127.0.0.1:8080/lab** in Chromium, Chrome, or another browser.
5. Click **Run simulated activity**. Examine the nine requests, pattern counts, response codes, and defense explanations.
6. Click **Download event report** to save JSON, or **Clear events** to reset.
7. Stop with Ctrl+C. If port 8080 is occupied: `python app.py --port 8090`.

The browser and Python process must run on the same computer. This package is not a publicly hosted site or a phone app.

## What the demonstration does

| Scenario | Decoy behavior | Lesson |
| --- | --- | --- |
| Normal page request | Returns a synthetic portal message | Establish normal traffic context |
| Admin/status discovery | Logs requests; returns 404 | Identify unexpected endpoint probing |
| Environment/source-control file probes | Returns 404; exposes no secrets | Keep configuration outside the web root |
| Encoded parent-directory probe | Returns 404; never accesses a requested filesystem path | Normalize paths and allowlist file access |
| Two synthetic login attempts | Always rejects with 401 | Detect repeated failures; use MFA and rate limits |
| SQL-like login input | Always rejects with 401; never runs a query | Recognize a signal; use parameterized queries |

The simulator sends actual HTTP requests only to the current lab instance's fixed loopback address. There is no external target setting. Categories are deliberately simple heuristics; ordinary requests may resemble attacks, and many attacks will not match these rules. This is not an intrusion-detection product.

## Isolation and data

- Binds only to `127.0.0.1`; no public deployment or firewall changes.
- No shell commands, database execution, outbound scanning, malware, or real accounts.
- Dashboard mutations require a per-run token; Host and Origin checks protect the local controls.
- The timeline stores method, path (maximum 160 characters), category, time, and response code. It omits query strings and raw bodies. Do not put real secrets in URL paths.
- At most 1,000 events remain in memory; restarting loses them. A downloaded report persists until you delete it.
- Static files are explicitly allowlisted. User-supplied paths are never used to read local files.
- No TLS or production hardening. Do not expose this development server through a tunnel or public port.

## Verify

```sh
python -m unittest -v
```

Tests exercise real loopback HTTP requests, all six pattern categories, denied dashboard mutations, DNS-rebinding-style Host rejection, password/query redaction, rejected path access, event reset, memory limits, and body limits.

## Extending toward a replica

To model your own application, add synthetic routes that resemble its public interfaces and use generated data. A realistic vulnerable-service exercise needs a separate disposable VM or isolated container network with no production credentials, data, mounts, or routes. This starter intentionally models observable requests and responses, not successful exploitation.

## Optional Chromium verification

GitHub Actions installs the browser and runs desktop/mobile checks automatically. To run these checks yourself:

```sh
python -m pip install -r requirements-browser.txt
python -m playwright install --with-deps chromium
python verify_browser.py
```

These checks cover simulation, event display, report download, clearing events, safe rendering of untrusted event text, and mobile layout. The server itself still needs only Python.
