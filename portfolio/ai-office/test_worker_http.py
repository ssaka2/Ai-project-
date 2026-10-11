import json
import threading
import socketserver
from http.client import RemoteDisconnected
from unittest.mock import patch
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from contextlib import closing
import office
import worker_store as store
from worker_test_support import fixture


class WorkerHTTPTests(unittest.TestCase):
    def setUp(self):
        self.app,self.candidate,self.tasks=fixture(self)
        self.server=office.make_server(self.app.path,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.token=json.load(urlopen(self.base+'/api/state'))['token']

    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(2)

    def request(self,path,data=None,token=True,origin=None):
        headers={'Content-Type':'application/json'}
        if token:headers['X-Office-Token']=self.token
        if origin:headers['Origin']=origin
        req=Request(self.base+path,headers=headers,data=json.dumps(data).encode() if data is not None else None)
        try:
            with urlopen(req) as response:return response.status,json.load(response)
        except HTTPError as e:return e.code,json.load(e)

    def test_settings_require_origin_token_revision_and_survive_restart(self):
        payload={'candidate':self.candidate,'enabled':True,'revision':0,'portfolio':'Verified synthetic API project'}
        self.assertEqual(self.request('/api/automation-settings',payload,token=False)[0],403)
        self.assertEqual(self.request('/api/automation-settings',payload,origin='https://evil.example')[0],403)
        status,result=self.request('/api/automation-settings',payload)
        self.assertEqual(status,200)
        self.assertEqual(result['revision'],1)
        self.assertEqual(self.request('/api/automation-settings',payload)[0],409)
        self.assertEqual(self.request('/api/automation-settings',{**payload,'candidate':True})[0],400)
        self.assertEqual(office.Office(self.app.path).snapshot()['automation_settings'][0]['enabled'],1)

    def test_get_pagination_and_unsupported_binding(self):
        status,caps=self.request('/api/capabilities');self.assertEqual(status,200)
        self.assertEqual(next(c for c in caps['capabilities'] if c['key']=='submission')['mode'],'unsupported')
        self.assertEqual(self.request(f'/api/worker-runs?candidate={self.candidate}&limit=101')[0],400)
        status,data=self.request(f'/api/worker-runs?candidate={self.candidate}')
        self.assertEqual(status,200);self.assertEqual(data['runs'],[])
        self.assertEqual(self.request('/api/worker-bind',{'task':self.tasks[3]['id'],'executor':'submission','version':1})[0],400)

    def test_cancel_revokes_lease_and_stale_retry_conflicts(self):
        r=store.enqueue(self.app,task_id=self.tasks[3]['id'],task_version=1,candidate_id=self.candidate,executor='cv_draft',fingerprint='fixture',now=100)
        r=store.claim(self.app,now=100)
        status,_=self.request('/api/worker-cancel',{'id':r['id'],'revision':r['revision']})
        self.assertEqual(status,200)
        self.assertFalse(store.finish(self.app,r['id'],r['lease_token'],state='succeeded',now=101))
        self.assertEqual(self.request('/api/worker-retry',{'id':r['id'],'revision':r['revision']})[0],409)

    def test_workflow_status_is_independent_of_history_pagination(self):
        store.enqueue(self.app,task_id=self.tasks[4]['id'],task_version=1,candidate_id=self.candidate,executor='portfolio_draft',fingerprint='old-current',now=100)
        store.claim(self.app,now=100)
        for i in range(30):
            store.enqueue(self.app,task_id=self.tasks[3]['id'],task_version=1,candidate_id=self.candidate,executor='cv_draft',fingerprint=str(i),now=100)
        status,data=self.request(f'/api/worker-status?candidate={self.candidate}')
        self.assertEqual(status,200)
        self.assertEqual(data['candidate_id'],self.candidate)
        self.assertEqual(sum(g['count'] for g in data['groups']),2)
        self.assertEqual({g['state'] for g in data['groups']},{'queued','running'})
        self.assertEqual(self.request('/api/worker-status?candidate=true')[0],400)

    def test_disconnected_poll_does_not_raise_server_error(self):
        with patch.object(socketserver._SocketWriter,'write',side_effect=BrokenPipeError('client closed')), patch.object(self.server,'handle_error') as error:
            with self.assertRaises(RemoteDisconnected):urlopen(self.base+'/api/state')
            error.assert_not_called()

    def test_worker_controls_are_served(self):
        with urlopen(self.base+'/') as response:html=response.read().decode()
        self.assertIn('id="worker-candidate"',html)
        with urlopen(self.base+'/workers.js') as response:self.assertIn('refreshWorkers',response.read().decode())

    def test_unknown_outcome_never_retries(self):
        r=store.enqueue(self.app,task_id=self.tasks[3]['id'],task_version=1,candidate_id=self.candidate,executor='submission',fingerprint='fixture',now=100)
        r=store.claim(self.app,now=100)
        store.recover_expired(self.app,now=341)
        r=store.list_runs(self.app,candidate_id=self.candidate)['runs'][0]
        self.assertEqual(self.request('/api/worker-retry',{'id':r['id'],'revision':r['revision']})[0],400)

if __name__=='__main__':unittest.main()
