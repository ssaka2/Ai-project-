# Application automation

The dashboard supports case-insensitive search by job title, company and location, combined with status filters. Download filtered applications as CSV for a spreadsheet; potential formula cells are neutralized. Downloads are private to the signed-in owner and are not cached.

Follow-ups are calculated whenever you open the page: Applied records are due seven days after their last update; Interviewing records after three days. Other statuses never enter the queue. Due dates use UTC. Any edit, including recording a follow-up in notes, restarts the interval. These are suggested dates, not employer deadlines.

Each due application has a deterministic draft for review and copying. No paid AI, background worker, email schedule or automatic application submission is used. No messages are sent. Existing email confirmation and login requirements remain in place. No database migration is required.

After deployment: sign in, save an application, search for it, export it and check the Follow-ups page. Verify another account cannot see it. SMTP setup must still be completed before the existing production app can start.
