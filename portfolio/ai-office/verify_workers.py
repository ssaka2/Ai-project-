"""Temporary synthetic-data worker smoke check. Calls only local Ollama by default."""
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
import ai_staff
from office import Office
import worker_runtime
import worker_store


def verify(provider=None, model=None):
    # A provider override is for automated tests; its evidence is labeled explicitly.
    selected=model or ai_staff.model_name()
    with patch.dict(os.environ,{'AI_OFFICE_MODEL':selected}), tempfile.TemporaryDirectory() as folder:
        app=Office(Path(folder)/'verification.sqlite3')
        candidate=app.mutate('candidate-project',{'name':'Synthetic smoke candidate','profile':'Fictional test data only'})['projects'][0]['id']
        app.mutate('campaign',{'candidate':candidate,'revision':0,'boards':'example','titles':'Software Engineer','locations':'United States','skills':'Python',
                              'resume':'Synthetic Person. Developed Python APIs for Fictional Example from 2020 to 2023. Education: Fictional University.',
                              'consent':True,'enabled':True})
        state=app.mutate('recruiting-project',{'name':'Synthetic smoke opening','candidate':candidate,'source_url':'https://example.com/jobs/smoke','description':'Software engineer building Python APIs in the United States. Fictional job.'})
        project=state['projects'][0]['id'];tasks=sorted([t for t in state['tasks'] if t['project']==project],key=lambda t:t['id'])
        for task in tasks[:3]:
            for version,status in enumerate(('active','review','done'),1):
                app.mutate('update',{'id':task['id'],'version':version,'status':status,'result':'Synthetic fixture evidence only; no real application.'})
        worker_store.set_settings(app,candidate,True,0,
            portfolio='Fictional Example API: Python REST service; synthetic fixture project, no public deployment.')
        worker_runtime.enqueue_eligible(app,now=time.time())
        # Exactly one attempt per role. No hidden retries or indefinite smoke run.
        for _ in worker_store.DRAFT_EXECUTORS:
            worker_runtime.run_once(app,provider=provider or ai_staff.generate)
        reopened=Office(app.path)
        runs=worker_store.list_runs(reopened,candidate_id=candidate)['runs']
        snapshot=reopened.snapshot()
        drafts={draft['id']:draft for draft in snapshot['ai_drafts']}
        saved_tasks={task['id']:task for task in snapshot['tasks']}
        if len(runs)!=3 or {run['executor'] for run in runs}!=set(worker_store.DRAFT_EXECUTORS):
            raise RuntimeError('Worker smoke failed: expected one run for each of the three document roles')
        evidence=[]
        for run in sorted(runs,key=lambda row:row['executor']):
            executor=run['executor']
            if run['state']!='succeeded':
                raise RuntimeError(f"Worker smoke failed: {executor} / {run['state']} / {run['error_code']}")
            draft=drafts.get(run['result_ref'])
            if (not draft or draft['task']!=run['task_id'] or draft['model']!=selected
                    or not draft['content'].startswith('UNVERIFIED AI DRAFT')):
                raise RuntimeError(f'Worker smoke failed: {executor} / missing or invalid persisted draft')
            task=saved_tasks[run['task_id']]
            if task['status']!='active':
                raise RuntimeError(f'Worker changed the approval state: {executor}')
            evidence.append({'executor':executor,'state':run['state'],'persisted':True,'task_status':task['status']})
        if len(drafts)!=3:
            raise RuntimeError('Worker smoke failed: unexpected persisted draft count')
        return {'verification':'injected_provider' if provider is not None else 'local_ollama',
                'model':selected,'runs':len(runs),'drafts':len(drafts),'task_status':'active','executors':evidence}


if __name__=='__main__':
    try:print(json.dumps(verify()))
    except (ValueError,RuntimeError) as error:
        print(str(error));raise SystemExit(1)
