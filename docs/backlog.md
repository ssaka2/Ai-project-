# Next implementation tasks

Tasks are ordered by dependency. These are drafted tasks, not published GitHub issues.

## 1. Commit the initial EF Core migration (P0)

Replace the development EnsureCreated bootstrap with migration-based initialization.
Generate the migration and snapshot with dotnet-ef 10.0.12 against the current model.
Review the SQL and apply to a fresh SQL Server test database.
Update setup instructions and remove the development bootstrap switch.

Acceptance: a fresh database can be initialized using dotnet ef database update;
rerunning applies no changes; Identity and job CRUD work against SQL Server.
Existing disposable bootstrap databases must not be migrated in place.

## 2. Add SQL Server and authenticated HTTP integration coverage (P0)

Exercise registration/sign-in with real antiforgery tokens and cookies.
Use two users and verify cross-account GET, edit POST, and delete POST fail.
Check database persistence after application restart.

Acceptance: a CI SQL Server job proves these behaviors, including attempted
OwnerId overposting. No test credentials become application defaults.

## 3. Add application status history (P1)

Record old/new status and UTC timestamp in the same transaction as the job update.
Render the history on the job page. Define applied-date behavior on repeated transitions.

Acceptance: a changed status creates exactly one event, unchanged status creates none,
and another user cannot read the history.

## 4. Store base resumes and draft snapshots (P1)

Add owner-scoped resume CRUD for pasted text. Add TailoredResume with an immutable
source resume snapshot, job-description snapshot, and editable generated text.

Acceptance: editing a draft never changes its base resume; deleting or editing source
records does not destroy the evidence used for an existing draft.

## 5. Implement resume tailoring (P1; depends on 4)

Select an AI provider and implement IResumeTailoringService plus a fake for tests.
Return draft text and missing-skill observations. Keep credentials server-side.
Treat pasted content as data; restrict input/output lengths, rate-limit requests,
handle cancellation/timeouts, and do not log resume bodies.

Acceptance: no fabricated qualifications in reviewed examples; errors preserve
existing drafts; the core dashboard works without provider credentials.

## 6. Prepare hosting and account recovery (P0 before public release)

Configure email delivery, confirmed accounts, password recovery, AllowedHosts,
HTTPS, persistent Data Protection keys, secrets, backups, and deployment migrations.

Acceptance: a new user can confirm their email, sign in, reset a password, and retain
access after a deployment restart. A documented rollback exists.

## Manual smoke test for this branch

1. Use a fresh disposable SQL Server database and follow the README.
2. Register Alice and Bob with synthetic addresses and strong passwords.
3. Alice saves a job and notes, then changes Saved to Applied.
4. Restart the app and verify Alice's job persists.
5. Bob sees an empty dashboard. Alice's edit/delete URLs return 404 for Bob.
6. Invalid URLs such as javascript:alert(1) are rejected.
7. Delete uses a confirmation page and requires a POST.
8. Verify sign-out and mobile-width page layout.

AI and resume acceptance tests are added when those features exist.
