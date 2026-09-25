from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from approvals import ApprovalQueue


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1000
        self.path = Path(self.temp.name) / 'queue.db'
        self.queue = ApprovalQueue(self.path, lambda: self.now)
        self.args = {'destination': 'demo', 'body': 'synthetic draft'}

    def submit(self):
        return self.queue.submit('request-1', 'publish_draft', self.args, ttl=60)['id']

    def test_approval_required(self):
        request = self.submit()
        with self.assertRaises(ValueError):
            self.queue.consume(request, 'publish_draft', self.args)
        self.queue.decide(request, True, 'reviewer')
        self.assertEqual(self.queue.consume(request, 'publish_draft', self.args)['arguments'], self.args)
        with self.assertRaises(ValueError):
            self.queue.consume(request, 'publish_draft', self.args)

    def test_arguments_bound_exactly(self):
        request = self.submit()
        self.queue.decide(request, True, 'reviewer')
        with self.assertRaises(ValueError):
            self.queue.consume(request, 'publish_draft', self.args | {'destination': 'other'})
        self.assertEqual(self.queue.get(request)['state'], 'approved')

    def test_denial_is_terminal(self):
        request = self.submit()
        self.queue.decide(request, False, 'reviewer')
        for action in (lambda: self.queue.consume(request, 'publish_draft', self.args), lambda: self.queue.decide(request, True, 'other')):
            with self.assertRaises(ValueError):
                action()

    def test_expiry_applies_after_approval(self):
        request = self.submit()
        self.queue.decide(request, True, 'reviewer')
        self.now += 60
        self.assertEqual(self.queue.get(request)['effective_state'], 'expired')
        with self.assertRaises(ValueError):
            self.queue.consume(request, 'publish_draft', self.args)

    def test_expired_pending_cannot_approve(self):
        request = self.submit()
        self.now += 61
        with self.assertRaises(ValueError):
            self.queue.decide(request, True, 'reviewer')

    def test_idempotency_and_collision(self):
        request = self.submit()
        self.assertEqual(self.submit(), request)
        with self.assertRaises(ValueError):
            self.queue.submit('request-1', 'other', {})
        self.assertEqual(len(self.queue.audit(request)), 1)

    def test_restart_and_audit(self):
        request = self.submit()
        self.queue.decide(request, True, 'Alice')
        restarted = ApprovalQueue(self.path, lambda: self.now)
        restarted.consume(request, 'publish_draft', self.args)
        self.assertEqual([e['action'] for e in restarted.audit(request)], ['submitted', 'approved', 'consumed'])

    def test_concurrent_consumption_has_one_winner(self):
        request = self.submit()
        self.queue.decide(request, True, 'reviewer')
        def consume(_):
            try:
                self.queue.consume(request, 'publish_draft', self.args)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(sum(pool.map(consume, range(8))), 1)

    def test_invalid_inputs(self):
        for arguments in ([1], {'score': float('nan')}, {'text': 'x'*17000}):
            with self.assertRaises(ValueError):
                self.queue.submit('bad', 'tool', arguments)
        with self.assertRaises(ValueError):
            self.queue.submit('bad', 'tool', {}, ttl=0)


if __name__ == '__main__':
    unittest.main()
