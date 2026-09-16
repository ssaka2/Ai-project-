# Software engineering portfolio

Runnable projects demonstrating backend logic, relational data modeling, document retrieval, and AI evaluation. All bundled examples use synthetic data and run locally without paid services.

[![Portfolio tests](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml/badge.svg)](https://github.com/ssaka2/Ai-project-/actions/workflows/portfolio.yml)

| Project | Stack | Engineering focus |
| --- | --- | --- |
| [AI Career Desk](../README.md) | C#, ASP.NET Core, EF Core, SQL Server | Account isolation, resume workflows, application tracking |
| [Inventory Ledger](inventory-ledger/) | Python, SQLite, SQL | Atomic updates, idempotent requests, concurrent writers |
| [Airport Analytics](airport-analytics/) | Python, CSV, SQLite, SQL | Validated ingestion, repeatable loads, operational metrics |
| [Local Knowledge Search](local-knowledge-search/) | Python, SQLite FTS5, BM25 | Offline retrieval, source citations, relevance evaluation |
| [Agent Evaluation Lab](agent-evaluation-lab/) | Python, JSONL, HTML | Response/trace checks, budget limits, regression gates |

## Quick start

Install Python 3.11 or newer. The four standalone projects use only the standard library. Knowledge Search also requires SQLite built with FTS5, which is verified by its tests.

```sh
git clone https://github.com/ssaka2/Ai-project-.git
cd Ai-project-
python portfolio/run_tests.py
python portfolio/airport-analytics/pipeline.py portfolio/airport-analytics/sample_flights.csv --db :memory:
```

Each project has its own entry point, test suite, setup instructions, design decisions, and limitations. They can be extracted into separate repositories without depending on CareerDesk.

## Review guide

- Inventory: follow `move()` from request validation to the database transaction; inspect the concurrent-sales test.
- Analytics: inspect `validate()`, the upsert, and `report.sql`; compare cancellation and on-time denominators.
- CareerDesk: review owner-scoped services and SQL Server integration tests.
- Knowledge Search: inspect snapshot replacement, line citations, literal query handling, and ranking evaluation.
- Evaluation Lab: compare the synthetic baseline and candidate, then inspect case-level regressions and the HTML report.

## Current AI engineering themes

The two newest projects demonstrate retrieval and agent evaluation, motivated by [contextual retrieval engineering](https://www.anthropic.com/engineering/contextual-retrieval) and [agent evaluation practices published in January 2026](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents). These are topic choices, not a claim that these repositories appear on GitHub Trending.

The portfolio workflow tests all four projects on Python 3.11, 3.12, and 3.13 and publishes downloadable example evaluation reports as workflow artifacts. AI CareerDesk has its own .NET/SQL Server/browser/Docker workflow.

These are portfolio demonstrations. No production use, performance benchmarks, or business impact is claimed. No license has been selected; the parent repository's licensing status applies.
