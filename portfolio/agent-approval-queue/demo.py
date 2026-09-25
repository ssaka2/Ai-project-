"""Demonstrate approval and one-time consumption without external side effects."""
import json
from pathlib import Path
import tempfile
from approvals import ApprovalQueue

with tempfile.TemporaryDirectory() as directory:
    queue = ApprovalQueue(Path(directory) / 'demo.db')
    arguments = {'draft_id': 'synthetic-42', 'destination': 'demo-board'}
    request = queue.submit('demo-request', 'publish_draft', arguments)
    try:
        queue.consume(request['id'], 'publish_draft', arguments)
        raise AssertionError('Unapproved request was accepted')
    except ValueError:
        print('Unapproved execution blocked.')
    print('Demo simulates reviewer approval; it does not send or publish anything.')
    queue.decide(request['id'], True, 'demo-reviewer')
    print(json.dumps(queue.consume(request['id'], 'publish_draft', arguments), indent=2))
    print(json.dumps(queue.audit(request['id']), indent=2))
