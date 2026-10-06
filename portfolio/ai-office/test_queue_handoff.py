import concurrent.futures
import unittest
import test_recruiting
import office

class HandoffTests(unittest.TestCase):
    setUp=test_recruiting.RecruitingTests.setUp
    tearDown=test_recruiting.RecruitingTests.tearDown
    due=test_recruiting.RecruitingTests.due
    scan=test_recruiting.RecruitingTests.scan

    def payload(self):
        return dict(candidate=self.candidate,board='example',job_id='124')

    def ready(self):
        self.scan([self.job])
        self.scan([self.job,dict(self.job,id='124',description='C# SQL Server '+('full requirements ' * 2000)+'END')])

    def test_complete_context_and_queued_tasks_survive_restart(self):
        self.ready()
        state=self.app.mutate('queue-workflow',dict(self.payload(),description='Forged description',candidate_name='ignored'))
        link=state['recruiting_workflows'][0]
        project=next(p for p in state['projects'] if p['id']==link['project'])
        self.assertEqual(project['candidate'],self.candidate)
        tasks=[t for t in state['tasks'] if t['project']==project['id']]
        self.assertEqual(len(tasks),10)
        self.assertEqual(len({t['agent'] for t in tasks}),9)
        for task in tasks:
            self.assertEqual(task['status'],'queued')
            self.assertIn('END',task['brief'])
            self.assertIn('First observed:',task['brief'])
            self.assertNotIn('Forged description',task['brief'])
        self.assertEqual(state['checks'],[])
        self.assertEqual(office.Office(self.app.path).snapshot()['recruiting_workflows'],state['recruiting_workflows'])

    def test_concurrent_duplicate_handoff_creates_one_project(self):
        self.ready()
        def create():
            try:self.app.mutate('queue-workflow',self.payload());return 'created'
            except office.Conflict:return 'duplicate'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes=list(pool.map(lambda _:create(),range(2)))
        self.assertCountEqual(outcomes,['created','duplicate'])
        state=self.app.snapshot()
        self.assertEqual(len(state['projects']),2)
        self.assertEqual(len(state['recruiting_workflows']),1)

    def test_baseline_missing_stale_and_stopped_are_rejected(self):
        self.ready()
        for payload in (dict(self.payload(),job_id='123'),dict(self.payload(),job_id='missing'),dict(self.payload(),candidate=True)):
            with self.assertRaises(ValueError):self.app.mutate('queue-workflow',payload)
        self.app.mutate('campaign',dict(self.config,revision=1))
        with self.assertRaises(ValueError):self.app.mutate('queue-workflow',self.payload())
        self.assertEqual(self.app.snapshot()['recruiting_workflows'],[])
        self.assertEqual(len(self.app.snapshot()['projects']),1)

    def test_stopped_candidate_cannot_promote_matching_job(self):
        self.ready()
        self.app.mutate('application-check',dict(project=self.candidate,revision=0,status='paused',evidence='Test pause',checked_at=office.utcnow()))
        with self.assertRaisesRegex(ValueError,'stopped'):
            self.app.mutate('queue-workflow',self.payload())

if __name__=='__main__':unittest.main()
