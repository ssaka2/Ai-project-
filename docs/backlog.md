# Implementation backlog

## Implemented

Identity accounts; confirmation, recovery, lockout, and account deletion;
private job CRUD and status history; base resumes and independent drafts;
immutable source snapshots; text downloads; optional reviewed AI suggestions;
optimistic concurrency for all edit forms; SQL migrations; local Docker stack
with SMTP inbox and persisted data/keys; automated database, HTTP, browser,
dependency-audit, and deployment checks.

## 1. Evaluate live AI

Configure the model/key using [AI setup](ai-setup.md). Evaluate synthetic examples:
ordinary resume, missing qualifications, irrelevant job, prompt injection,
and long input. Compare every generated claim to the original.

Acceptance: model/account compatibility and reviewed output quality are recorded.
Fake-provider tests do not establish model factuality.

## 2. Complete manual accessibility review

Review keyboard focus/order, screen-reader labels and errors, contrast, zoom,
and narrow layouts. Automated Chromium workflows cover desktop/mobile widths,
but are not a complete accessibility audit. Add Firefox/WebKit verification.

Acceptance: registration, recovery, tracking, editing, review, and deletion are
usable by keyboard and with a screen reader; findings are resolved or documented.

## 3. Public deployment and operations

Choose hosting/domain and configure production HTTPS, trusted proxy handling,
AllowedHosts, SMTP credentials, SQL service/licensing, least-privileged app login,
secret storage, and protected persistent Data Protection keys.
Apply the migration bundle as a deployment task. Define retention and support.

Acceptance: two synthetic users complete the workflow after a deployment restart;
a nonproduction database restore is demonstrated; rollback is documented.
The local Compose stack is not the public hosting configuration.

## 4. Follow-up hardening

Before horizontal scaling, replace in-memory AI request limits with shared limits.
Review registration/recovery abuse controls for the public hosting environment.
Extend personal-data export to include job records and resume sources if needed.

## Later

Google sign-in; external job feeds; PDF/DOCX import/export; reminders.
Automatic submission is a separate feature requiring explicit product scope.
