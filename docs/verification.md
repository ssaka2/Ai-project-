# Verification

The full-stack build passed on September 14, 2026:
[GitHub Actions run 34869758082](https://github.com/ssaka2/Ai-project-/actions/runs/34869758082).

Result: **45 tests passed, none failed or skipped; zero build warnings/errors;
zero dependency advisory findings**. The Docker deployment and restart check passed.
CI repeats these checks for subsequent code changes; consult the pull request's
latest run for its current commit.

## Database and account workflows

- SQL Server migration application, reapplication, and model/schema alignment.
- Existing-data migration upgrade, followed by successful editing.
- Real registration, email confirmation, password recovery, and login.
- Reused password-reset token rejection and five-attempt login lockout.
- Account deletion cascades to jobs, history, resumes, and draft snapshots.
- Real cookies and antiforgery; forged owner IDs cannot change ownership.
- Cross-account reads, writes, deletions, and downloads are rejected.
- Saved data persists across fresh application hosts and logins.
- Source editing/deletion preserves independent drafts and source snapshots.
- Status history records actual changes atomically.
- Stale HTTP edits preserve submitted text and return 409.
- Already-tracked competing database writers cannot overwrite jobs, resumes,
  or drafts; rejected job changes leave no stray history.

## Chromium browser workflow

A real Kestrel process, SQL Server, Chromium, and Mailpit SMTP inbox exercise
registration/confirmation, job validation and status changes, resume/draft editing,
stale-tab conflicts, text downloads, disabled-AI behavior, two-account isolation,
logout, password reset, and login. Widths of 1280 and 390 pixels are checked.
Inserted script text is escaped and no browser page errors occur.

This is automated workflow coverage, not a complete visual/accessibility audit.

## AI workflow and adapter

Fake-provider tests cover consent, ownership, separate suggestions, explicit
review/apply, model metadata, gaps, concurrent manual edits, stale acceptance,
provider failures, cancellation, deletion during generation, and request limits.

Fake HTTP tests cover the Responses API request contract, structured output,
store=false, input/response limits, incomplete/refusal/malformed responses,
401/429/500 handling, and timeouts without exposing provider response bodies.
No paid calls are made by CI.

## Full-stack packaging

CI builds the Docker image and self-contained migration bundle, starts the
Compose SQL Server/migration/SMTP/web services, checks database readiness and
the login page, restarts the web container, and checks readiness again.
The local stack uses persistent SQL Server and Data Protection volumes.

## Remaining release checks

No live OpenAI call or model-quality evaluation has been performed.
Fake tests cannot establish factual model output.

Public hosting, real SMTP-provider credentials/deliverability, production HTTPS
and proxy configuration, backup restore, additional browsers, and manual
keyboard/screen-reader review remain open. The dependency advisory scan covers
NuGet packages; it is not a full security audit or container-image vulnerability scan.

See [setup](full-stack-setup.md), [AI setup](ai-setup.md), and [backlog](backlog.md).

## Follow-up regression coverage

Deletion forms now submit the version that was reviewed. Stale confirmations and
changes committed by another database context return conflicts instead of deleting
newer work. Fresh confirmation still permits deletion.

The private JSON export requires sign-in and antiforgery, excludes authentication
secrets, disables caching, and scopes jobs, history, resumes, drafts, and suggestions
to the authenticated account. HTTP tests verify ownership and export completeness.
Browser workflows now include the export download and run on Chromium, Firefox,
and WebKit. See the current PR checks for these follow-up results.
