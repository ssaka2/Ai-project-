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

    def test_job_workflow_all_handoffs_and_reopening(self):
        state = self.office.mutate('job-project', {'name':'Example company - Engineer'})
        self.assertEqual(len(state['agents']), 20)
        tasks = sorted([t for t in state['tasks'] if t['project']], key=lambda t:t['id'])
        self.assertEqual(len(tasks), 9)
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
