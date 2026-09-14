# Implementation backlog

These are drafted tasks, not published GitHub issues.

## Completed in the draft branch

- ASP.NET Core accounts and private job CRUD.
- Dashboard filters and counts.
- Initial SQL Server migration and model snapshot.
- SQL Server registration, ownership, persistence, and antiforgery workflow tests.
- Transactional status-change history.
- Base resumes, independent drafts, immutable source snapshots, and text downloads.

## 1. AI resume tailoring (P1)

Choose a provider and implement IResumeTailoringService plus a fake for tests.
Use saved source snapshots to request a draft and a missing-skill summary.
Keep credentials server-side. Treat pasted content as data, enforce length limits,
rate-limit calls, support cancellation/timeouts, and avoid resume-content logging.
Save generation/provider/model metadata separately from user edits.

Acceptance: generation never silently overwrites user edits; reviewed examples
do not fabricate qualifications; provider failures preserve drafts; tracking
remains usable without an AI key. Fake-provider tests run without paid calls.

## 2. Email confirmation and recovery (P0 before public hosting)

Configure email delivery, RequireConfirmedAccount, confirmation links,
password reset, failed-login lockout behavior, and account deletion.
Decide and document snapshot retention on account deletion.

Acceptance: a new user confirms email, logs in, resets a password, and deletes
their account and associated records. Expired/reused tokens fail.

## 3. Concurrent edit protection (P1 before multiple active users)

Add concurrency tokens to job, resume, and draft edits. Return a conflict screen
that preserves the submitted text and lets the user compare current content.

Acceptance: two browser sessions cannot silently overwrite each other's changes.

## 4. Browser and accessibility review (P0 before release)

Check registration, validation messages, job filtering/history, resume editing,
snapshot expansion, downloads, and deletion on mobile and desktop.
Verify keyboard navigation, focus, labels, contrast, and screen-reader errors.

Acceptance: the complete workflow can be performed by keyboard at narrow widths.
Document tested browsers and any remaining limitations.

## 5. Deployment and operations (P0 before public hosting)

Choose hosting; configure production SQL Server, HTTPS, AllowedHosts, persistent
Data Protection keys, secret storage, reviewed migration deployment, and backups.
Define rollback and restore procedures. Do not use startup schema creation.

Acceptance: two accounts complete the workflow after a deployment restart;
a database restore is demonstrated in a non-production environment.

## Later

Google sign-in; job feeds; PDF/DOCX import/export; reminders; application automation
where supported. AI generation and automatic application submission are separate features.

## Manual review checklist

1. Follow README setup against a fresh SQL Server database.
2. Register two synthetic accounts and save distinct jobs/resumes.
3. Update job statuses and inspect their timestamps.
4. Create, edit, and download a draft; verify the base resume is unchanged.
5. Edit/delete the source records; verify the draft snapshots remain.
6. Try another account's direct URLs and verify access is denied.
7. Check validation, keyboard use, narrow layouts, and deletion confirmation.
