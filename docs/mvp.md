# MVP scope

## Goal

A job seeker can sign in, save an IT opportunity, prepare a reviewed resume draft,
and track the application. Each account's data remains private.

The C# / ASP.NET Core stack was explicitly selected. The career-dashboard product
direction follows the owner's earlier requests.

## Implemented in the draft branch

1. Foundation: Identity accounts, SQL Server configuration, initial migration, CI.
2. Job tracking: private CRUD, counts, filters, status-change history, employer links.
3. Resumes: private base-text CRUD, independent drafts, immutable source snapshots,
   and text downloads.

## Remaining v0.1 milestones

4. AI: provider abstraction, truthful tailoring, skill gaps, timeouts/rate limits.
5. Release: email confirmation/recovery, deployment, browser/accessibility review.

## Acceptance criteria

- Two independent accounts register and sign in.
- Saved data survives a host restart.
- Cross-account reads, edits, deletions, and downloads fail.
- Mutations require POST and antiforgery protection.
- Submitted owner IDs cannot override authenticated ownership.
- Source edits/deletions do not rewrite existing draft snapshots.
- Editing a draft leaves its base resume unchanged.
- Actual status changes append history in the same transaction.
- Applied is user-confirmed, never inferred from opening an employer URL.
- AI failures preserve records; ordinary tracking works without AI credentials.

Automated coverage includes these implemented behaviors against SQLite and/or SQL
Server. Visual browser usability is still a release check.

## Data design

IdentityUser owns JobApplication, Resume, and ResumeDraft.
ApplicationStatusHistory belongs to a job and is queried through job ownership.
Draft provenance IDs have no foreign keys to source jobs/resumes so snapshots
survive source deletion. Draft snapshots are never accepted from edit forms.
All entity mutations use validated input types rather than binding database entities.

## Excluded from v0.1

Automatic job submission, broad job scraping, external feeds, Google sign-in,
PDF/DOCX processing, email synchronization, and reminders.
