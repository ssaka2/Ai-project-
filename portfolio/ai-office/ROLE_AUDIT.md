# Staff role audit — October 5, 2026

30 built-in roles verified with synthetic data. This audit establishes working task coordination and record-based chat, not autonomous job execution or placement success.

For every role, regression tests assign/reassign a task, run queued → active → review → done, check its chat attribution, and verify saved tasks and conversations after reopening the database. All 21 template stages are checked for the expected staff owner and prerequisite edges.

| Role | Template assignments | Execution |
| --- | --- | --- |
| Research | Available for manually assigned tasks | Manual tasks; automated records chat |
| Builder | Available for manually assigned tasks | Manual tasks; automated records chat |
| Reviewer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Planner | Available for manually assigned tasks | Manual tasks; automated records chat |
| Frontend Engineer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Backend Engineer | Available for manually assigned tasks | Manual tasks; automated records chat |
| QA Engineer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Security Reviewer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Data Analyst | Available for manually assigned tasks | Manual tasks; automated records chat |
| DevOps Engineer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Technical Writer | Available for manually assigned tasks | Manual tasks; automated records chat |
| Support Specialist | Available for manually assigned tasks | Manual tasks; automated records chat |
| Applications Manager | Set application preferences; Review the application report | Manual tasks; automated records chat |
| Job Discovery Team | Discover and verify an opening; Build the linked application pipeline | Manual tasks; automated records chat |
| Eligibility Team | Check eligibility and job fit | Manual tasks; automated records chat |
| CV Tailoring Team | Prepare the tailored CV | Manual tasks; automated records chat |
| Cover Letter Team | Prepare the cover letter | Manual tasks; automated records chat |
| Application QA Team | Review application and obtain approval | Manual tasks; automated records chat |
| Submission Team | Submit and record the outcome; Track response and follow-up; Review the active application campaign | Manual tasks; automated records chat |
| Follow-up Team | Available for manually assigned tasks | Manual tasks; automated records chat |
| Placement Manager | Record the candidate offer decision | Manual tasks; automated records chat |
| Candidate Intake Team | Complete candidate intake | Manual tasks; automated records chat |
| US Location Coordinator | Confirm US location preferences | Manual tasks; automated records chat |
| Employer Requirements Team | Map employer requirements | Manual tasks; automated records chat |
| Profile and Portfolio Team | Prepare the candidate profile | Manual tasks; automated records chat |
| Skills Development Team | Prepare the skills and interview plan | Manual tasks; automated records chat |
| Interview Coaching Team | Coordinate interviews and feedback | Manual tasks; automated records chat |
| Offer Coordination Team | Review a written offer with the candidate | Manual tasks; automated records chat |
| Onboarding Team | Coordinate onboarding and confirm job start | Manual tasks; automated records chat |
| Candidate Success Team | Follow up after the confirmed start | Manual tasks; automated records chat |

## Automated assistance and remaining gaps

- Configured Greenhouse discovery and keyword screening run while the local server is open. This is one shared worker, not 30 autonomous workers.
- CV preparation selects exact excerpts and preserves the supplied master CV. It does not independently write or verify qualifications.
- Chat reads stored statuses, evidence timestamps, next checks, and open tasks; it does not contact staff, employers, or portals.
- Submission, inbox monitoring, employer outreach, interviewing, offer decisions, and onboarding actions require manual execution or future authorized integrations.
- Follow-up Team and general engineering roles have no default recruiting-template tasks; they remain assignable. Zero assigned work is explicitly reported, not represented as completed work.

## Fixed in this audit

Case-insensitive team lookup prevents new workflow creation from duplicating a team after a capitalization-only rename. Existing instructions and task ownership remain intact. Existing pre-existing duplicate rows are not merged or deleted automatically.
