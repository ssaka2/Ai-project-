# Verification

The build and SQL Server test suite passed during implementation on September 14, 2026:
https://github.com/ssaka2/Ai-project-/actions/runs/34862312707

Result: 20 tests passed, none skipped; build had zero warnings and errors.
The generated initial migration was then reviewed and committed. Subsequent CI
runs validate that committed migrations match the model before running the suite.

## What is exercised

- SQL Server initial migration, safe reapplication, and model/schema alignment.
- Real registration, login, cookies, and antiforgery tokens.
- Two accounts with private jobs and resumes.
- Cross-account GET and POST rejection, including draft downloads.
- Submitted OwnerId values cannot replace authenticated ownership.
- Fresh host plus fresh login retrieves existing data.
- Draft editing leaves base text unchanged.
- Original source snapshots survive source deletion.
- SQLite tests additionally exercise source edits and exact status-history behavior.
- Public pages render; protected pages redirect anonymous users.

## Remaining verification

No visual browser or accessibility review was performed. Email delivery,
confirmation/recovery, AI generation, and production deployment are not tested
because they are not implemented/configured. See backlog.md for release gates.
