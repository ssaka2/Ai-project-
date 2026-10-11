import tempfile
import threading
import time
import unittest
from pathlib import Path
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import office
try:
    import worker_store as store
except ImportError:
    store = None


class WorkerStoreTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(store, 'Durable worker store is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = office.Office(Path(self.tmp.name)/'office.db')
        self.candidate = self.app.mutate('candidate-project', {'name':'Synthetic','profile':'Fixture'})['projects'][0]['id']
        self.task = self.app.snapshot()['tasks'][0]['id']

    def enqueue(self, fingerprint='abc', executor='cv_draft'):
        return store.enqueue(self.app,task_id=self.task,task_version=1,candidate_id=self.candidate,
                             executor=executor,fingerprint=fingerprint,now=100)

    def test_unique_run_and_single_concurrent_claim(self):
        one=self.enqueue(); self.assertEqual(one['id'], self.enqueue()['id'])
        with ThreadPoolExecutor(2) as pool:
            claims=list(pool.map(lambda _:store.claim(self.app,now=100),range(2)))
        run=next(x for x in claims if x)
        self.assertEqual(sum(x is not None for x in claims),1)
        self.assertEqual(run['lease_expires_at'],340)
        self.assertEqual(run['attempts'],1)
        self.assertEqual(len(office.Office(self.app.path).snapshot()['tasks']),12)

    def test_retries_are_bounded_and_old_leases_cannot_finish(self):
        self.enqueue()
        for now,due in [(100,130),(130,250),(250,None)]:
            run=store.claim(self.app,now=now)
            self.assertTrue(store.finish(self.app,run['id'],run['lease_token'],state='retry_wait',now=now,error_code='timeout'))
            self.assertFalse(store.finish(self.app,run['id'],run['lease_token'],state='succeeded',now=now))
            saved=store.list_runs(self.app,candidate_id=self.candidate)['runs'][0]
            self.assertEqual(saved['state'],'failed' if due is None else 'retry_wait')
            if due: self.assertEqual(saved['due_at'],due)
        self.assertEqual(saved['attempts'],3)
        self.assertIsNone(store.claim(self.app,now=1000))

    def test_expiry_recovery_and_renewal(self):
        self.enqueue(); run=store.claim(self.app,now=100)
        self.assertTrue(store.renew(self.app,run['id'],run['lease_token'],now=130))
        self.assertEqual(store.recover_expired(self.app,now=340),0)
        self.assertEqual(store.recover_expired(self.app,now=371),1)
        self.assertFalse(store.finish(self.app,run['id'],run['lease_token'],state='succeeded',now=371))
        self.enqueue('other','submission')
        claimed=store.claim(self.app,now=371)
        self.assertEqual(claimed['executor'],'submission')
        store.recover_expired(self.app,now=612)
        rows=store.list_runs(self.app,candidate_id=self.candidate)['runs']
        self.assertEqual(rows[0]['state'],'unknown_outcome')

    def test_contended_renewal_cannot_revive_expired_lease(self):
        self.enqueue();run=store.claim(self.app,now=time.time())
        with closing(self.app.connect()) as lock,lock:
            lock.execute('UPDATE worker_runs SET lease_expires_at=? WHERE id=?',(time.time()+0.10,run['id']))
        started=threading.Event()
        with closing(self.app.connect()) as lock:
            lock.execute('BEGIN IMMEDIATE')
            def renew():
                now=time.time();started.set()
                return store.renew(self.app,run['id'],run['lease_token'],now=now)
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(renew)
                self.assertTrue(started.wait(2));time.sleep(.30)
                lock.rollback()
                self.assertFalse(future.result(timeout=2))
        self.assertEqual(store.recover_expired(self.app,now=time.time()),1)

    def test_contended_finish_rejects_expired_lease(self):
        self.enqueue();run=store.claim(self.app,now=time.time())
        with closing(self.app.connect()) as db,db:
            db.execute('UPDATE worker_runs SET lease_expires_at=? WHERE id=?',(time.time()+.10,run['id']))
        started=threading.Event()
        with closing(self.app.connect()) as lock:
            lock.execute('BEGIN IMMEDIATE')
            def finish():
                now=time.time();started.set()
                return store.finish(self.app,run['id'],run['lease_token'],state='blocked',now=now)
            with ThreadPoolExecutor(1) as pool:
                future=pool.submit(finish);self.assertTrue(started.wait(2));time.sleep(.30);lock.rollback()
                self.assertFalse(future.result(timeout=2))

    def test_pagination_validation_and_additive_migration(self):
        for n in range(4):self.enqueue(str(n))
        first=store.list_runs(self.app,candidate_id=self.candidate,limit=2)
        second=store.list_runs(self.app,candidate_id=self.candidate,limit=2,before_id=first['next_cursor'])
        self.assertFalse({r['id'] for r in first['runs']} & {r['id'] for r in second['runs']})
        with self.assertRaises(ValueError):store.list_runs(self.app,candidate_id=True)
        with self.assertRaises(ValueError):store.list_runs(self.app,candidate_id=self.candidate,limit=101)
        before=self.app.snapshot();office.Office(self.app.path);office.Office(self.app.path)
        self.assertEqual(before,self.app.snapshot())

if __name__=='__main__':unittest.main()
