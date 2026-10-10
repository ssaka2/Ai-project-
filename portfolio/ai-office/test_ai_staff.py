import json
import tempfile
import unittest
from io import BytesIO
from urllib.error import HTTPError, URLError
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

    def test_cached_draft_rejects_changed_role_and_model(self):
        ai_staff.draft(self.app,self.data,office.utcnow,lambda m,p:'Original draft')
        self.app.mutate('agents',{'id':1,'name':'Research','role':'Changed task instructions'})
        with self.assertRaisesRegex(ValueError,'stale'):
            ai_staff.draft(self.app,self.data,office.utcnow,lambda m,p:self.fail('Should require new task version'))
        self.app.mutate('update',{'id':self.task['id'],'version':2,'result':'Refreshed source'})
        ai_staff.draft(self.app,{'id':self.task['id'],'version':3},office.utcnow,lambda m,p:'Fresh draft')
        with patch.dict('os.environ',{'AI_OFFICE_MODEL':'different-model'}):
            with self.assertRaisesRegex(ValueError,'stale'):
                ai_staff.draft(self.app,{'id':self.task['id'],'version':3},office.utcnow)
        self.assertEqual(len(self.app.snapshot()['ai_drafts']),2)

    def test_legacy_draft_is_preserved_but_not_trusted_as_current(self):
        from contextlib import closing
        with closing(self.app.connect()) as db,db:
            db.execute('INSERT INTO ai_drafts(task,task_version,model,content,created) VALUES (?,?,?,?,?)',
                       (self.task['id'],2,'fixture-model','Legacy draft',office.utcnow()))
        reopened=office.Office(self.path)
        with self.assertRaisesRegex(ValueError,'stale'):
            ai_staff.draft(reopened,self.data,office.utcnow)
        self.assertEqual(reopened.snapshot()['ai_drafts'][0]['content'],'Legacy draft')

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

    def test_incomplete_generation_never_saves_and_releases_lock(self):
        before=self.app.snapshot()['tasks']
        for body in ({'done':True,'done_reason':'length','response':'Cut off'},
                     {'done':False,'response':'Partial'},
                     {'done':True,'done_reason':'error','response':'Incomplete'},
                     {'done':True,'response':''}, ['invalid']):
            with self.subTest(body=body), patch('ai_staff.build_opener') as factory:
                factory.return_value.open.return_value=BytesIO(json.dumps(body).encode())
                with self.assertRaisesRegex(ValueError,'No draft was saved'):
                    ai_staff.draft(self.app,self.data,office.utcnow)
                self.assertEqual(self.app.snapshot()['ai_drafts'],[])
                self.assertEqual(self.app.snapshot()['tasks'],before)
        with patch('ai_staff.build_opener') as factory:
            factory.return_value.open.return_value=BytesIO(b'{"done":true,"done_reason":"stop","response":"Complete fixture"}')
            self.assertEqual(len(ai_staff.draft(self.app,self.data,office.utcnow)['ai_drafts']),1)

    def test_transport_failures_have_safe_actionable_messages(self):
        cases=[(TimeoutError(),'timed out'),(URLError(TimeoutError()),'timed out'),
               (URLError('private details'),'Cannot reach'),
               (HTTPError('http://localhost',404,'private details',None,None),'not found'),
               (HTTPError('http://localhost',500,'private details',None,None),'rejected')]
        for error,message in cases:
            with self.subTest(error=error),patch('ai_staff.build_opener') as factory:
                factory.return_value.open.side_effect=error
                with self.assertRaisesRegex(ValueError,message) as caught:
                    ai_staff.draft(self.app,self.data,office.utcnow)
                self.assertNotIn('private details',str(caught.exception))
                self.assertEqual(self.app.snapshot()['ai_drafts'],[])

    def test_generation_timeout_configuration(self):
        with patch.dict('os.environ',{'AI_OFFICE_GENERATION_TIMEOUT':'90'}),patch('ai_staff.build_opener') as factory:
            factory.return_value.open.return_value=BytesIO(b'{"done":true,"response":"fixture"}')
            ai_staff.generate('fixture','test')
            self.assertEqual(factory.return_value.open.call_args.kwargs['timeout'],90)
        for invalid in ('0','151','NaN','1.5'):
            with patch.dict('os.environ',{'AI_OFFICE_GENERATION_TIMEOUT':invalid}),patch('ai_staff.build_opener') as factory:
                with self.assertRaisesRegex(ValueError,'5 to 150'):ai_staff.generate('fixture','test')
                factory.assert_not_called()

    def test_malformed_response_is_not_saved(self):
        for raw in (b'not json',b'\xff',b'x'*250001):
            with patch('ai_staff.build_opener') as factory:
                factory.return_value.open.return_value=BytesIO(raw)
                with self.assertRaisesRegex(ValueError,'No draft was saved'):
                    ai_staff.draft(self.app,self.data,office.utcnow)
                self.assertEqual(self.app.snapshot()['ai_drafts'],[])
