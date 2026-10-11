"""Synthetic test fixtures; never contact a job portal or model service."""
from contextlib import closing
from pathlib import Path
import tempfile
from unittest.mock import patch
import office


def fixture(test):
    tmp=tempfile.TemporaryDirectory();test.addCleanup(tmp.cleanup)
    test.env=patch.dict('os.environ',{'AI_OFFICE_MODEL':'fixture-model'});test.env.start();test.addCleanup(test.env.stop)
    app=office.Office(Path(tmp.name)/'office.db')
    candidate=app.mutate('candidate-project',{'name':'Synthetic','profile':'Synthetic CV facts'})['projects'][0]['id']
    app.mutate('campaign',{'candidate':candidate,'revision':0,'boards':'example','titles':'Software Engineer','locations':'United States','skills':'Python',
                          'resume':'Synthetic Person\nBuilt Python APIs at Example 2020-2023. Education: Example University.','consent':True,'enabled':True})
    state=app.mutate('recruiting-project',{'name':'Synthetic role','candidate':candidate,'source_url':'https://example.com/jobs/1','description':'Software engineer with Python APIs in United States.'})
    project=state['projects'][0]['id']
    tasks=sorted([t for t in state['tasks'] if t['project']==project],key=lambda t:t['id'])
    # Satisfy discovery tasks using the actual prerequisite/review transitions.
    for task in tasks[:3]:
        for status in ('active','review','done'):
            row=next(t for t in app.snapshot()['tasks'] if t['id']==task['id'])
            app.mutate('update',{'id':row['id'],'version':row['version'],'status':status,'result':'Verified synthetic opening and candidate identity; fixture only.'})
    return app,candidate,tasks
