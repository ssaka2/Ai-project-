"""Durable work records. Network calls never belong in these transactions."""
import secrets
import time
from contextlib import closing

DRAFT_EXECUTORS = ('cv_draft', 'portfolio_draft', 'cover_letter_draft')
STATES = ('queued','running','retry_wait','succeeded','blocked','failed','cancelled','unknown_outcome')


def integer(value, name='ID', minimum=1, maximum=2**63-1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f'{name} must be an integer from {minimum} to {maximum}')
    return value


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS automation_settings(
          candidate_id INTEGER PRIMARY KEY REFERENCES projects(id),
          enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
          revision INTEGER NOT NULL DEFAULT 1, portfolio TEXT NOT NULL DEFAULT '', updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS worker_bindings(
          task_id INTEGER PRIMARY KEY REFERENCES tasks(id), executor TEXT NOT NULL
          CHECK(executor IN ('cv_draft','portfolio_draft','cover_letter_draft')));
        CREATE TABLE IF NOT EXISTS worker_runs(
          id INTEGER PRIMARY KEY, revision INTEGER NOT NULL DEFAULT 1,
          task_id INTEGER NOT NULL REFERENCES tasks(id), task_version INTEGER NOT NULL,
          candidate_id INTEGER NOT NULL REFERENCES projects(id), executor TEXT NOT NULL,
          fingerprint TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'queued'
          CHECK(state IN ('queued','running','retry_wait','succeeded','blocked','failed','cancelled','unknown_outcome')),
          attempts INTEGER NOT NULL DEFAULT 0, cycle_attempts INTEGER NOT NULL DEFAULT 0,
          max_attempts INTEGER NOT NULL DEFAULT 3 CHECK(max_attempts=3),
          due_at REAL NOT NULL, lease_token TEXT, lease_expires_at REAL,
          error_code TEXT NOT NULL DEFAULT '', result_ref INTEGER REFERENCES ai_drafts(id),
          created REAL NOT NULL, updated REAL NOT NULL,
          UNIQUE(executor,task_id,task_version,fingerprint));
        CREATE INDEX IF NOT EXISTS worker_due ON worker_runs(state,due_at,id);
        CREATE INDEX IF NOT EXISTS worker_latest ON worker_runs(candidate_id,task_id,id);
        CREATE TABLE IF NOT EXISTS worker_attempts(
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES worker_runs(id),
          attempt INTEGER NOT NULL, started REAL NOT NULL, ended REAL,
          outcome TEXT NOT NULL DEFAULT 'running', error_code TEXT NOT NULL DEFAULT '',
          UNIQUE(run_id,attempt));
        INSERT OR IGNORE INTO migrations(name) VALUES ('worker-foundation-v1');
    ''')


def enqueue(office, *, task_id, task_version, candidate_id, executor, fingerprint, now):
    for v in (task_id, task_version, candidate_id):integer(v)
    if not isinstance(fingerprint,str) or not 1 <= len(fingerprint) <= 128:raise ValueError('Invalid fingerprint')
    if executor not in (*DRAFT_EXECUTORS,'submission'):raise ValueError('Unsupported executor')
    with closing(office.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''INSERT OR IGNORE INTO worker_runs
            (task_id,task_version,candidate_id,executor,fingerprint,due_at,created,updated)
            VALUES (?,?,?,?,?,?,?,?)''',(task_id,task_version,candidate_id,executor,fingerprint,now,now,now))
        return dict(db.execute('SELECT * FROM worker_runs WHERE executor=? AND task_id=? AND task_version=? AND fingerprint=?',
                               (executor,task_id,task_version,fingerprint)).fetchone())


def claim(office, *, now):
    with closing(office.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute("SELECT * FROM worker_runs WHERE state IN ('queued','retry_wait') AND due_at<=? ORDER BY due_at,id LIMIT 1",(now,)).fetchone()
        if not row:return None
        token=secrets.token_hex(24)
        db.execute("UPDATE worker_runs SET state='running',attempts=attempts+1,cycle_attempts=cycle_attempts+1,lease_token=?,lease_expires_at=?,updated=?,revision=revision+1 WHERE id=?",(token,now+240,now,row['id']))
        db.execute('INSERT INTO worker_attempts(run_id,attempt,started) VALUES (?,?,?)',(row['id'],row['attempts']+1,now))
        return dict(db.execute('SELECT * FROM worker_runs WHERE id=?',(row['id'],)).fetchone())


def live(db, run_id, token, now):
    return db.execute("SELECT * FROM worker_runs WHERE id=? AND state='running' AND lease_token=? AND lease_expires_at>?",(run_id,token,now)).fetchone()


def renew(office, run_id, token, *, now):
    started=time.monotonic()
    with closing(office.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        now+=time.monotonic()-started
        return bool(db.execute("UPDATE worker_runs SET lease_expires_at=? WHERE id=? AND state='running' AND lease_token=? AND lease_expires_at>?",(now+240,run_id,token,now)).rowcount)


def finish_db(db, run_id, token, *, state, now, error_code='', result_ref=None, expired=False):
    if state not in ('retry_wait','succeeded','blocked','failed','cancelled','unknown_outcome'):raise ValueError('Invalid completion state')
    row=(db.execute("SELECT * FROM worker_runs WHERE id=? AND state='running' AND lease_token=?",(run_id,token)).fetchone()
         if expired else live(db,run_id,token,now))
    if not row:return False
    due=now
    if state=='retry_wait':
        if row['cycle_attempts']>=row['max_attempts']:state='failed'
        else:due=now+(30 if row['cycle_attempts']==1 else 120)
    db.execute('''UPDATE worker_runs SET state=?,due_at=?,error_code=?,result_ref=?,updated=?,revision=revision+1,
                lease_token=NULL,lease_expires_at=NULL WHERE id=?''',(state,due,error_code,result_ref,now,run_id))
    db.execute('UPDATE worker_attempts SET ended=?,outcome=?,error_code=? WHERE run_id=? AND attempt=?',
               (now,state,error_code,run_id,row['attempts']))
    return True


def finish(office, run_id, token, *, state, now, error_code='', result_ref=None):
    started=time.monotonic()
    with closing(office.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        if not live(db,run_id,token,now+time.monotonic()-started):return False
        return finish_db(db,run_id,token,state=state,now=now,error_code=error_code,result_ref=result_ref)


def recover_expired(office, *, now):
    with closing(office.connect()) as db, db:
        db.execute('BEGIN IMMEDIATE')
        rows=db.execute("SELECT * FROM worker_runs WHERE state='running' AND lease_expires_at<=?",(now,)).fetchall()
        for row in rows:
            finish_db(db,row['id'],row['lease_token'],state='retry_wait' if row['executor'] in DRAFT_EXECUTORS else 'unknown_outcome',now=now,error_code='lease_expired',expired=True)
        return len(rows)


def list_runs(office, *, candidate_id, before_id=None, limit=25):
    integer(candidate_id);integer(limit,'limit',1,100)
    if before_id is not None:integer(before_id)
    with closing(office.connect()) as db:
        rows=[dict(r) for r in db.execute('''SELECT r.*,t.agent FROM worker_runs r JOIN tasks t ON t.id=r.task_id
            WHERE candidate_id=? AND r.id<? ORDER BY r.id DESC LIMIT ?''',(candidate_id,before_id or 2**63-1,limit+1))]
    for row in rows:row.pop('lease_token',None)
    return {'runs':rows[:limit],'next_cursor':rows[limit-1]['id'] if len(rows)>limit else None}


def set_settings(office, candidate_id, enabled, expected_revision, portfolio=None):
    import time
    from office import Conflict
    integer(candidate_id);integer(expected_revision,'revision',0)
    if type(enabled) is not bool:raise ValueError('enabled must be true or false')
    if portfolio is not None and (not isinstance(portfolio,str) or len(portfolio)>12000):raise ValueError('Verified project inventory must be at most 12000 characters')
    with closing(office.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        if not db.execute("SELECT 1 FROM projects WHERE id=? AND kind='candidate-placement'",(candidate_id,)).fetchone():raise ValueError('Choose a candidate case')
        old=db.execute('SELECT * FROM automation_settings WHERE candidate_id=?',(candidate_id,)).fetchone()
        if expected_revision!=(old['revision'] if old else 0):raise Conflict('Automation settings changed; refresh before saving')
        text=portfolio if portfolio is not None else old['portfolio'] if old else ''
        db.execute('''INSERT INTO automation_settings(candidate_id,enabled,revision,portfolio,updated) VALUES (?,?,?,?,?)
            ON CONFLICT(candidate_id) DO UPDATE SET enabled=excluded.enabled,revision=excluded.revision,portfolio=excluded.portfolio,updated=excluded.updated''',
            (candidate_id,int(enabled),expected_revision+1,text,time.time()))
        db.execute('INSERT INTO events(message,created) VALUES (?,datetime(\'now\'))',(f'Candidate #{candidate_id}: document automation {"enabled" if enabled else "paused"}',))
        return dict(db.execute('SELECT * FROM automation_settings WHERE candidate_id=?',(candidate_id,)).fetchone())


def control_run(office, run_id, action, expected_revision):
    import time
    import worker_registry
    from office import Conflict
    integer(run_id);integer(expected_revision,'revision')
    if action not in ('retry','cancel'):raise ValueError('Unknown worker action')
    now=time.time()
    with closing(office.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT * FROM worker_runs WHERE id=?',(run_id,)).fetchone()
        if not row:raise ValueError('Unknown worker run')
        if row['revision']!=expected_revision:raise Conflict('Run changed; refresh before trying again')
        if action=='retry':
            if row['state'] not in ('failed','blocked'):raise ValueError('Only resolved failed/blocked draft runs can retry; unknown outcomes require reconciliation')
            prepared=worker_registry.prepare_db(db,row['task_id'],row['executor'])
            if prepared['blocker']:raise ValueError('Resolve blocker first: '+prepared['blocker'])
            if prepared['fingerprint']!=row['fingerprint']:raise ValueError('Inputs changed; the scheduler will create a new versioned run')
            if row['error_code']=='existing_draft_stale':raise ValueError('Save a new task version before generating a replacement draft')
            db.execute("UPDATE worker_runs SET state='queued',cycle_attempts=0,due_at=?,error_code='',revision=revision+1,updated=? WHERE id=?",(now,now,run_id))
        else:
            if row['state'] not in ('queued','running','retry_wait','blocked','failed'):raise ValueError('Run cannot be cancelled in this state')
            db.execute("UPDATE worker_attempts SET outcome='cancelled',ended=? WHERE run_id=? AND ended IS NULL",(now,run_id))
            db.execute("UPDATE worker_runs SET state='cancelled',lease_token=NULL,lease_expires_at=NULL,revision=revision+1,updated=? WHERE id=?",(now,run_id))
        db.execute('INSERT INTO events(task,message,created) VALUES (?,?,datetime(\'now\'))',(row['task_id'],f'Worker run #{run_id}: operator {action}'))
        result=dict(db.execute('SELECT * FROM worker_runs WHERE id=?',(run_id,)).fetchone());result.pop('lease_token',None)
        return result


def bind_task(office, task_id, executor, expected_version):
    from office import Conflict
    integer(task_id);integer(expected_version,'version')
    if executor not in DRAFT_EXECUTORS:raise ValueError('Only document executors may be bound')
    with closing(office.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        task=db.execute("SELECT t.*,p.candidate FROM tasks t JOIN projects p ON p.id=t.project WHERE t.id=? AND p.kind='job-application'",(task_id,)).fetchone()
        if not task or not task['candidate']:raise ValueError('Choose a task in a candidate-linked application')
        if task['version']!=expected_version:raise Conflict('Task changed; refresh before binding')
        if task['status'] not in ('queued','active'):raise ValueError('Only queued/active tasks may be bound')
        if db.execute('SELECT 1 FROM worker_bindings WHERE task_id=?',(task_id,)).fetchone():raise ValueError('Task already has a stable executor binding')
        # Existing template tasks other than document work are not convertible.
        if task['title'] not in ('Prepare the tailored CV','Prepare the tailored portfolio','Prepare the cover letter'):
            raise ValueError('Only a document preparation task may be bound')
        expected={'Prepare the tailored CV':'cv_draft','Prepare the tailored portfolio':'portfolio_draft','Prepare the cover letter':'cover_letter_draft'}[task['title']]
        if executor!=expected:raise ValueError('Executor does not match the document task')
        db.execute('INSERT INTO worker_bindings VALUES (?,?)',(task_id,executor))
        db.execute('UPDATE tasks SET version=version+1 WHERE id=?',(task_id,))
        db.execute('INSERT INTO events(task,message,created) VALUES (?,?,datetime(\'now\'))',(task_id,f'Explicit document executor binding: {executor}'))
        return {'task_id':task_id,'executor':executor,'version':expected_version+1}


def workflow_status(office, candidate_id):
    integer(candidate_id)
    with closing(office.connect()) as db:
        groups=[dict(r) for r in db.execute('''SELECT t.title,t.agent,r.state,COUNT(*) AS count
            FROM worker_runs r JOIN tasks t ON t.id=r.task_id
            WHERE r.candidate_id=? AND r.id=(SELECT MAX(newer.id) FROM worker_runs newer WHERE newer.task_id=r.task_id AND newer.candidate_id=r.candidate_id)
            GROUP BY t.title,t.agent,r.state ORDER BY t.title,t.agent,r.state''',(candidate_id,))]
    return {'candidate_id':candidate_id,'groups':groups,'checked_at':time.time()}
