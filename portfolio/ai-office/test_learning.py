import tempfile
import unittest
from pathlib import Path
from contextlib import closing
import office
import application_learning as learning


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'learning.db';self.app=office.Office(self.path)
        self.candidate=self.app.mutate('candidate-project',{'name':'Synthetic candidate','profile':'Test only'})['projects'][0]['id']
        self.projects=[]
        for n in range(2):
            p=self.app.mutate('job-project',{'name':f'Test opening {n}','candidate':self.candidate})['projects'][0]['id'];self.projects.append(p)
            self.app.mutate('application-identity',{'project':p,'candidate':self.candidate,'employer':'example.com','requisition':str(n)})
        self.owner=self.app.snapshot()['agents'][0]['id']
        self.reject()

    def tearDown(self):self.tmp.cleanup()

    def reject(self):
        checks=[c for c in self.app.snapshot()['checks'] if c['project']==self.projects[0]]
        self.check=self.app.mutate('application-check',{'project':self.projects[0],'revision':checks[0]['id'] if checks else 0,'status':'rejected','evidence':'Synthetic rejection; no employer reason','checked_at':office.utcnow()})['checks'][0]['id']

    def review(self,**kw):
        return self.app.mutate('rejection-review',{'check_id':self.check,'owner':self.owner,'basis':'unknown','reason':'No reason supplied','corrective_action':'Verify role requirements and factual CV accuracy; do not infer why rejected',**kw})

    def gate(self):
        with closing(self.app.connect()) as db:learning.gate(db,self.projects[1])

    def preflight(self,revision):
        return self.app.mutate('application-preflight',{'project':self.projects[1],'review_revision':revision,'owner':self.owner,'evidence':'Synthetic check of all applicable lessons, CV and answers'})

    def test_review_preflight_and_new_lessons_invalidate(self):
        with self.assertRaisesRegex(ValueError,'pending rejection'):self.gate()
        revision=self.review()['rejection_reviews'][0]['id']
        with self.assertRaisesRegex(ValueError,'fresh corrective'):self.gate()
        self.preflight(revision);self.gate()
        self.reject()
        with self.assertRaises(ValueError):self.gate()
        newer=self.review(basis='employer_feedback',reason='Synthetic employer feedback reference')['rejection_reviews'][0]['id']
        with self.assertRaises(office.Conflict):self.preflight(revision)
        self.preflight(newer);self.gate()
        self.assertEqual(len(office.Office(self.path).snapshot()['rejection_reviews']),2)

    def test_duplicate_invalid_review_and_pending_preflight(self):
        with self.assertRaises(ValueError):self.preflight(0)
        for kw in ({'basis':'confirmed_by_ai'},{'reason':''},{'owner':True},{'corrective_action':''}):
            with self.assertRaises(ValueError):self.review(**kw)
        self.review()
        with self.assertRaises(office.Conflict):self.review()

    def test_other_candidate_not_blocked(self):
        other=self.app.mutate('candidate-project',{'name':'Other','profile':'Synthetic'})['projects'][0]['id']
        p=self.app.mutate('job-project',{'name':'Other opening','candidate':other})['projects'][0]['id']
        self.app.mutate('application-identity',{'project':p,'candidate':other,'employer':'example.com','requisition':'other'})
        with closing(self.app.connect()) as db:learning.gate(db,p)

    def test_submission_task_gate_and_observations_remain_recordable(self):
        tasks=sorted([t for t in self.app.snapshot()['tasks'] if t['project']==self.projects[1]],key=lambda t:t['id'])
        for task in tasks[:6]:
            for version,status in enumerate(('active','review','done'),1):
                self.app.mutate('update',{'id':task['id'],'version':version,'status':status,'result':'Synthetic review'})
        with self.assertRaisesRegex(ValueError,'pending rejection'):
            self.app.mutate('update',{'id':tasks[6]['id'],'version':1,'status':'active'})
        revision=self.review()['rejection_reviews'][0]['id'];self.preflight(revision)
        self.app.mutate('update',{'id':tasks[6]['id'],'version':1,'status':'active'})
        self.app.mutate('application-check',{'project':self.projects[1],'revision':0,'status':'blocked','evidence':'No actual submission connector','checked_at':office.utcnow()})
