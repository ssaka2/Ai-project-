import concurrent.futures
import tempfile
import unittest
from pathlib import Path
import office


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'office.sqlite3'
        self.app=office.Office(self.path)
        self.candidate=self.app.mutate('candidate-project',{'name':'Fixture candidate','profile':'Synthetic only'})['projects'][0]['id']
        self.first=self.app.mutate('job-project',{'name':'Portal A'})['projects'][0]['id']
        self.second=self.app.mutate('job-project',{'name':'Portal B'})['projects'][0]['id']

    def tearDown(self):self.tmp.cleanup()

    def identity(self,project,**kw):
        return self.app.mutate('application-identity',{'project':project,'candidate':self.candidate,'employer':'Example.COM','requisition':'REQ-1',**kw})

    def test_cross_portal_identity_normalization_and_restart(self):
        self.identity(self.first)
        self.identity(self.first,employer='www.example.com.',requisition='  req-1  ')
        with self.assertRaises(office.Conflict):self.identity(self.second,requisition='ＲＥＱ-１')
        self.assertEqual(len(office.Office(self.path).snapshot()['application_identities']),1)
        second=next(p for p in self.app.snapshot()['projects'] if p['id']==self.second)
        self.assertIsNone(second['candidate'])
        with self.assertRaises(office.Conflict):self.identity(self.first,requisition='different')

    def test_distinct_candidate_or_requisition_allowed(self):
        self.identity(self.first)
        self.identity(self.second,requisition='REQ-2')
        another=self.app.mutate('candidate-project',{'name':'Other candidate','profile':'Synthetic'})['projects'][0]['id']
        third=self.app.mutate('job-project',{'name':'Other application'})['projects'][0]['id']
        self.identity(third,candidate=another)
        self.assertEqual(len(self.app.snapshot()['application_identities']),3)

    def test_concurrent_registration_only_one_wins(self):
        def register(project):
            try:self.identity(project);return 'saved'
            except office.Conflict:return 'duplicate'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(register,[self.first,self.second])),['saved','duplicate'])
        self.assertEqual(len(self.app.snapshot()['application_identities']),1)

    def test_legacy_submission_fails_closed_but_history_updates_work(self):
        payload={'project':self.first,'revision':0,'status':'submitted','evidence':'Synthetic receipt','checked_at':office.utcnow()}
        with self.assertRaises(ValueError):self.app.mutate('application-check',payload)
        task=next(t for t in self.app.snapshot()['tasks'] if t['project']==self.first and t['title']=='Submit and record the outcome')
        with self.assertRaisesRegex(ValueError,'Register candidate'):
            self.app.mutate('update',{'id':task['id'],'version':1,'status':'active'})
        self.identity(self.first)
        state=self.app.mutate('application-check',payload)
        self.app.mutate('application-check',{**payload,'revision':state['checks'][0]['id'],'checked_at':office.utcnow()})
        self.assertEqual(len(self.app.snapshot()['application_identities']),1)
        self.assertEqual(len(self.app.snapshot()['checks']),2)
        with self.assertRaises(office.Conflict):self.identity(self.second)

    def test_invalid_identity_and_candidate_reassignment_rejected(self):
        for override in ({'employer':'https://example.com'},{'requisition':''},{'candidate':True},{'project':self.candidate}):
            with self.assertRaises(ValueError):
                self.app.mutate('application-identity',{'project':self.first,'candidate':self.candidate,'employer':'example.com','requisition':'1',**override})
        self.assertEqual(self.app.snapshot()['application_identities'],[])
