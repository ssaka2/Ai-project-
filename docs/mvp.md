# MVP scope and milestones

## Working product direction

AI Career Desk follows the owner's earlier career-dashboard goal. C# / ASP.NET Core
was explicitly selected. The product direction was carried forward as a working
assumption when no alternative was selected.

## Goal

A job seeker can sign in, save an IT opportunity, prepare a reviewed resume draft,
and track their application in one place. Each account's data is private.

## Milestones

1. Foundation: accounts, SQL Server, reviewed migrations, CI.
2. Job tracking: CRUD, filters, dashboard counts, status history.
3. Resumes: base text, independent drafts, source snapshots.
4. AI: provider abstraction, truthful tailoring, skill gaps, timeout/rate-limit handling.
5. Release: email/account recovery, deployment, two-account end-to-end verification.

The foundation branch implements account configuration and basic job tracking.
Migrations, status history, resumes, and AI remain outstanding.

## Acceptance criteria

- Two users can register and sign in independently.
- A saved job survives an application restart.
- Reading, editing, or deleting another user's job by ID fails.
- Dashboard counts match the signed-in user's records.
- All mutations use POST and antiforgery protection.
- Applied is a user-confirmed status, never inferred from opening a URL.
- Tailored drafts leave the base resume unchanged and retain source snapshots.
- AI failures preserve existing records and show a retryable error.
- No AI API key is needed for ordinary job tracking.

## Data design

Implemented: IdentityUser and JobApplication, linked by OwnerId.
Planned: Resume, TailoredResume, ApplicationStatusHistory.
Drafts will include resume/job-description snapshots and provider/model metadata.
Every query and mutation must enforce ownership through the authenticated user.

## Excluded from v0.1

Automated applications, broad job scraping, external job feeds, Google sign-in,
PDF/DOCX parsing and export, email synchronization, and scheduled reminders.

## Verification before release

Build and automated tests must pass. Run the SQL Server smoke test in backlog.md
and test the full workflow in a browser with two accounts. Do not treat SQLite
tests as evidence that SQL Server setup or registration works end to end.
