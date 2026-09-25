# Agent Approval Queue

A local Python service layer and CLI for reviewing an agent's proposed tool call before a trusted executor uses it. Requests, reviewer decisions, and consumption events persist in SQLite. Every request starts pending; an approval is bound to the exact tool and canonical JSON arguments, expires, and can be consumed once.

## Why this project

Agent tools can cause changes outside the model. This project demonstrates the state management behind explicit review: idempotent submissions, terminal denial, argument binding, expiration, and atomic consumption under concurrent workers. It follows the human-review theme in the [MCP tools specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx), but it is not an MCP server or an agent SDK plugin.

## Quick demo

Requires Python 3.11+; no pip dependencies. From the repository root:

```sh
python portfolio/agent-approval-queue/demo.py
python -m unittest discover -s portfolio/agent-approval-queue -v
```

The demo uses a temporary database and a synthetic publish request. It shows a blocked unapproved call, simulates a reviewer decision, consumes the approval, and prints the history. It never publishes or sends anything.

## Review a request yourself

From this project folder:

```sh
python approvals.py submit --key draft-42 --tool publish_draft --arguments '{"draft_id":"demo-42"}' --ttl 600
# Replace REQUEST_ID below with the returned id.
python approvals.py show REQUEST_ID
python approvals.py approve REQUEST_ID --reviewer demo-reviewer
python approvals.py consume REQUEST_ID --tool publish_draft --arguments '{"draft_id":"demo-42"}'
python approvals.py audit REQUEST_ID
```

Use `deny` instead of `approve` to reject a pending request. `--db` is a global option, placed before the command. Windows shells may require different JSON quoting; the Python demo avoids shell-quoting differences.

The same idempotency key with the same payload returns the original request. Changing the payload under that key fails. Retrying a submission never extends its expiration. Repeated approval decisions or consumption fail. `show` distinguishes stored `state` from time-dependent `effective_state`.

## State and integration

`pending → approved → consumed`, or `pending → denied`. Pending and approved requests become unusable at their expiry time. SQLite transactions serialize competing decisions and consumption; the concurrency test verifies exactly one winner among eight workers.

A trusted application imports `ApprovalQueue`, submits a request, presents the stored arguments to its reviewer, then calls `consume` immediately before its own executor dispatches those same arguments. The returned payload is the reviewed payload. Failed argument matching does not consume the approval. The executor must enforce this path itself.

## Verification and limits

Nine automated tests cover required review, payload changes, denial, expiry before/after approval, idempotency collision, restart persistence, history, concurrent consumption, and invalid input. CI runs this suite on Python 3.11–3.14.

This is a local coordination component, not an authorization boundary against an attacker. Anyone with database or CLI access can act as a reviewer; reviewer labels are not authenticated identities. The history is transactional but not tamper-proof. No real tool is executed. Consuming an approval and executing an external action are not one transaction: a crash can consume an approval without completing the action. An execution system needs its own idempotency and reconciliation. Use a trusted clock and protect the database; do not store secrets in request arguments. There is no web UI, hosted endpoint, or production deployment.
