"""Original local task office. Python 3.11+, no third-party runtime dependencies."""
import argparse
import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
STATUSES = ('queued', 'active', 'review', 'done')
SPECIALISTS = (
    ('Planner', 'Break briefs into scoped tasks and acceptance criteria'),
    ('Frontend Engineer', 'Build accessible interfaces and responsive layouts'),
    ('Backend Engineer', 'Design APIs, validation, and service boundaries'),
    ('QA Engineer', 'Test edge cases and document reproducible failures'),
    ('Security Reviewer', 'Review trust boundaries and sensitive data handling'),
    ('Data Analyst', 'Check data quality and explain analysis assumptions'),
    ('DevOps Engineer', 'Prepare reproducible builds and deployment checks'),
    ('Technical Writer', 'Write setup guides and document known limitations'),
    ('Support Specialist', 'Triage requests and capture clear reproduction steps'),
)

JOB_TEAMS = (
    ('Applications Manager', 'Define target roles, coordinate handoffs, and review campaign progress.'),
    ('Job Discovery Team', 'Record a current job URL and description from permitted sources; check duplicates.'),
    ('Eligibility Team', 'Check location, work authorization, sponsorship, requirements, and applicant preferences.'),
    ('CV Tailoring Team', 'Tailor the CV using verified applicant facts; never invent experience or qualifications.'),
    ('Cover Letter Team', 'Draft a role-specific cover letter grounded in verified applicant facts.'),
    ('Application QA Team', 'Check the job, CV, letter, missing answers, and applicant approval.'),
    ('Submission Team', 'Submit only after applicant approval; record an actual receipt or explain the blocker.'),
    ('Follow-up Team', 'Track responses and plan follow-ups without sending unsolicited messages.'),
)
# Index dependencies produce one explicit, auditable handoff graph.
JOB_STAGES = (
    (0, 'Set application preferences', 'Record target roles, locations, work authorization/sponsorship needs, and the verified master CV. Ask for missing facts.', ()),
    (1, 'Discover and verify an opening', 'Record one software job URL, company, role, job description, and closing date if known. Check that it is current and not already tracked. Use permitted sources only.', (0,)),
    (2, 'Check eligibility and job fit', 'Compare the opening with the applicant preferences and CV. Record verified matches, gaps, and unanswered questions. Do not assume work authorization or qualifications.', (1,)),
    (3, 'Prepare the tailored CV', 'Use only verified master-CV facts. Record the tailored document location and the changes made. Preserve dates, employers, credentials, and factual accuracy.', (2,)),
    (4, 'Prepare the cover letter', 'Draft a role-specific letter from verified facts. Record the draft or its location. Do not send it.', (2,)),
    (5, 'Review application and obtain approval', 'Check the exact CV, letter, destination, and application answers. Resolve missing data and record applicant approval for this application before handoff.', (3,4)),
    (6, 'Submit and record the outcome', 'Use an approved portal or permitted integration. This workspace cannot submit externally. Record the real confirmation/reference and submission date, or leave this task open with the blocker. Never claim a submission without evidence.', (5,)),
    (7, 'Track response and follow-up', 'Record the response or the next follow-up date and planned action. Sending a message is a separate action requiring authorization.', (6,)),
    (0, 'Review the application report', 'Review the submitted application evidence, response, and next action. Record unresolved issues and close this application workflow.', (7,)),
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def required(data, key, limit=200):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{key} must contain 1–{limit} characters')
    return value.strip()


def due_date(value):
    if value in (None, ''):
        return None
    if not isinstance(value, str):
        raise ValueError('due must be an ISO timestamp with timezone')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        raise ValueError('due must be an ISO timestamp with timezone') from None


class Office:
    def __init__(self, path):
        self.path = str(path)
        with closing(self.connect()) as db, db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript('''
                CREATE TABLE IF NOT EXISTS migrations(name TEXT PRIMARY KEY);
                CREATE TABLE IF NOT EXISTS projects(
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    kind TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS agents(
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks(
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL, brief TEXT NOT NULL,
                    agent INTEGER NOT NULL REFERENCES agents(id), due TEXT,
                    status TEXT NOT NULL DEFAULT 'queued', result TEXT NOT NULL DEFAULT '',
                    version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS dependencies(
                    task INTEGER NOT NULL REFERENCES tasks(id),
                    prerequisite INTEGER NOT NULL REFERENCES tasks(id),
                    PRIMARY KEY(task, prerequisite));
                CREATE TABLE IF NOT EXISTS events(
                    id INTEGER PRIMARY KEY, task INTEGER REFERENCES tasks(id),
                    message TEXT NOT NULL, created TEXT NOT NULL);
            ''')
            if 'project' not in [r['name'] for r in db.execute('PRAGMA table_info(tasks)')]:
                db.execute('ALTER TABLE tasks ADD COLUMN project INTEGER REFERENCES projects(id)')
            db.execute('CREATE INDEX IF NOT EXISTS tasks_project ON tasks(project)')
            if not db.execute('SELECT 1 FROM agents').fetchone():
                db.executemany('INSERT INTO agents(name,role) VALUES (?,?)', [
                    ('Research', 'Gather evidence and record sources'),
                    ('Builder', 'Implement and document the requested change'),
                    ('Reviewer', 'Verify results and record limitations')])
            # One migration per database; never overwrite renamed/custom staff.
            db.execute('INSERT OR IGNORE INTO migrations(name) VALUES (?)', ('specialist-roster-v1',))
            if db.execute('SELECT changes()').fetchone()[0]:
                for name, role in SPECIALISTS:
                    if not db.execute('SELECT 1 FROM agents WHERE name=?', (name,)).fetchone():
                        db.execute('INSERT INTO agents(name,role) VALUES (?,?)', (name, role))


    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def snapshot(self):
        with closing(self.connect()) as db, db:
            # One read transaction gives export and UI a consistent snapshot.
            db.execute('BEGIN')
            return {key: [dict(row) for row in db.execute(query)] for key, query in {
                'projects': 'SELECT * FROM projects ORDER BY id DESC',
                'dependencies': 'SELECT * FROM dependencies ORDER BY task, prerequisite',
                'agents': 'SELECT * FROM agents ORDER BY id',
                'tasks': 'SELECT * FROM tasks ORDER BY id DESC',
                'events': 'SELECT * FROM events ORDER BY id DESC LIMIT 200'
            }.items()}

    def mutate(self, action, data):
        if not isinstance(data, dict):
            raise ValueError('JSON object required')
        with closing(self.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            if action == 'job-project':
                name = required(data, 'name', 120)
                if db.execute('SELECT 1 FROM projects WHERE name=? COLLATE NOCASE', (name,)).fetchone():
                    raise Conflict('A project with this name already exists. Choose a unique application name.')
                project = db.execute('INSERT INTO projects(name,kind,created) VALUES (?,?,?)',
                                     (name, 'job-application', utcnow())).lastrowid
                # Reuse teams by name without overwriting customized instructions.
                teams = []
                for team, role in JOB_TEAMS:
                    row = db.execute('SELECT id FROM agents WHERE name=? ORDER BY id LIMIT 1', (team,)).fetchone()
                    teams.append(row['id'] if row else db.execute('INSERT INTO agents(name,role) VALUES (?,?)', (team, role)).lastrowid)
                tasks = []
                for team, title, brief, parents in JOB_STAGES:
                    task = db.execute('INSERT INTO tasks(title,brief,agent,project,created) VALUES (?,?,?,?,?)',
                                      (title, brief, teams[team], project, utcnow())).lastrowid
                    tasks.append(task)
                    db.executemany('INSERT INTO dependencies(task,prerequisite) VALUES (?,?)', [(task,tasks[parent]) for parent in parents])
                    db.execute('INSERT INTO events(task,message,created) VALUES (?,?,?)', (task, 'Application workflow task created', utcnow()))
                task, message = None, f'Job application project created: {name}'
            elif action == 'agents':
                name, role = required(data, 'name', 60), required(data, 'role', 500)
                agent = data.get('id')
                if agent is None:
                    db.execute('INSERT INTO agents(name,role) VALUES (?,?)', (name, role))
                else:
                    if type(agent) is not int or not db.execute('SELECT 1 FROM agents WHERE id=?', (agent,)).fetchone():
                        raise ValueError('Unknown agent')
                    db.execute('UPDATE agents SET name=?,role=? WHERE id=?', (name, role, agent))
                task, message = None, f'Agent saved: {name}'
            elif action == 'tasks':
                title, brief = required(data, 'title'), required(data, 'brief', 5000)
                agent = data.get('agent')
                if type(agent) is not int or not db.execute('SELECT 1 FROM agents WHERE id=?', (agent,)).fetchone():
                    raise ValueError('Choose an existing agent')
                due = due_date(data.get('due'))
                task = db.execute('INSERT INTO tasks(title,brief,agent,due,created) VALUES (?,?,?,?,?)',
                                  (title, brief, agent, due, utcnow())).lastrowid
                message = 'Task created'
            elif action == 'update':
                task, version = data.get('id'), data.get('version')
                if type(task) is not int or type(version) is not int:
                    raise ValueError('Integer id and version required')
                row = db.execute('SELECT * FROM tasks WHERE id=?', (task,)).fetchone()
                if row is None:
                    raise ValueError('Unknown task')
                if row['version'] != version:
                    raise Conflict('Task changed in another session. Refresh and try again.')
                agent = data.get('agent', row['agent'])
                if type(agent) is not int or not db.execute('SELECT 1 FROM agents WHERE id=?', (agent,)).fetchone():
                    raise ValueError('Choose an existing agent')
                status = data.get('status', row['status'])
                allowed = {'queued': ('queued', 'active'), 'active': ('active', 'review'),
                           'review': ('review', 'active', 'done'), 'done': ('done', 'queued')}
                if row['status'] == 'queued' and status == 'active':
                    waiting = db.execute('SELECT t.id FROM dependencies d JOIN tasks t ON t.id=d.prerequisite WHERE d.task=? AND t.status!=?', (task, 'done')).fetchall()
                    if waiting:
                        raise ValueError('Complete prerequisite tasks first: ' + ', '.join(str(t['id']) for t in waiting))
                if status not in allowed[row['status']]:
                    raise ValueError('Invalid task transition')
                result = data.get('result', row['result'])
                if not isinstance(result, str) or len(result) > 20000:
                    raise ValueError('Result must be text up to 20000 characters')
                if status in ('review', 'done') and not result.strip():
                    raise ValueError('Add a result before requesting review or completing a task')
                if row['status'] == 'queued' and status == 'active' and row['due'] and row['due'] > utcnow():
                    raise ValueError('This scheduled task is not due yet')
                if row['status'] == 'done' and (status != 'done' or result != row['result'] or agent != row['agent']):
                    started = db.execute('SELECT t.id FROM dependencies d JOIN tasks t ON t.id=d.task WHERE d.prerequisite=? AND t.status!=?', (task, 'queued')).fetchall()
                    if started:
                        raise ValueError('Reopen dependent tasks in reverse order before changing their input')
                db.execute('UPDATE tasks SET status=?,result=?,agent=?,version=version+1 WHERE id=?', (status, result, agent, task))
                message = f"{row['status']} → {status}" if status != row['status'] else 'Result updated'
                if agent != row['agent']:
                    message += f"; reassigned from agent #{row['agent']} to #{agent}"
            else:
                raise ValueError('Unknown operation')
            db.execute('INSERT INTO events(task,message,created) VALUES (?,?,?)', (task, message, utcnow()))
        return self.snapshot()


class Conflict(ValueError):
    pass


def make_server(path, port=4521):
    office = Office(path)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, kind='application/json; charset=utf-8'):
            raw = json.dumps(body).encode() if kind.startswith('application/json') else body
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(raw)

        def valid_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {'error': 'Local host required'})
            route = urlsplit(self.path).path
            if route == '/api/state':
                return self.send(200, {**office.snapshot(), 'token': token})
            if route == '/api/export':
                return self.send(200, office.snapshot())
            assets = {'/': ('index.html', 'text/html; charset=utf-8'),
                      '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8')}
            if route not in assets:
                return self.send(404, {'error': 'Not found'})
            name, mime = assets[route]
            self.send(200, (ROOT / name).read_bytes(), mime)

        def do_POST(self):
            if not self.valid_host() or not secrets.compare_digest(self.headers.get('X-Office-Token', ''), token):
                return self.send(403, {'error': 'Reload the local page before saving'})
            origin = self.headers.get('Origin')
            if origin and origin != 'http://' + self.headers.get('Host', ''):
                return self.send(403, {'error': 'Same-origin requests required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 100000:
                    raise ValueError('Request size must be 1–100000 bytes')
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('Use application/json')
                data = json.loads(self.rfile.read(length))
                action = {'/api/agents': 'agents', '/api/tasks': 'tasks', '/api/update': 'update', '/api/job-project': 'job-project'}.get(self.path)
                if action is None:
                    return self.send(404, {'error': 'Not found'})
                self.send(200, office.mutate(action, data))
            except Conflict as exc:
                self.send(409, {'error': str(exc)})
            except (ValueError, UnicodeError) as exc:
                self.send(400, {'error': str(exc)})
            except sqlite3.Error:
                self.send(503, {'error': 'Storage unavailable; retry shortly'})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default=str(ROOT / 'office.sqlite3'))
    parser.add_argument('--port', default=4521, type=int)
    args = parser.parse_args()
    server = make_server(args.db, args.port)
    print(f'AI Office: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
