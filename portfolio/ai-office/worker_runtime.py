"""One bounded local dispatcher. No submission or inbox tools are available."""
import sqlite3
import threading
import time
from contextlib import closing
from datetime import datetime, timezone
from urllib.error import URLError, HTTPError
import ai_staff
import recruiting
import worker_registry as registry
import worker_store as store


def enqueue_eligible(office, *, now):
    with closing(office.connect()) as db:
        tasks=[dict(r) for r in db.execute('''SELECT t.*,b.executor FROM worker_bindings b
            JOIN tasks t ON t.id=b.task_id JOIN projects p ON p.id=t.project
            JOIN automation_settings s ON s.candidate_id=p.candidate
            JOIN recruiting_campaigns c ON c.candidate=p.candidate
            WHERE s.enabled=1 AND c.enabled=1 AND t.status IN ('queued','active')
            AND NOT EXISTS(SELECT 1 FROM dependencies d JOIN tasks parent ON parent.id=d.prerequisite
                           WHERE d.task=t.id AND parent.status!='done')
            ORDER BY t.id''')]
    count=0
    for task in tasks:
        try:
            with closing(office.connect()) as db:
                project=db.execute('SELECT candidate FROM projects WHERE id=?',(task['project'],)).fetchone()
                status=db.execute('SELECT status FROM application_checks WHERE project=? ORDER BY id DESC LIMIT 1',(project['candidate'],)).fetchone()
                if status and status['status'] in recruiting.STOP_STATES:continue
            if task['status']=='queued':
                if task['due'] and datetime.fromisoformat(task['due']).timestamp()>now:continue
                office.mutate('update',{'id':task['id'],'version':task['version'],'status':'active'})
            prepared=registry.prepare(office,task['id'],task['executor'])
            store.enqueue(office,task_id=prepared['task_id'],task_version=prepared['task_version'],candidate_id=prepared['candidate_id'],
                          executor=prepared['executor'],fingerprint=prepared['fingerprint'],now=now)
            count+=1
        except ValueError:
            # A simultaneous task edit is retried from a fresh snapshot next tick.
            continue
    return count


def classify(error):
    current=error
    while current:
        if isinstance(current,TimeoutError):return 'retry_wait','provider_timeout'
        if isinstance(current,HTTPError):
            return ('retry_wait','provider_unavailable') if current.code>=500 else ('blocked','provider_rejected')
        if isinstance(current,URLError):return 'retry_wait','provider_unavailable'
        current=current.__cause__
    return 'blocked','invalid_output_or_context'


def run_once(office, *, now_fn=time.time, provider=ai_staff.generate, stop=None):
    if not ai_staff.LOCK.acquire(blocking=False):return False
    heartbeat_stop=threading.Event()
    heartbeat=None
    run=None
    try:
        if stop and stop.is_set():return False
        run=store.claim(office,now=now_fn())
        if not run:return False
        if run['executor'] not in store.DRAFT_EXECUTORS:
            store.finish(office,run['id'],run['lease_token'],state='blocked',now=now_fn(),error_code='unsupported_executor')
            return True
        try:prepared=registry.prepare(office,run['task_id'],run['executor'])
        except ValueError:
            store.finish(office,run['id'],run['lease_token'],state='blocked',now=now_fn(),error_code='inputs_changed');return True
        if prepared['fingerprint']!=run['fingerprint'] or prepared['blocker']:
            store.finish(office,run['id'],run['lease_token'],state='blocked',now=now_fn(),error_code=prepared['blocker'] or 'inputs_changed');return True
        def beat():
            while not heartbeat_stop.wait(30):
                try:
                    if (stop and stop.is_set()) or not store.renew(office,run['id'],run['lease_token'],now=now_fn()):return
                except sqlite3.Error:return
        heartbeat=threading.Thread(target=beat,daemon=True);heartbeat.start()
        with closing(office.connect()) as db:
            cached=db.execute('SELECT content,context_digest FROM ai_drafts WHERE task=? AND task_version=?',(run['task_id'],run['task_version'])).fetchone()
        if cached:
            if cached['context_digest']!=prepared['draft_digest']:
                store.finish(office,run['id'],run['lease_token'],state='blocked',now=now_fn(),error_code='existing_draft_stale');return True
            result=cached['content']
        else:result=provider(prepared['model'],prepared['prompt'])
        with closing(office.connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            current=registry.prepare_db(db,run['task_id'],run['executor'])
            if current['fingerprint']!=prepared['fingerprint'] or current['blocker']:
                store.finish_db(db,run['id'],run['lease_token'],state='blocked',now=now_fn(),error_code='inputs_changed')
            elif stop and stop.is_set():
                # A process restart does not invalidate unchanged source facts.
                # Discard this output and use the existing bounded retry policy.
                store.finish_db(db,run['id'],run['lease_token'],state='retry_wait',now=now_fn(),error_code='shutdown_interrupted')
            elif store.live(db,run['id'],run['lease_token'],now_fn()):
                draft_id=ai_staff.persist_draft(db,prepared,result,datetime.now(timezone.utc).isoformat())
                if not store.finish_db(db,run['id'],run['lease_token'],state='succeeded',now=now_fn(),result_ref=draft_id):
                    raise ValueError('Worker lease expired; draft rolled back')
        return True
    except sqlite3.Error:
        # Preserve the lease for recovery; never pretend a partial save succeeded.
        return False
    except Exception as error:
        if run:
            state,code=classify(error)
            # Invalidated contexts are deterministic blockers, never provider retries.
            if isinstance(error,ValueError) and 'changed' in str(error):code='inputs_changed'
            try:store.finish(office,run['id'],run['lease_token'],state=state,now=now_fn(),error_code=code)
            except sqlite3.Error:pass
        return bool(run)
    finally:
        heartbeat_stop.set()
        if heartbeat:heartbeat.join(timeout=1)
        ai_staff.LOCK.release()


def serve(office, stop):
    while not stop.is_set():
        try:
            store.recover_expired(office,now=time.time())
            enqueue_eligible(office,now=time.time())
            if not stop.is_set():run_once(office,stop=stop)
        except sqlite3.Error:
            pass
        stop.wait(1)
