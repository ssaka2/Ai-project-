# Candidate recruiting office: implementation plan and current capability

The goal is accountable support from intake through a confirmed job start. Employment is an employer/candidate decision; this system cannot offer a 100% placement guarantee or guarantee that a rejection will not recur.

| Stage | Accountable staff | Current implementation | Remaining work |
| --- | --- | --- | --- |
| Intake and preferences | Placement Manager, Candidate Intake, US Location Coordinator | Candidate cases, manually recorded consent/preferences | Private candidate accounts and structured approved profile/document storage |
| New openings | Job Discovery | Recurring configured Greenhouse boards; first-scan baseline and per-board ID deduplication | Additional permitted feeds, cross-source identity resolution, closing-date verification |
| CV and fit | CV Tailoring, Eligibility, Employer Requirements, Profile and Portfolio | Exact CV excerpt preparation, keyword screen, manual review tasks | Structured factual CV editing, document export, authenticated model adapter if desired, complete eligibility checks |
| Quality control | Application QA, Applications Manager | Review dependencies, duplicate identity registration, rejection review and corrective checks | Secure independent approver identity, immutable versioned application packages |
| Apply | Submission Team | Manual task, unique application record, recorded receipt/status | Authorized provider-specific submit adapter, required-answer validation, idempotent delivery and uncertain-outcome reconciliation |
| Track | Submission Team | Manual timestamped status evidence and next checks | Authenticated inbox/portal adapter, message-to-application matching and evidence retention |
| Learn from rejection | Named review owner, QA, Applications Manager | Evidence-labelled rejection review; subsequent submission starts require current corrective check | Automated evidence ingestion and manager review reminders; outcome evaluation without assuming causality |
| Interviews and offers | Interview Coaching, Offer Coordination | Manual workflow and recorded status | Authorized calendar/email integration; candidate-approved scheduling and offer decisions |
| Start and follow-up | Onboarding, Candidate Success | Accepted and started are separate; manual start confirmation | Secure onboarding document channels and follow-up reminders |

## Rejection improvement rules implemented

1. Record actual rejection evidence in the application status desk. A rejection alone does not establish a mistake or its cause.
2. Review the observation with an assigned staff owner. Use employer feedback, hypothesis, or unknown. Record the source and a corrective action or verification step. Never invent missing qualifications or turn an unconfirmed explanation into a fact.
3. Before starting another submission task for that candidate, complete pending rejection reviews and record a per-application corrective check against all current lessons. Explain the changes or why a lesson is inapplicable.
4. New review records invalidate older corrective checks. Another candidate's lessons do not block unrelated submissions. Records are append-only; duplicate reviews of one observation are rejected.
5. Discovery continues during rejection/interview states. Accepted, started, paused, or withdrawn candidate cases stop discovery. An accepted offer is not proof of an actual start.

The gate controls starting the template submission task. It does not send applications or block recording real observations, including actions performed outside the workspace. It does not stop an already-active submission task or independently verify the truth of reviewer notes. If corrections are discovered after submission begins, the manager must pause and review that work. Existing preflights certify only the recorded review version, not a cryptographic CV/package version; versioned packages remain planned.

## Integration assessment

GitHub publishes and verifies the code. Outlook Email was found in the plugin directory but is not connected; it could help inspect authorized status emails in this conversation after connection. A ChatGPT connection does not automatically authenticate the standalone app. Runtime OAuth, candidate-specific permissions, secret storage and polling still need implementation. The plugin search did not return a direct job-application submission integration; directory results are not exhaustive. Unrelated plugins were not installed.

Do not deploy the current loopback development server as a public staffing portal. Authentication, server-side candidate isolation, protected storage and production hosting are prerequisites for remote candidate access. Current tests use synthetic data; none establishes live applications, actual employer feedback ingestion, or guaranteed placements.


## AI runtime increment

An optional local Ollama adapter now generates drafts for active tasks across all staff roles. It has no action tools, stores unverified text separately, and preserves human review and submission gates. This does not replace the unimplemented authenticated submit/inbox adapters, production candidate accounts, or actual model installation. See README for configuration and tested limits.
