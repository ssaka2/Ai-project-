# Appointment Booking Web API

A complete local appointment-booking demonstration: ASP.NET Core HTTP API, browser UI, persistent bookings, and a separate Python web-service client. The browser and Python client both call the same REST endpoints.

## Download the ready-built package

1. Open [Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml) and choose a successful run for `main`.
2. Under **Artifacts**, download **booking-web-api-release** (GitHub sign-in may be required). Artifacts are retained for 30 days.
3. Extract it into a writable folder. Install the **ASP.NET Core Runtime 10** for your operating system and CPU, or the .NET 10 SDK. The base .NET Runtime alone is insufficient.
4. Open a terminal in the extracted folder:

```sh
dotnet BookingApi.dll --urls http://127.0.0.1:5080
```

Open http://127.0.0.1:5080. Keep the terminal running; use Ctrl+C to stop. Keep the package files together and start from its folder so browser assets and the default data path resolve correctly. Keep your `data` folder when replacing the application files with a newer package.

The package includes the browser UI, API, Python client, and verification script. It is framework-dependent: no source compilation is needed, but the runtime is required. CI verifies it on Linux; Windows and macOS have not been tested.

With optional Python 3.11+, run these commands from the extracted folder in another terminal:

```sh
python client.py list
python client.py demo
python verify_api.py --published-dir .
```

Verification starts a separate temporary server and uses disposable data; it does not touch your saved bookings. The package is a local application download, not a public hosted deployment.

## Run the app from source

Install .NET 10 SDK. From the repository root:

```sh
cd portfolio/booking-web-api
dotnet run --urls http://127.0.0.1:5080
```

Open http://127.0.0.1:5080. Choose a service, enter a synthetic customer name and a future time, then book. The page displays times in your local timezone; requests convert them to UTC. Bookings survive restarts in `data/bookings.json`. Set `BOOKING_DATA` to select another writable file.

In another terminal, call the web service using Python 3.11+:

```sh
python portfolio/booking-web-api/client.py list
python portfolio/booking-web-api/client.py demo
```

The demo creates, retrieves, and cancels one synthetic booking. It needs the running service above. If that service already has a consultation in the selected demo time, it reports the conflict instead of overwriting it.

## Web API

| Method | Endpoint | Result |
| --- | --- | --- |
| GET | /health | 200 when startup succeeded |
| GET | /api/services | Supported service identifiers |
| GET | /api/bookings | Bookings ordered by start time |
| GET | /api/bookings/{id} | One booking, or 404 |
| POST | /api/bookings | 201 with Location header; 400 invalid input; 409 overlap |
| DELETE | /api/bookings/{id} | 204 cancelled; 404 missing |

Example request body (replace the time with a future UTC time within 365 days):

```json
{"service":"consultation","customer":"Demo Customer","start":"2026-10-01T14:00:00Z","minutes":30}
```

Durations are 15–240 minutes. Each service has capacity one. Adjacent appointments are allowed. Different services may share a time. Errors use HTTP status codes and Problem Details where handled by the API. Oversized request bodies are rejected. This is a REST web service, not a SOAP/WSDL service.

## Verification

```sh
python portfolio/booking-web-api/verify_api.py
```

CI verifies both the source build and the published package, with 26 HTTP and persistence checks each in Production mode. The verifier builds the app by default and runs a real HTTP server using a temporary database file. It tests the UI assets, CRUD, validation, concurrent conflicts, restart persistence, corrupted data, and the separate Python client. No external database or paid account is needed.

## Design and limits

Writes serialize within one application process and atomically replace the JSON file after flushing. In-memory state changes only after a successful replacement. Use one process per data file; there is no cross-process lock or distributed coordination. The whole dataset is kept in memory, so this is intended for small demos. A database and migrations would be required for a larger service. `/health` is a liveness check, not a guarantee that a future storage write will succeed.

There is no authentication, ownership isolation, email notification, payment, or calendar integration. Every API caller can see and cancel every appointment. Run on loopback with synthetic data only. Public production deployment requires authentication, authorization, rate limits, HTTPS, protected storage, and backup/restore testing. No public hosting is claimed.
