"""Temporary synthetic-data worker smoke check. Calls only local Ollama by default."""
import json
import os
import tempfile
import time
from contextlib import closing
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
        with closing(app.connect()) as db,db:
            db.execute('DELETE FROM worker_bindings WHERE task_id!=?',(tasks[3]['id'],))
        worker_store.set_settings(app,candidate,True,0)
        worker_runtime.enqueue_eligible(app,now=time.time())
        worker_runtime.run_once(app,provider=provider or ai_staff.generate)
        reopened=Office(app.path)
        runs=worker_store.list_runs(reopened,candidate_id=candidate)['runs'];drafts=reopened.snapshot()['ai_drafts']
        if len(runs)!=1 or runs[0]['state']!='succeeded':
            raise RuntimeError('Worker smoke failed: '+(runs[0]['state']+' / '+runs[0]['error_code'] if runs else 'no run'))
        if len(drafts)!=1 or not drafts[0]['content'].startswith('UNVERIFIED AI DRAFT'):
            raise RuntimeError('Worker smoke failed: missing or invalid persisted draft')
        task=next(t for t in reopened.snapshot()['tasks'] if t['id']==tasks[3]['id'])
        if task['status']!='active':raise RuntimeError('Worker changed the approval state')
        return {'verification':'injected_provider' if provider else 'local_ollama','model':selected,'runs':1,'drafts':1,'task_status':task['status']}


if __name__=='__main__':
    try:print(json.dumps(verify()))
    except (ValueError,RuntimeError) as error:
        print(str(error));raise SystemExit(1)
