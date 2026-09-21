import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from jobs import claim, connect, enqueue, finish, work_once


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'jobs.db')
        self.db = connect(self.path)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def add(self, max_attempts=3):
        return enqueue(self.db, 'demo', 'word_count', {'text': 'one two'}, max_attempts, now=0)

    def test_enqueue_is_idempotent_and_conflicts_rejected(self):
        self.assertEqual(self.add(), self.add())
        with self.assertRaises(ValueError):
            enqueue(self.db, 'demo', 'word_count', {'text': 'different'})

    def test_success_and_persistence(self):
        self.add()
        result = work_once(self.db)
        self.assertEqual(result['result'], {'words': 2})
        self.db.close()
        self.db = connect(self.path)
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'succeeded')
        self.assertFalse(work_once(self.db)['worked'])

    def test_competing_workers_claim_job_once(self):
        self.add()
        def worker(_):
            db = connect(self.path)
            try:
                return claim(db, now=0)
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(job is not None for job in pool.map(worker, range(2))), 1)

    def test_expired_lease_recovered_and_stale_worker_rejected(self):
        identifier = self.add()
        old = claim(self.db, lease_seconds=5, now=0)
        newer = claim(self.db, now=5)
        self.assertNotEqual(old['token'], newer['token'])
        self.assertEqual(newer['attempts'], 2)
        with self.assertRaises(ValueError):
            finish(self.db, identifier, old['token'], result={}, now=6)
        self.assertEqual(finish(self.db, identifier, newer['token'], result={}, now=6), 'succeeded')

    def test_expired_lease_cannot_finish_before_reclaim(self):
        identifier = self.add()
        job = claim(self.db, lease_seconds=5, now=0)
        with self.assertRaises(ValueError):
            finish(self.db, identifier, job['token'], result={}, now=5)

    def test_retry_backoff_and_dead_letter(self):
        identifier = self.add(max_attempts=2)
        job = claim(self.db, now=0)
        self.assertEqual(finish(self.db, identifier, job['token'], error='failed', now=1), 'pending')
        self.assertIsNone(claim(self.db, now=2))
        job = claim(self.db, now=3)
        self.assertEqual(finish(self.db, identifier, job['token'], error='failed again', now=4), 'dead')
        self.assertIsNone(claim(self.db, now=100))

    def test_exhausted_crashed_job_becomes_dead(self):
        self.add(max_attempts=1)
        claim(self.db, lease_seconds=1, now=0)
        self.assertIsNone(claim(self.db, now=1))
        self.assertEqual(self.db.execute('SELECT state FROM jobs').fetchone()[0], 'dead')

    def test_unknown_token_and_double_completion_rejected(self):
        identifier = self.add()
        job = claim(self.db, now=0)
        with self.assertRaises(ValueError):
            finish(self.db, identifier, 'wrong', now=1)
        finish(self.db, identifier, job['token'], result={}, now=1)
        with self.assertRaises(ValueError):
            finish(self.db, identifier, job['token'], result={}, now=2)

    def test_input_validation(self):
        for key, kind, payload, attempts in [('', 'sha256', {'text': ''}, 1),
                ('x', 'shell', {'text': ''}, 1), ('x', 'sha256', {'text': 1}, 1),
                ('x', 'sha256', {'text': ''}, 0)]:
            with self.assertRaises(ValueError):
                enqueue(self.db, key, kind, payload, attempts)


if __name__ == '__main__':
    unittest.main()
