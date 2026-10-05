import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import office
import recruiting


class RecruitingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=office.Office(Path(self.tmp.name)/'office.db')
        self.candidate=self.app.mutate('candidate-project',{'name':'Synthetic candidate','profile':'Fixture only'})['projects'][0]['id']
        self.config={'candidate':self.candidate,'revision':0,'boards':'example','titles':'Software Engineer',
                     'locations':'United States','skills':'C#, SQL Server','resume':'Test Person\nDeveloper, Example 2020–2023\nBuilt C# APIs using SQL Server.\nEducation: Example University',
                     'consent':True,'enabled':True}
        self.app.mutate('campaign',self.config)
        self.job={'id':'123','title':'Software Engineer','location':'United States','url':'https://example.com/jobs/123','description':'Build C# APIs and SQL Server services.'}

    def tearDown(self):
        self.tmp.cleanup()

    def due(self):
        with closing(self.app.connect()) as db,db:
            db.execute('UPDATE recruiting_campaigns SET next_run=NULL')

    def scan(self,jobs):
        self.due()
        recruiting.scan(self.app,lambda board:jobs)
        return self.app.snapshot()['job_queue']

    def test_baseline_new_jobs_and_no_duplicates(self):
        self.assertEqual(self.scan([self.job])[0]['outcome'],'baseline')
        newer={**self.job,'id':'124'}
        rows=self.scan([self.job,newer])
        self.assertEqual(len(rows),2)
        new=next(r for r in rows if r['job_id']=='124')
        self.assertEqual(new['outcome'],'blocked')
        self.assertIn(self.config['resume'],new['draft'])
        self.assertIn('No authorized submission connector',new['reason'])
        self.assertEqual(len(self.scan([self.job,newer])),2)
        self.assertEqual(self.app.snapshot()['checks'],[])
        self.assertEqual(len(office.Office(self.app.path).snapshot()['job_queue']),2)

    def test_filters_and_fact_preservation(self):
        self.scan([])
        rows=self.scan([{**self.job,'title':'Sales Representative','location':'London','description':'Python only'}])
        self.assertEqual(rows[0]['outcome'],'filtered')
        self.assertIn('Location',rows[0]['reason'])
        self.assertNotIn('Python',rows[0]['draft'])
        self.assertIn('Education: Example University',rows[0]['draft'])

    def test_failed_first_scan_does_not_create_baseline(self):
        def fail(board): raise TimeoutError('untrusted error content')
        recruiting.scan(self.app,fail)
        self.assertEqual(self.app.snapshot()['job_queue'],[])
        error=self.app.snapshot()['campaigns'][0]['error']
        self.assertIn('TimeoutError',error)
        self.assertNotIn('untrusted',error)
        self.assertEqual(self.scan([self.job])[0]['outcome'],'baseline')

    def test_stop_states_and_interview_continuation(self):
        for status in ('accepted','started','paused','withdrawn','interviewing'):
            state=self.app.snapshot()
            self.app.mutate('application-check',{'project':self.candidate,'revision':state['checks'][0]['id'] if state['checks'] else 0,'status':status,'evidence':'Synthetic evidence only','checked_at':office.utcnow()})
            self.due()
            calls=[]
            recruiting.scan(self.app,lambda board:calls.append(board) or [])
            self.assertEqual(len(calls),1 if status=='interviewing' else 0)

    def test_campaign_changes_require_review_and_stale_writes_fail(self):
        self.scan([]);self.scan([self.job])
        self.app.mutate('campaign',{**self.config,'revision':1,'resume':'Updated verified C# experience','enabled':False})
        self.assertEqual(self.app.snapshot()['job_queue'][0]['outcome'],'needs_review')
        with self.assertRaises(office.Conflict): self.app.mutate('campaign',self.config)
        calls=[]
        recruiting.scan(self.app,lambda board:calls.append(board) or [])
        self.assertEqual(calls,[])

    def test_profile_change_during_fetch_discards_results(self):
        self.scan([])
        def changed(board):
            self.app.mutate('campaign',{**self.config,'revision':1,'enabled':False})
            return [self.job]
        self.due();recruiting.scan(self.app,changed)
        self.assertEqual(self.app.snapshot()['job_queue'],[])

    def test_invalid_sources_and_missing_consent(self):
        for update in ({'boards':'https://localhost/test'},{'consent':False},{'resume':''},{'boards':'a,b,c,d,e,f'}):
            with self.assertRaises(ValueError):self.app.mutate('campaign',{**self.config,'revision':1,**update})
        self.assertEqual(self.app.snapshot()['campaigns'][0]['revision'],1)
        with self.assertRaises(ValueError):recruiting.fetch_board('../internal')

    def test_paused_campaign_does_not_report_fake_scan(self):
        self.app.mutate('application-check',{'project':self.candidate,'revision':0,'status':'paused','evidence':'Fixture pause','checked_at':office.utcnow()})
        before=self.app.snapshot()['campaigns'][0]
        self.due()
        def unexpected(board):self.fail('Paused campaign contacted source')
        recruiting.scan(self.app,unexpected)
        after=self.app.snapshot()['campaigns'][0]
        self.assertEqual(after['last_run'],before['last_run'])
        self.assertIsNone(after['next_run'])

    def test_source_transaction_rolls_back_partial_baseline(self):
        bad={**self.job,'id':'bad','location':None}
        self.assertEqual(self.scan([self.job,bad]),[])
        self.assertEqual(self.scan([self.job])[0]['outcome'],'baseline')

    def test_competing_scans_fetch_once(self):
        import concurrent.futures
        import threading
        entered,release=threading.Event(),threading.Event()
        calls=[]
        def fetch(board):
            calls.append(board);entered.set()
            if not release.wait(3):raise TimeoutError('test deadline')
            return [self.job]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(recruiting.scan,self.app,fetch)
            self.assertTrue(entered.wait(3))
            try:pool.submit(recruiting.scan,self.app,fetch).result(timeout=3)
            finally:release.set()
            first.result(timeout=3)
        self.assertEqual(calls,['example'])
        self.assertEqual(len(self.app.snapshot()['job_queue']),1)

    def test_redirect_and_malformed_source_rejected(self):
        with self.assertRaises(ValueError):
            recruiting.NoRedirect().redirect_request(None,None,302,'redirect',{},'http://127.0.0.1/')
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps({'jobs':[{'id':1,'internal_job_id':2,'title':'Engineer','content':'C#','location':None}]}).encode()
        with patch('recruiting.build_opener') as opener:
            opener.return_value.open.return_value=Response()
            with self.assertRaises(ValueError):recruiting.fetch_board('example')

    def test_provider_parser(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps({'jobs':[{'id':1,'internal_job_id':2,'title':'Engineer','location':{'name':'US'},'absolute_url':'https://example.com/1','content':'&lt;p&gt;C# APIs&lt;/p&gt;'}]}).encode()
        with patch('recruiting.build_opener') as opener:
            opener.return_value.open.return_value=Response()
            jobs=recruiting.fetch_board('example')
        self.assertEqual(jobs[0]['id'],'1')
        self.assertIn('C# APIs',jobs[0]['description'])
        self.assertNotIn('<p>',jobs[0]['description'])


if __name__=='__main__':unittest.main()
