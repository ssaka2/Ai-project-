# Implementation backlog

These are drafted tasks, not published GitHub issues.

## Completed in the draft branch

- ASP.NET Core accounts and private job CRUD.
- Dashboard filters and counts.
- Initial SQL Server migration and model snapshot.
- SQL Server registration, ownership, persistence, and antiforgery workflow tests.
- Transactional status-change history.
- Base resumes, independent drafts, immutable source snapshots, and text downloads.
- Optional AI suggestions with separate storage, source consent, gap summaries, and review/apply.
- Bounded responses, timeouts, cancellation, per-user and concurrency limits.
- Optimistic concurrency for manual draft saves and AI acceptance.

## 1. Configure and evaluate live AI (P1)

The OpenAI adapter is implemented and disabled by default. Configure a supported
model and server-side key using ai-setup.md. Run a small synthetic evaluation:
ordinary resume, missing qualification, irrelevant job, prompt injection in source
text, and long input. Review every generated claim against its source.

Acceptance: account/model compatibility and representative output quality are
documented. No fabricated qualifications in reviewed examples. Do not interpret
fake-provider tests as proof of model factuality.

## 2. Email confirmation and recovery (P0 before public hosting)

Configure email delivery, RequireConfirmedAccount, confirmation links,
password reset, failed-login lockout behavior, and account deletion.
Decide and document snapshot retention on account deletion.

Acceptance: a new user confirms email, logs in, resets a password, and deletes
their account and associated records. Expired/reused tokens fail.

## 3. Concurrent edit protection (P1 before multiple active users)

Draft edits and AI acceptance now have concurrency tokens. Extend protection to
job and base-resume edits. Return a conflict screen
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
where supported. AI suggestions and automatic application submission are separate features.

## Manual review checklist

1. Follow README setup against a fresh SQL Server database.
2. Register two synthetic accounts and save distinct jobs/resumes.
3. Update job statuses and inspect their timestamps.
4. Create, edit, and download a draft; verify the base resume is unchanged.
5. Edit/delete the source records; verify the draft snapshots remain.
6. Try another account's direct URLs and verify access is denied.
7. Check validation, keyboard use, narrow layouts, and deletion confirmation.
