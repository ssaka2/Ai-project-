"""Public-board discovery and fact-preserving candidate preparation; no submission adapter."""
import lever_source
import html
import json
import re
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone, timedelta
from urllib.request import Request, build_opener, HTTPRedirectHandler

LOCK = threading.Lock()
GREENHOUSE_MAX_BYTES = 20_000_000
DEFAULT_MAX_BYTES = 5_000_000


class BoardSizeError(ValueError):
    """A complete source response could not fit within the bounded read."""


STOP_STATES = ('accepted', 'started', 'paused', 'withdrawn')


def now():
    return datetime.now(timezone.utc).isoformat()


def initialize(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS recruiting_campaigns(
            candidate INTEGER PRIMARY KEY REFERENCES projects(id),
            boards TEXT NOT NULL, titles TEXT NOT NULL, locations TEXT NOT NULL,
            skills TEXT NOT NULL, resume TEXT NOT NULL, enabled INTEGER NOT NULL,
            revision INTEGER NOT NULL, last_run TEXT, next_run TEXT, error TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS recruiting_jobs(
            candidate INTEGER NOT NULL REFERENCES projects(id), board TEXT NOT NULL,
            job_id TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL,
            location TEXT NOT NULL, description TEXT NOT NULL, first_seen TEXT NOT NULL,
            outcome TEXT NOT NULL, reason TEXT NOT NULL, draft TEXT NOT NULL,
            PRIMARY KEY(candidate,board,job_id));
        CREATE TABLE IF NOT EXISTS recruiting_workflows(
            candidate INTEGER NOT NULL, board TEXT NOT NULL, job_id TEXT NOT NULL,
            project INTEGER NOT NULL UNIQUE REFERENCES projects(id),
            PRIMARY KEY(candidate,board,job_id),
            FOREIGN KEY(candidate,board,job_id) REFERENCES recruiting_jobs(candidate,board,job_id));
        CREATE TABLE IF NOT EXISTS recruiting_baselines(
            candidate INTEGER NOT NULL REFERENCES projects(id), board TEXT NOT NULL,
            created TEXT NOT NULL, PRIMARY KEY(candidate,board));
    ''')


def snapshot_queries():
    return {'recruiting_workflows':'SELECT * FROM recruiting_workflows ORDER BY project',
            'campaigns':'SELECT * FROM recruiting_campaigns ORDER BY candidate',
            'job_queue':'SELECT * FROM recruiting_jobs ORDER BY first_seen DESC,job_id'}


def terms(data, key):
    value = data.get(key)
    if not isinstance(value,str) or not value.strip() or len(value)>2000:
        raise ValueError(f'{key} requires comma-separated values (maximum 2000 characters)')
    result = list(dict.fromkeys(x.strip() for x in value.split(',') if x.strip()))
    if not result or len(result)>30:
        raise ValueError(f'{key} requires 1–30 values')
    return result


def configure(db, data, conflict):
    candidate = data.get('candidate')
    if type(candidate) is not int or not db.execute("SELECT 1 FROM projects WHERE id=? AND kind='candidate-placement'",(candidate,)).fetchone():
        raise ValueError('Choose a candidate case')
    old = db.execute('SELECT revision FROM recruiting_campaigns WHERE candidate=?',(candidate,)).fetchone()
    if type(data.get('revision')) is not int or data['revision'] != (old['revision'] if old else 0):
        raise conflict('Campaign changed. Refresh and select the candidate again.')
    boards,titles,locations,skills = (terms(data,k) for k in ('boards','titles','locations','skills'))
    boards = list(dict.fromkeys(normalize_board(b) for b in boards))
    if len(boards)>5:
        raise ValueError('Maximum five employer boards per campaign')
    resume = data.get('resume')
    if not isinstance(resume,str) or not resume.strip() or len(resume)>20000:
        raise ValueError('Verified master CV must contain 1–20000 characters')
    if data.get('consent') is not True or type(data.get('enabled')) is not bool:
        raise ValueError('Candidate authorization and an explicit enabled setting are required')
    db.execute('''INSERT INTO recruiting_campaigns(candidate,boards,titles,locations,skills,resume,enabled,revision,next_run)
                  VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(candidate) DO UPDATE SET
                  boards=excluded.boards,titles=excluded.titles,locations=excluded.locations,
                  skills=excluded.skills,resume=excluded.resume,enabled=excluded.enabled,
                  revision=excluded.revision,next_run=excluded.next_run,error='' ''',
               (candidate,*(json.dumps(v) for v in (boards,titles,locations,skills)),resume.strip(),int(data['enabled']),data['revision']+1,now()))
    # Old packages are never silently reused after a profile/preference change.
    db.execute("UPDATE recruiting_jobs SET outcome='needs_review',reason='Campaign changed; review this saved package against current preferences' WHERE candidate=? AND outcome='blocked'",(candidate,))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Board redirected; source review required')


def normalize_board(board):
    if not isinstance(board,str) or not re.fullmatch(r'(?:(?:greenhouse|lever):)?[a-zA-Z0-9_-]{1,80}',board):
        raise ValueError('Use a Greenhouse token or lever:company, not a URL')
    # Preserve old Greenhouse database keys; aliases cannot create a second queue.
    return board.removeprefix('greenhouse:')


def read_json(url, *, max_bytes=DEFAULT_MAX_BYTES):
    request = Request(url,headers={'User-Agent':'AI-Office/1.0','Accept':'application/json'})
    with build_opener(NoRedirect).open(request,timeout=15) as response:
        raw = response.read(max_bytes + 1)
    if len(raw)>max_bytes:
        raise BoardSizeError('Board response exceeds size limit')
    return json.loads(raw)


def fetch_board(board):
    board = normalize_board(board)
    if board.startswith('lever:'):
        return lever_source.fetch(board.split(':',1)[1],read_json)
    body = read_json(f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true', max_bytes=GREENHOUSE_MAX_BYTES)
    if not isinstance(body,dict) or not isinstance(body.get('jobs'),list) or len(body['jobs'])>10000:
        raise ValueError('Invalid or oversized board response')
    jobs=[]
    for item in body['jobs']:
        if not isinstance(item,dict):
            raise ValueError('Invalid job entry')
        # Prospect posts are not specific job openings.
        if item.get('internal_job_id') is None:
            continue
        if type(item.get('id')) is not int or not isinstance(item.get('title'),str) or not isinstance(item.get('content'),str):
            raise ValueError('Incomplete job entry')
        location_object = item.get('location')
        if not isinstance(location_object,dict):
            raise ValueError('Invalid job location')
        location = location_object.get('name','')
        url = item.get('absolute_url','')
        if not isinstance(location,str) or not isinstance(url,str) or not url.startswith('https://'):
            raise ValueError('Invalid job location or URL')
        description = re.sub(r'<[^>]*>',' ',html.unescape(item['content']))
        jobs.append({'id':str(item['id']),'title':item['title'][:500],'url':url[:2000],
                     'location':location[:1000],'description':description[:50000]})
    return jobs


def contains(text, term):
    return re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.I) is not None


def prepare(campaign, job):
    description=job['description']
    skills=json.loads(campaign['skills'])
    matched=[s for s in skills if contains(description,s) and contains(campaign['resume'],s)]
    # Exact source lines only: retain every original fact in the master CV below.
    highlights=[line for line in campaign['resume'].splitlines() if line.strip() and any(contains(line,s) for s in matched)]
    draft=('DRAFT — candidate review required\nTarget: '+job['title']+'\nSource: '+job['url']+
           '\n\nRelevant verified CV excerpts\n'+'\n'.join(highlights[:8])+'\n\nComplete master CV (unchanged)\n'+campaign['resume'])
    reasons=[]
    if not any(contains(job['title'],t) for t in json.loads(campaign['titles'])):
        reasons.append('Title does not match candidate targets')
    if not any(contains(job['location'],t) for t in json.loads(campaign['locations'])):
        reasons.append('Location not explicitly matched; US location/remote eligibility needs review')
    if not matched:
        reasons.append('No supplied skill appears in both CV and job description')
    if reasons:
        return 'filtered','; '.join(reasons),draft
    return 'blocked','Keyword screen matched; full requirements, sponsorship, candidate answers and CV approval need review. No authorized submission connector is configured.',draft


def scan(office, fetcher=fetch_board):
    """One bounded scan. The shared lock prevents concurrent scheduler/manual requests."""
    if not LOCK.acquire(blocking=False):
        return
    try:
        with closing(office.connect()) as db:
            campaigns=[dict(r) for r in db.execute('SELECT * FROM recruiting_campaigns WHERE enabled=1')]
        for campaign in campaigns:
            if campaign['next_run'] and campaign['next_run']>now():
                continue
            errors=[]
            attempted=False
            for board in json.loads(campaign['boards']):
                try:
                    # Check stop conditions before making any network request.
                    with closing(office.connect()) as db:
                        if not active(db,campaign):
                            break
                    attempted=True
                    jobs=fetcher(board)
                    with closing(office.connect()) as db, db:
                        db.execute('BEGIN IMMEDIATE')
                        if not active(db,campaign):
                            break
                        baseline=db.execute('SELECT 1 FROM recruiting_baselines WHERE candidate=? AND board=?',(campaign['candidate'],board)).fetchone()
                        for job in jobs:
                            if db.execute('SELECT 1 FROM recruiting_jobs WHERE candidate=? AND board=? AND job_id=?',(campaign['candidate'],board,job['id'])).fetchone():
                                continue
                            outcome,reason,draft=prepare(campaign,job) if baseline else ('baseline','Existing on first successful scan; excluded from new-job queue','')
                            db.execute('INSERT INTO recruiting_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                                       (campaign['candidate'],board,job['id'],job['title'],job['url'],job['location'],job['description'],now(),outcome,reason,draft))
                        db.execute('INSERT OR IGNORE INTO recruiting_baselines VALUES (?,?,?)',(campaign['candidate'],board,now()))
                except Exception as exc:
                    # Avoid returning third-party content, URLs or credentials in errors.
                    errors.append(f'{board}: source exceeds response limit; no partial jobs saved. Source adapter review required.' if isinstance(exc, BoardSizeError) else f'{board}: {type(exc).__name__}; retry next cycle')
            if not attempted:
                continue
            with closing(office.connect()) as db, db:
                db.execute('UPDATE recruiting_campaigns SET last_run=?,next_run=?,error=? WHERE candidate=? AND revision=?',
                           (now(),(datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(),'; '.join(errors),campaign['candidate'],campaign['revision']))
    finally:
        LOCK.release()


def active(db, campaign):
    row=db.execute('SELECT enabled,revision FROM recruiting_campaigns WHERE candidate=?',(campaign['candidate'],)).fetchone()
    status=db.execute('SELECT status FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(campaign['candidate'],)).fetchone()
    return row and row['enabled'] and row['revision']==campaign['revision'] and (not status or status['status'] not in STOP_STATES)


def worker(office, stop):
    while not stop.is_set():
        try:
            scan(office)
        except sqlite3.Error:
            pass  # Database errors retry on the next tick, never report a submission.
        stop.wait(30)


def handoff(db, data, conflict):
    """Resolve stored source data inside the workflow-creation transaction."""
    candidate, board, job_id = data.get('candidate'), data.get('board'), data.get('job_id')
    if type(candidate) is not int or not isinstance(board,str) or not isinstance(job_id,str) or len(job_id)>200:
        raise ValueError('Candidate, board and job ID required')
    board = normalize_board(board)
    key = (candidate,board,job_id)
    linked = db.execute('SELECT project FROM recruiting_workflows WHERE candidate=? AND board=? AND job_id=?',key).fetchone()
    if linked:
        raise conflict(f"Already linked to application project #{linked['project']}; use the existing workflow")
    job = db.execute('SELECT * FROM recruiting_jobs WHERE candidate=? AND board=? AND job_id=?',key).fetchone()
    if not job or job['outcome']!='blocked':
        raise ValueError('Only a current keyword-matched queue entry can enter the workflow; review campaign preferences and source evidence')
    status = db.execute('SELECT status FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(candidate,)).fetchone()
    if status and status['status'] in STOP_STATES:
        raise ValueError('Candidate search is stopped; review the candidate status first')
    # Deterministic unique name without leaking candidate details or truncating JD.
    row = db.execute('SELECT rowid FROM recruiting_jobs WHERE candidate=? AND board=? AND job_id=?',key).fetchone()
    name = f"Queue #{row[0]}: " + job['title'][:90]
    context = (f"\nDiscovery source: {board} / {job_id}\nFirst observed: {job['first_seen']}"
               f"\nSource location: {job['location']}\nFreshness and eligibility remain unverified. "
               'No task has been completed and no application has been sent.')
    return key, dict(name=name,candidate=candidate,source_url=job['url'],description=job['description']), context
