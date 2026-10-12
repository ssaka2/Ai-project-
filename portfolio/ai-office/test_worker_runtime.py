import unittest
from contextlib import closing
from unittest.mock import patch
import sqlite3
import worker_store as store
from worker_test_support import fixture
try:
    import worker_runtime as runtime
except ImportError:runtime=None


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(runtime,'Worker dispatcher is not implemented')
        self.app,self.candidate,self.tasks=fixture(self)
        with closing(self.app.connect()) as db,db:
            db.execute('INSERT INTO automation_settings(candidate_id,enabled,portfolio,updated) VALUES (?,1,?,100)',(self.candidate,'Verified synthetic API project https://example.com/demo'))
            # Isolate CV execution. Other executors are separately bound/tested.
            db.execute('DELETE FROM worker_bindings WHERE task_id!=?',(self.tasks[3]['id'],))
        self.now=100.

    def tick(self, provider=lambda m,p:'Synthetic verified-input draft'):
        runtime.enqueue_eligible(self.app,now=self.now)
        return runtime.run_once(self.app,now_fn=lambda:self.now,provider=provider)

    def rows(self):return store.list_runs(self.app,candidate_id=self.candidate)['runs']

    def test_duplicate_ticks_persist_one_draft_without_approval(self):
        calls=[]
        self.tick(lambda m,p:calls.append(p) or 'Synthetic draft')
        self.assertFalse(self.tick(lambda m,p:self.fail('Duplicate inference')))
        self.assertEqual(len(calls),1);self.assertEqual(len(self.app.snapshot()['ai_drafts']),1)
        self.assertEqual(self.rows()[0]['state'],'succeeded')
        self.assertEqual(next(t for t in self.app.snapshot()['tasks'] if t['id']==self.tasks[3]['id'])['status'],'active')
        self.assertEqual(len(type(self.app)(self.app.path).snapshot()['ai_drafts']),1)

    def test_transient_timeout_stops_after_three_attempts(self):
        def timeout(m,p):raise TimeoutError('private upstream content')
        for now,expected in [(100,'retry_wait'),(130,'retry_wait'),(250,'failed')]:
            self.now=now;self.tick(timeout);self.assertEqual(self.rows()[0]['state'],expected)
        self.assertEqual(self.rows()[0]['attempts'],3)
        self.assertEqual(self.rows()[0]['error_code'],'provider_timeout')
        self.now=1000;self.assertFalse(self.tick(timeout))

    def test_pause_during_call_discards_output(self):
        def pause(m,p):
            with closing(self.app.connect()) as db,db:db.execute('UPDATE automation_settings SET enabled=0,revision=revision+1')
            return 'Must not persist'
        self.tick(pause)
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        self.assertEqual(self.rows()[0]['state'],'blocked')

    def test_shutdown_during_call_retries_after_database_reopen(self):
        import threading
        stop=threading.Event()
        runtime.enqueue_eligible(self.app,now=self.now)
        def interrupted(m,p):
            stop.set()
            return 'Shutdown output must not be saved'
        runtime.run_once(self.app,now_fn=lambda:self.now,provider=interrupted,stop=stop)
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        row=self.rows()[0]
        self.assertEqual((row['state'],row['error_code']),('retry_wait','shutdown_interrupted'))
        self.assertEqual(row['attempts'],1)
        self.app=type(self.app)(self.app.path)
        runtime.enqueue_eligible(self.app,now=self.now)
        self.assertFalse(runtime.run_once(self.app,now_fn=lambda:self.now,
            provider=lambda m,p:self.fail('Retry backoff must be respected'),stop=threading.Event()))
        self.now=row['due_at']
        self.assertTrue(runtime.run_once(self.app,now_fn=lambda:self.now,
            provider=lambda m,p:'Completed after restart',stop=threading.Event()))
        row=self.rows()[0]
        self.assertEqual((row['state'],row['attempts']),('succeeded',2))
        drafts=self.app.snapshot()['ai_drafts']
        self.assertEqual(len(drafts),1)
        self.assertTrue(drafts[0]['content'].endswith('Completed after restart'))

    def test_edit_during_call_discards_output(self):
        def edit(m,p):
            task=next(t for t in self.app.snapshot()['tasks'] if t['id']==self.tasks[3]['id'])
            self.app.mutate('update',{'id':task['id'],'version':task['version'],'result':'Changed facts'})
            return 'Must not persist'
        self.tick(edit);self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        self.assertEqual(self.rows()[0]['error_code'],'inputs_changed')

    def test_missing_model_and_invalid_output_block(self):
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':''}):
            self.tick(lambda m,p:self.fail('Unconfigured inference'))
        self.assertEqual(self.rows()[0]['error_code'],'model_not_configured')
        self.tick(lambda m,p:'')
        self.assertEqual(self.rows()[0]['state'],'blocked')
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])

    def test_maximum_length_cached_draft_is_reused_without_inference(self):
        self.tick(lambda m,p:'x'*18000)
        with closing(self.app.connect()) as db,db:
            db.execute('UPDATE automation_settings SET revision=revision+1')
        self.tick(lambda m,p:self.fail('Cached source must not repeat inference'))
        self.assertEqual(self.rows()[0]['state'],'succeeded')
        self.assertEqual(len(self.app.snapshot()['ai_drafts']),1)
        self.assertTrue(self.app.snapshot()['ai_drafts'][0]['content'].endswith('x'*18000))

    def test_oversized_combined_context_records_actionable_blocker(self):
        # Each component is within its supported 20k limit; combined JSON exceeds 60k.
        with closing(self.app.connect()) as db,db:
            db.execute('UPDATE recruiting_campaigns SET resume=? WHERE candidate=?',('r'*19999,self.candidate))
            db.execute('UPDATE tasks SET brief=? WHERE id=?',('j'*19999,self.tasks[3]['id']))
            db.execute('UPDATE tasks SET result=? WHERE id=?',('e'*19999,self.tasks[2]['id']))
        self.tick(lambda m,p:self.fail('Oversized context must not reach the model'))
        self.assertEqual(len(self.rows()),1)
        self.assertEqual(self.rows()[0]['state'],'blocked')
        self.assertEqual(self.rows()[0]['error_code'],'context_too_large')
        self.assertFalse(self.tick(lambda m,p:self.fail('Blocked task must not spin')))

    def test_model_lock_does_not_consume_attempt(self):
        import ai_staff
        runtime.enqueue_eligible(self.app,now=self.now)
        with ai_staff.LOCK:self.assertFalse(runtime.run_once(self.app,now_fn=lambda:self.now,provider=lambda m,p:''))
        self.assertEqual(self.rows()[0]['attempts'],0)

    def test_stop_states_and_expired_lease(self):
        import recruiting
        for status in recruiting.STOP_STATES:
            with self.subTest(status=status):
                with closing(self.app.connect()) as db,db:
                    db.execute('INSERT INTO application_checks(project,status,evidence,checked_at,recorded_at) VALUES (?,?,?,?,?)',(self.candidate,status,'Fixture','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00'))
                self.assertEqual(runtime.enqueue_eligible(self.app,now=100),0)
        with closing(self.app.connect()) as db,db:db.execute('DELETE FROM application_checks WHERE project=?',(self.candidate,))
        def expire(m,p):self.now=341;return 'Too late'
        self.tick(expire)
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        store.recover_expired(self.app,now=341)
        self.assertEqual(self.rows()[0]['state'],'retry_wait')

    def test_expiry_during_finalization_rolls_back_artifact(self):
        runtime.enqueue_eligible(self.app,now=100)
        clock=iter([100,339,341])
        runtime.run_once(self.app,now_fn=lambda:next(clock,341),provider=lambda m,p:'Synthetic output')
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        self.assertNotEqual(self.rows()[0]['state'],'succeeded')

    def test_recovery_service_survives_database_busy(self):
        import threading
        stop=threading.Event();calls=[]
        def scan(*a,**kw):
            calls.append(1)
            if len(calls)==1:raise sqlite3.OperationalError('database is locked')
            stop.set()
            return 0
        with patch.object(runtime,'enqueue_eligible',scan):runtime.serve(self.app,stop)
        self.assertEqual(len(calls),2)

if __name__=='__main__':unittest.main()
