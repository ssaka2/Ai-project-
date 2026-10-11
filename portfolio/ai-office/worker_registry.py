"""Explicit execution bindings and evidence-based capability reporting."""
import hashlib
import json
import os
from contextlib import closing
import ai_staff
import recruiting
from worker_store import DRAFT_EXECUTORS, integer

LABELS={'cv_draft':'CV tailor','portfolio_draft':'Portfolio tailor','cover_letter_draft':'Cover-letter writer'}


def prepare_db(db, task_id, executor):
    integer(task_id)
    binding=db.execute('SELECT executor FROM worker_bindings WHERE task_id=?',(task_id,)).fetchone()
    if executor not in DRAFT_EXECUTORS or not binding or binding['executor']!=executor:raise ValueError('Task has no matching executor binding')
    task=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
    project=db.execute('SELECT * FROM projects WHERE id=?',(task['project'],)).fetchone()
    candidate=project['candidate'] if project and project['kind']=='job-application' else None
    if not candidate:raise ValueError('Choose a document task linked to a candidate application')
    settings=db.execute('SELECT * FROM automation_settings WHERE candidate_id=?',(candidate,)).fetchone()
    campaign=db.execute('SELECT * FROM recruiting_campaigns WHERE candidate=?',(candidate,)).fetchone()
    status=db.execute('SELECT id,status FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(candidate,)).fetchone()
    blocker=''
    if not settings or not settings['enabled']:blocker='automation_paused'
    elif status and status['status'] in recruiting.STOP_STATES:blocker='candidate_stopped'
    elif not campaign or not campaign['enabled'] or not campaign['resume'].strip():blocker='missing_campaign_facts'
    elif db.execute("SELECT 1 FROM dependencies d JOIN tasks t ON t.id=d.prerequisite WHERE d.task=? AND t.status!='done'",(task_id,)).fetchone():blocker='prerequisites_pending'
    elif executor=='portfolio_draft' and not settings['portfolio'].strip():blocker='missing_portfolio'
    model=os.environ.get('AI_OFFICE_MODEL','')
    try:ai_staff.model_name()
    except ValueError:blocker=blocker or 'model_not_configured'
    prompt=ai_staff.context(db,task_id,task['version'],enforce_limit=False)
    source_prompt=prompt
    if executor=='portfolio_draft':
        prompt=json.dumps({'context':json.loads(prompt),'verified_project_inventory':settings['portfolio'] if settings else ''},sort_keys=True,ensure_ascii=True)
    if len(prompt)>60000:blocker=blocker or 'context_too_large'
    digest=hashlib.sha256((ai_staff.SYSTEM+'\n'+model+'\n'+prompt).encode()).hexdigest()
    identity={'draft':digest,'executor':executor,'adapter_version':1,'settings':dict(settings) if settings else None,
              'campaign_revision':campaign['revision'] if campaign else None,'candidate_status':dict(status) if status else None}
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    return {'task_id':task_id,'task_version':task['version'],'candidate_id':candidate,'executor':executor,
            'fingerprint':fingerprint,'prompt':prompt,'context_prompt':source_prompt,'model':model,'draft_digest':digest,
            'settings_revision':settings['revision'] if settings else 0,'blocker':blocker}


def prepare(office, task_id, executor):
    with closing(office.connect()) as db,db:
        db.execute('BEGIN')
        return prepare_db(db,task_id,executor)


def capabilities(office):
    try: model=ai_staff.model_name()
    except ValueError:model=''
    with closing(office.connect()) as db:
        result=[]
        for key,label in LABELS.items():
            row=db.execute("SELECT r.id,d.model FROM worker_runs r JOIN ai_drafts d ON d.id=r.result_ref WHERE r.executor=? AND r.state='succeeded' ORDER BY r.id DESC LIMIT 1",(key,)).fetchone()
            result.append({'key':key,'label':label,'mode':'local_model','configured':bool(model),'reachable':None,
                           'execution_verified':bool(row and row['model']==model),'last_run_id':row['id'] if row else None,
                           'blocker':'' if model else 'model_not_configured'})
        discovery=db.execute('SELECT MAX(last_run) AS checked FROM recruiting_campaigns').fetchone()['checked']
    for key,label,mode,blocker in [('discovery','Job collector','configured_feeds','Only configured Greenhouse/Lever boards'),
            ('screening','US software screener','rules','Freshness and eligibility require evidence review'),
            ('duplicates','Duplicate checker','rules','Canonical identity must be provided and verified'),
            ('matching','Eligibility matcher','manual_review','Verified candidate facts required'),
            ('qa','Application QA','manual_review','Operator review and candidate authorization required'),
            ('submission','Submission agent','unsupported','No authorized submission adapter'),
            ('inbox','Status tracker','unsupported','No runtime inbox OAuth connection'),
            ('chat','Candidate assistant','stored_records','Trusted operator only; no public candidate login'),
            ('manager','Manager','scheduler','Schedules bound document tasks only'),
            ('recovery','Recovery monitor','scheduler','Runs only while the Python server is running')]:
        result.append({'key':key,'label':label,'mode':mode,'configured':mode!='unsupported','reachable':None,
                       'execution_verified':False,'last_run_id':None,'blocker':blocker})
    result[3]['last_checked']=discovery
    return result
