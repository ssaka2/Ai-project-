import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import office
import ai_staff


class AIStaffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'ai.db';self.app=office.Office(self.path)
        self.env=patch.dict('os.environ',{'AI_OFFICE_MODEL':'fixture-model'});self.env.start()
        self.task=self.app.mutate('tasks',{'title':'Draft plan','brief':'Synthetic facts only','agent':1})['tasks'][0]
        self.app.mutate('update',{'id':self.task['id'],'version':1,'status':'active'})
        self.data={'id':self.task['id'],'version':2}

    def tearDown(self):self.env.stop();self.tmp.cleanup()

    def test_draft_is_separate_idempotent_and_persistent(self):
        before=self.app.snapshot()['tasks']
        state=ai_staff.draft(self.app,self.data,office.utcnow,lambda m,p:'Synthetic draft')
        self.assertEqual(before,state['tasks'])
        self.assertIn('UNVERIFIED',state['ai_drafts'][0]['content'])
        state=ai_staff.draft(self.app,self.data,office.utcnow,lambda m,p:self.fail('Duplicate inference'))
        self.assertEqual(len(state['ai_drafts']),1)
        self.assertEqual(len(office.Office(self.path).snapshot()['ai_drafts']),1)

    def test_missing_runtime_and_invalid_results_do_not_mutate(self):
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':''}):
            with self.assertRaisesRegex(ValueError,'not configured'):ai_staff.draft(self.app,self.data,office.utcnow)
        for result in ('',None,'x'*18001):
            with self.assertRaises(ValueError):ai_staff.draft(self.app,self.data,office.utcnow,lambda m,p:result)
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        self.assertEqual(self.app.snapshot()['tasks'][0]['version'],2)

    def test_changed_task_during_generation_discards_result(self):
        def provider(model,prompt):
            self.app.mutate('update',{'id':self.task['id'],'version':2,'result':'New source notes'})
            return 'Outdated generated text'
        with self.assertRaises(ValueError):ai_staff.draft(self.app,self.data,office.utcnow,provider)
        self.assertEqual(self.app.snapshot()['ai_drafts'],[])
        self.assertEqual(self.app.snapshot()['tasks'][0]['result'],'New source notes')

    def test_all_30_roles_can_draft_without_changing_task_status(self):
        self.app.mutate('candidate-project',{'name':'Fixture case','profile':'Synthetic'})
        self.app.mutate('job-project',{'name':'Fixture opening'})
        roster=self.app.snapshot()['agents'];self.assertEqual(len(roster),30)
        for agent in roster:
            with self.subTest(role=agent['name']):
                task=self.app.mutate('tasks',{'title':'Fixture role draft','brief':'No real candidate facts','agent':agent['id']})['tasks'][0]
                self.app.mutate('update',{'id':task['id'],'version':1,'status':'active'})
                def provider(model,prompt):
                    self.assertEqual(json.loads(prompt)['staff']['name'],agent['name'])
                    return 'Synthetic response'
                state=ai_staff.draft(self.app,{'id':task['id'],'version':2},office.utcnow,provider)
                self.assertEqual(state['tasks'][0]['status'],'active')
        self.assertEqual(len(self.app.snapshot()['ai_drafts']),30)

    def test_http_adapter_contract_and_failure(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,limit):return b'{"done":true,"response":"fixture"}'
        with patch('ai_staff.build_opener') as factory:
            factory.return_value.open.return_value=Response()
            self.assertEqual(ai_staff.generate('fixture-model','test'),'fixture')
            request=factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,'http://127.0.0.1:11434/api/generate')
            self.assertFalse(json.loads(request.data)['stream'])
            factory.return_value.open.side_effect=TimeoutError()
            with self.assertRaisesRegex(ValueError,'No task status'):ai_staff.generate('fixture-model','test')

    def test_candidate_context_excludes_other_profiles(self):
        for name,cv in [('One','C# FACTS'),('Other','PRIVATE OTHER CV')]:
            candidate=self.app.mutate('candidate-project',{'name':name,'profile':'Fixture'})['projects'][0]['id']
            self.app.mutate('campaign',{'candidate':candidate,'revision':0,'boards':'fixture','titles':'Engineer','locations':'US','skills':'C#','resume':cv,'consent':True,'enabled':False})
            if name=='One':case=candidate
        task=next(t for t in self.app.snapshot()['tasks'] if t['project']==case and t['title']=='Complete candidate intake')
        self.app.mutate('update',{'id':task['id'],'version':1,'status':'active'})
        def provider(model,prompt):
            self.assertIn('C# FACTS',prompt);self.assertNotIn('PRIVATE OTHER CV',prompt)
            return 'Fixture'
        ai_staff.draft(self.app,{'id':task['id'],'version':2},office.utcnow,provider)
