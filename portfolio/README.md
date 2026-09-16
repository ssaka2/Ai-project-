# Software engineering portfolio

Runnable projects demonstrating backend logic, relational data modeling, and data quality. All examples use synthetic data and run locally without paid services.

| Project | Stack | Engineering focus |
| --- | --- | --- |
| [AI Career Desk](../README.md) | C#, ASP.NET Core, EF Core, SQL Server | Account isolation, resume workflows, application tracking |
| [Inventory Ledger](inventory-ledger/) | Python, SQLite, SQL | Atomic updates, idempotent requests, concurrent writers |
| [Airport Analytics](airport-analytics/) | Python, CSV, SQLite, SQL | Validated ingestion, repeatable loads, operational metrics |

## Quick start

Install Python 3.11 or newer. These two projects use only the standard library.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
python -m unittest discover -s portfolio/inventory-ledger -v
python -m unittest discover -s portfolio/airport-analytics -v
python portfolio/airport-analytics/pipeline.py portfolio/airport-analytics/sample_flights.csv --db :memory:
```

Each project has its own entry point, test suite, setup instructions, design decisions, and limitations. They can be extracted into separate repositories without depending on CareerDesk.

## Review guide

- Inventory: follow `move()` from request validation to the database transaction; inspect the concurrent-sales test.
- Analytics: inspect `validate()`, the upsert, and `report.sql`; compare cancellation and on-time denominators.
- CareerDesk: review owner-scoped services and SQL Server integration tests.

These are portfolio demonstrations. No production use, performance benchmarks, or business impact is claimed. No license has been selected; the parent repository's licensing status applies.
