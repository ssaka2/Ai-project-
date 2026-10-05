import concurrent.futures
import importlib.util
import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

spec = importlib.util.spec_from_file_location('ai_office_app', Path(__file__).with_name('office.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class OfficeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite3'
        self.office = app.Office(self.path)
        self.task = self.office.mutate('tasks', {'title': 'Review', 'brief': 'Check evidence', 'agent': 1})['tasks'][0]

    def tearDown(self):
        self.tmp.cleanup()

    def update(self, **kwargs):
        payload = {'id': self.task['id'], 'version': self.task['version'], **kwargs}
        self.task = self.office.mutate('update', payload)['tasks'][0]
        return self.task

    def test_candidate_case_and_linked_applications(self):
        state = self.office.mutate('candidate-project', {'name':'Synthetic candidate', 'profile':'Test only: software roles; location preferences pending.'})
        case = state['projects'][0]['id']
        tasks = sorted((t for t in state['tasks'] if t['project']==case), key=lambda t:t['id'])
        self.assertEqual(len(tasks),12)
        self.assertIn('location preferences pending', tasks[0]['brief'])
        with self.assertRaises(ValueError):
            self.office.mutate('update', {'id':tasks[1]['id'],'version':1,'status':'active'})
        for task in tasks:
            for version,status in enumerate(('active','review','done'),1):
                self.office.mutate('update', {'id':task['id'],'version':version,'status':status,'result':'Synthetic workflow test evidence'})
        self.assertEqual(self.office.snapshot()['checks'], [])
        state = self.office.mutate('job-project', {'name':'Linked opening','candidate':case})
        self.assertEqual(state['projects'][0]['candidate'],case)
        self.assertEqual(app.Office(self.path).snapshot()['projects'][0]['candidate'],case)
        payload = {'project':case,'revision':0,'status':'searching','evidence':'Synthetic candidate-approved search','checked_at':'2026-01-01T00:00:00Z'}
        self.office.mutate('application-check',payload)
        with self.assertRaises(ValueError):
            self.office.mutate('application-check',{**payload,'revision':1,'status':'submitted'})
        with self.assertRaises(ValueError):
            self.office.mutate('job-project',{'name':'Bad link','candidate':state['projects'][0]['id']})
        self.assertEqual(len(self.office.snapshot()['projects']),2)

    def test_candidate_validation_is_atomic(self):
        before = self.office.snapshot()
        for profile in ('',None,'x'*5001):
            with self.assertRaises(ValueError):
                self.office.mutate('candidate-project', {'name':'Invalid','profile':profile})
        self.assertEqual(self.office.snapshot(),before)

    def test_review_lifecycle_and_restart(self):
        self.update(status='active')
        with self.assertRaises(ValueError): self.update(status='review')
        self.update(status='review', result='Checked with sources')
        self.update(status='done')
        fresh = app.Office(self.path).snapshot()
        self.assertEqual(fresh['tasks'][0]['status'], 'done')
        self.assertEqual(len(fresh['events']), 4)
        self.update(status='queued')

    def test_no_skip_review(self):
        with self.assertRaises(ValueError): self.update(status='done', result='x')
        self.assertEqual(len(self.office.snapshot()['events']), 1)

    def test_conflicting_concurrent_updates(self):
        payload = {'id': self.task['id'], 'version': 1, 'status': 'active'}
        def attempt(_):
            try: self.office.mutate('update', payload); return 'saved'
            except app.Conflict: return 'conflict'
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(pool.map(attempt, range(2)), ['saved', 'conflict'])
        self.assertEqual(len(self.office.snapshot()['events']), 2)

    def test_schedule_timezone_and_due_gate(self):
        self.task = self.office.mutate('tasks', {'title':'Future','brief':'Later','agent':1,'due':'2099-01-01T08:00:00+02:00'})['tasks'][0]
        self.assertTrue(self.task['due'].startswith('2099-01-01T06:00:00'))
        with self.assertRaises(ValueError): self.update(status='active')
        self.task = self.office.mutate('tasks', {'title':'Past','brief':'Now','agent':1,'due':'2000-01-01T08:00:00Z'})['tasks'][0]
        self.assertEqual(self.update(status='active')['status'], 'active')

    def test_bad_dates_and_references(self):
        for due in ['tomorrow', '2026-01-01', 5]:
            with self.assertRaises(ValueError): self.office.mutate('tasks', {'title':'x','brief':'y','agent':1,'due':due})
        for agent in [999, True, '1']:
            with self.assertRaises(ValueError): self.office.mutate('tasks', {'title':'x','brief':'y','agent':agent})
        self.assertEqual(len(self.office.snapshot()['tasks']), 1)

    def test_agent_creation_and_edit(self):
        state = self.office.mutate('agents', {'name':'Writer','role':'Cite all claims'})
        agent = state['agents'][-1]
        self.office.mutate('agents', {**agent, 'name':'Editor'})
        self.assertEqual(app.Office(self.path).snapshot()['agents'][-1]['name'], 'Editor')

    def test_specialist_migration_preserves_custom_staff(self):
        path = Path(self.tmp.name) / 'legacy.sqlite3'
        import sqlite3
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE agents(id INTEGER PRIMARY KEY,name TEXT NOT NULL,role TEXT NOT NULL)')
            db.execute("INSERT INTO agents VALUES (1,'My researcher','Keep this custom role')")
            db.execute("INSERT INTO agents VALUES (2,'Planner','My own planning instructions')")
        office = app.Office(path)
        agents = office.snapshot()['agents']
        self.assertEqual(agents[0]['role'], 'Keep this custom role')
        self.assertEqual(agents[1]['role'], 'My own planning instructions')
        self.assertEqual(len(agents), 10)
        office.mutate('agents', {'id': agents[-1]['id'], 'name':'Custom support', 'role':'Keep edits'})
        reopened = app.Office(path).snapshot()['agents']
        self.assertEqual(len(reopened), 10)
        self.assertEqual(reopened[-1]['name'], 'Custom support')
        self.assertEqual(len(self.office.snapshot()['agents']), 12)

    def test_reassignment_validation_history_and_conflict(self):
        agent = self.office.snapshot()['agents'][-1]['id']
        task = self.update(agent=agent)
        self.assertEqual(task['agent'], agent)
        self.assertIn('reassigned', self.office.snapshot()['events'][0]['message'])
        with self.assertRaises(app.Conflict):
            self.office.mutate('update', {'id':task['id'],'version':1,'agent':1})
        with self.assertRaises(ValueError): self.update(agent=99999)
        self.assertEqual(app.Office(self.path).snapshot()['tasks'][0]['agent'], agent)

    def protect(self,project):
        from contextlib import closing
        with closing(self.office.connect()) as db,db:
            candidate=db.execute("INSERT INTO projects(name,kind,created) VALUES ('Synthetic identity','candidate-placement',?)",(app.utcnow(),)).lastrowid
        self.office.mutate('application-identity',{'project':project,'candidate':candidate,'employer':'example.com','requisition':'TEST-1'})

    def test_job_workflow_all_handoffs_and_reopening(self):
        state = self.office.mutate('job-project', {'name':'Example company - Engineer'})
        self.protect(state['projects'][0]['id'])
        self.assertEqual(len(state['agents']), 20)
        tasks = sorted([t for t in state['tasks'] if t['project']], key=lambda t:t['id'])
        self.assertEqual(len(tasks), 9)
        self.assertEqual(tasks[6]['agent'], tasks[7]['agent'])
        self.assertEqual(len(state['dependencies']), 9)
        with self.assertRaises(ValueError):
            self.office.mutate('update', {'id':tasks[1]['id'], 'version':1, 'status':'active'})
        for task in tasks:
            for version, status in [(1,'active'), (2,'review'), (3,'done')]:
                self.office.mutate('update', {'id':task['id'], 'version':version, 'status':status, 'result':'Synthetic test evidence; no external action performed'})
        snapshot = app.Office(self.path).snapshot()
        self.assertTrue(all(t['status']=='done' for t in snapshot['tasks'] if t['project']))
        with self.assertRaises(ValueError):
            self.office.mutate('update', {'id':tasks[0]['id'], 'version':4, 'status':'queued'})
        with self.assertRaises(ValueError):
            self.office.mutate('update', {'id':tasks[0]['id'], 'version':4, 'result':'Changed after downstream approval'})
        # Rework must move backwards through the dependency chain.
        for task in reversed(tasks):
            self.office.mutate('update', {'id':task['id'], 'version':4, 'status':'queued'})
        self.assertTrue(all(t['status']=='queued' for t in self.office.snapshot()['tasks'] if t['project']))

    def test_duplicate_projects_atomic_and_teams_reused(self):
        self.office.mutate('job-project', {'name':'Opening A'})
        with self.assertRaises(app.Conflict): self.office.mutate('job-project', {'name':'opening a'})
        self.assertEqual(len(self.office.snapshot()['projects']), 1)
        self.assertEqual(len(self.office.snapshot()['tasks']), 10)
        self.office.mutate('job-project', {'name':'Opening B'})
        state = self.office.snapshot()
        self.assertEqual(len(state['agents']), 20)
        self.assertEqual(len(state['projects']), 2)
        self.assertEqual(len(state['tasks']), 19)

    def test_status_owner_upgrade_preserves_existing_work(self):
        from contextlib import closing
        state = self.office.mutate('job-project', {'name':'Legacy opening'})
        tasks = sorted([t for t in state['tasks'] if t['project']], key=lambda t:t['id'])
        followup = next(a for a in state['agents'] if a['name']=='Follow-up Team')['id']
        with closing(self.office.connect()) as db, db:
            db.execute("DELETE FROM migrations WHERE name='submission-status-owner-v1'")
            db.execute('UPDATE tasks SET agent=?,result=? WHERE id=?', (followup, 'Keep my notes', tasks[7]['id']))
        updated = app.Office(self.path).snapshot()
        status_task = next(t for t in updated['tasks'] if t['id']==tasks[7]['id'])
        self.assertEqual(status_task['agent'], tasks[6]['agent'])
        self.assertEqual(status_task['result'], 'Keep my notes')
        self.assertEqual(status_task['version'], 2)
        self.assertIn('next check date', status_task['brief'])
        again = app.Office(self.path).snapshot()
        self.assertEqual(next(t for t in again['tasks'] if t['id']==status_task['id'])['version'], 2)
        with self.assertRaises(app.Conflict):
            self.office.mutate('update', {'id':status_task['id'], 'version':1, 'agent':followup})

    def test_application_evidence_history_and_conflicts(self):
        project = self.office.mutate('job-project', {'name':'Status test'})['projects'][0]['id']
        self.protect(project)
        data = {'project':project,'revision':0,'status':'submitted','evidence':'Synthetic receipt R1',
                'checked_at':'2026-01-01T10:00:00Z','next_check':'2026-01-02T10:00:00Z'}
        state = self.office.mutate('application-check', data)
        check = state['checks'][0]
        self.assertEqual(check['status'], 'submitted')
        self.assertTrue(all(t['status']=='queued' for t in state['tasks']))
        with self.assertRaises(app.Conflict): self.office.mutate('application-check', data)
        self.office.mutate('application-check', {**data,'revision':check['id'],'status':'under_review',
                                               'evidence':'Synthetic portal status', 'checked_at':'2026-01-01T11:00:00Z'})
        saved = app.Office(self.path).snapshot()['checks']
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0]['status'], 'under_review')
        self.assertEqual(saved[1]['evidence'], 'Synthetic receipt R1')

    def test_status_validation_and_nonchronological_checks(self):
        project = self.office.mutate('job-project', {'name':'Validation test'})['projects'][0]['id']
        data = {'project':project,'revision':0,'status':'unknown','evidence':'Portal unavailable',
                'checked_at':'2026-01-01T10:00:00Z'}
        for override in [{'evidence':''},{'status':'made_up'},{'checked_at':'2099-01-01T00:00:00Z'},
                         {'checked_at':None},{'checked_at':'2026-01-01T10:00:00'},
                         {'next_check':'2026-01-01T09:00:00Z'},{'project':True},{'project':99999}]:
            with self.assertRaises(ValueError): self.office.mutate('application-check', {**data,**override})
        self.assertEqual(self.office.snapshot()['checks'], [])
        check = self.office.mutate('application-check', data)['checks'][0]
        with self.assertRaises(ValueError):
            self.office.mutate('application-check', {**data,'revision':check['id'],'checked_at':'2025-01-01T00:00:00Z'})
        self.assertEqual(len(self.office.snapshot()['checks']), 1)

    def test_input_limits(self):
        for title in ['', ' ', 'x'*201, 3, None]:
            with self.assertRaises(ValueError): self.office.mutate('tasks', {'title':title,'brief':'x','agent':1})
        with self.assertRaises(ValueError): self.office.mutate('tasks', [])
        with self.assertRaises(ValueError): self.update(result='x'*20001)


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = app.make_server(Path(self.tmp.name) / 'http.sqlite3', 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.get('/api/state')[1]['token']

    def tearDown(self):
        self.server.shutdown(); self.thread.join(); self.server.server_close(); self.tmp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response: return response.status, json.load(response)

    def post(self, path, data, headers=None):
        request = Request(self.base+path, json.dumps(data).encode(), headers={
            'Content-Type':'application/json', 'X-Office-Token':self.token, **(headers or {})})
        try:
            with urlopen(request) as response: return response.status, json.load(response)
        except HTTPError as response: return response.code, json.load(response)

    def test_http_workflow_export(self):
        code, state = self.post('/api/tasks', {'title':'API test','brief':'Verify HTTP','agent':1})
        self.assertEqual(code, 200)
        task = state['tasks'][0]
        self.assertEqual(self.post('/api/update', {'id':task['id'],'version':1,'status':'active'})[0], 200)
        self.assertEqual(self.post('/api/update', {'id':task['id'],'version':1,'status':'review'})[0], 409)
        _, export = self.get('/api/export')
        self.assertNotIn('token', export)
        self.assertEqual(export['tasks'][0]['status'], 'active')

    def test_status_http_and_export(self):
        _, state = self.post('/api/job-project', {'name':'HTTP status'})
        payload = {'project':state['projects'][0]['id'],'revision':0,'status':'blocked',
                   'evidence':'Synthetic portal sign-in needed','checked_at':'2026-01-01T00:00:00Z'}
        self.assertEqual(self.post('/api/application-check',payload,{'X-Office-Token':''})[0],403)
        self.assertEqual(self.post('/api/application-check',payload)[0],200)
        self.assertEqual(self.post('/api/application-check',payload)[0],409)
        self.assertEqual(self.get('/api/export')[1]['checks'][0]['status'],'blocked')

    def test_candidate_http_route(self):
        payload={'name':'HTTP candidate','profile':'Synthetic intake notes'}
        self.assertEqual(self.post('/api/candidate-project',payload,{'X-Office-Token':''})[0],403)
        code,state=self.post('/api/candidate-project',payload)
        self.assertEqual(code,200)
        self.assertEqual(state['projects'][0]['kind'],'candidate-placement')
        self.assertEqual(len(state['tasks']),12)
        self.assertEqual(self.post('/api/candidate-project',payload)[0],409)

    def test_hostile_inputs_return_errors_without_mutation(self):
        for agent in (10**100,-1):
            self.assertEqual(self.post('/api/tasks',{'title':'x','brief':'x','agent':agent})[0],400)
        for due in ('0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00'):
            self.assertEqual(self.post('/api/tasks',{'title':'x','brief':'x','agent':1,'due':due})[0],400)
        self.assertEqual(self.post('/api/discover',[])[0],400)
        self.assertEqual(self.post('/api/tasks',{}, {'X-Office-Token':'é'})[0],403)
        self.assertEqual(self.get('/api/state')[1]['tasks'],[])

    def test_deep_json_returns_400_and_server_recovers(self):
        request=Request(self.base+'/api/tasks',('['*1200+'0'+']'*1200).encode(),headers={
            'Content-Type':'application/json','X-Office-Token':self.token})
        with self.assertRaises(HTTPError) as error:urlopen(request)
        self.assertEqual(error.exception.code,400)
        self.assertEqual(self.get('/api/state')[1]['tasks'],[])

    def test_learning_routes_validate_and_require_token(self):
        for route in ('/api/rejection-review','/api/application-preflight'):
            self.assertEqual(self.post(route,{}, {'X-Office-Token':''})[0],403)
            self.assertEqual(self.post(route,{})[0],400)

    def test_staff_chat_http(self):
        _,state=self.post('/api/candidate-project',{'name':'Chat candidate','profile':'Synthetic'})
        data={'candidate':state['projects'][0]['id'],'agent':state['agents'][0]['id'],'question':'What is my status?'}
        self.assertEqual(self.post('/api/staff-chat',data,{'X-Office-Token':''})[0],403)
        code,state=self.post('/api/staff-chat',data)
        self.assertEqual(code,200)
        self.assertIn('No linked application',state['chats'][0]['answer'])
        self.assertEqual(self.post('/api/staff-chat',{**data,'question':''})[0],400)

    def test_duplicate_protection_http(self):
        _,state=self.post('/api/candidate-project',{'name':'Identity candidate','profile':'Synthetic'})
        candidate=state['projects'][0]['id']
        ids=[]
        for name in ('Portal A','Portal B'):
            _,state=self.post('/api/job-project',{'name':name})
            ids.append(state['projects'][0]['id'])
        payload={'project':ids[0],'candidate':candidate,'employer':'example.com','requisition':'R1'}
        self.assertEqual(self.post('/api/application-identity',payload,{'X-Office-Token':''})[0],403)
        self.assertEqual(self.post('/api/application-identity',payload)[0],200)
        self.assertEqual(self.post('/api/application-identity',{**payload,'project':ids[1]})[0],409)
        self.assertEqual(len(self.get('/api/export')[1]['application_identities']),1)

    def test_campaign_http_auth_and_validation(self):
        self.assertEqual(self.post('/api/campaign',{}, {'X-Office-Token':''})[0],403)
        self.assertEqual(self.post('/api/campaign',{})[0],400)
        self.assertEqual(self.post('/api/discover',{}, {'X-Office-Token':''})[0],403)
        self.assertEqual(self.post('/api/discover',{})[0],200)

    def test_project_http_route(self):
        code, state = self.post('/api/job-project', {'name':'HTTP opening'})
        self.assertEqual(code, 200)
        self.assertEqual(len(state['projects']), 1)
        self.assertEqual(len(state['tasks']), 9)
        self.assertEqual(self.post('/api/job-project', {'name':'HTTP opening'})[0], 409)
        self.assertEqual(self.post('/api/job-project', {'name':'   '})[0], 400)

    def test_cross_origin_and_missing_token(self):
        for headers in [{'X-Office-Token':''},{'Origin':'https://unrelated.example'},{'Host':'attacker.example'}]:
            self.assertEqual(self.post('/api/tasks', {}, headers)[0], 403)
        self.assertEqual(self.get('/api/state')[1]['tasks'], [])

    def test_errors_and_static_assets(self):
        self.assertEqual(self.post('/api/tasks', [])[0], 400)
        self.assertEqual(self.post('/api/unknown', {})[0], 404)
        for route, mime in [('/', 'text/html'),('/app.js', 'text/javascript'),('/style.css','text/css')]:
            with urlopen(self.base+route) as response:
                self.assertTrue(response.headers['Content-Type'].startswith(mime))
                self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
                self.assertGreater(len(response.read()), 100)
        with self.assertRaises(HTTPError) as error: urlopen(self.base+'/../office.py')
        self.assertEqual(error.exception.code, 404)


if __name__ == '__main__': unittest.main()
