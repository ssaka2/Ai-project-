"""Exercise worker supervision through the real command-line entrypoint."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class SupervisionTests(unittest.TestCase):
    def test_dead_background_worker_causes_nonzero_process_exit(self):
        root=Path(__file__).resolve().parent
        for module,function,name in (('recruiting','worker','job-discovery'),
                                     ('worker_runtime','serve','document-dispatcher')):
            with self.subTest(worker=name),tempfile.TemporaryDirectory() as folder:
                # Simulate an unexpectedly returned background loop, not a model
                # response error (which the dispatcher already handles itself).
                code=f'''
import runpy,sys
import {module}
{module}.{function}=lambda *args: None
sys.argv=['office.py','--db',sys.argv[1],'--port','0']
runpy.run_path('office.py',run_name='__main__')
'''
                process=subprocess.Popen([sys.executable,'-c',code,str(Path(folder)/'office.db')],
                    cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                timed_out=False
                try:
                    stdout,stderr=process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    timed_out=True;process.kill();stdout,stderr=process.communicate()
                self.assertFalse(timed_out,'HTTP process kept running after '+name+' stopped')
                self.assertNotEqual(process.returncode,0)
                self.assertIn('Background worker stopped: '+name,stderr)

    def test_real_entrypoint_starts_document_dispatcher(self):
        import time
        import worker_store
        from worker_test_support import fixture
        app,candidate,tasks=fixture(self)
        worker_store.set_settings(app,candidate,True,0,portfolio='Fictional Python API project')
        code='''
import ai_staff,recruiting,runpy,sys
# Replace external I/O only; retain both production worker loops and startup.
ai_staff.generate=lambda model,prompt: 'Synthetic startup verification draft'
recruiting.scan=lambda office: None
sys.argv=['office.py','--db',sys.argv[1],'--port','0']
runpy.run_path('office.py',run_name='__main__')
'''
        process=subprocess.Popen([sys.executable,'-c',code,str(app.path)],
            cwd=Path(__file__).resolve().parent,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        try:
            deadline=time.monotonic()+10
            while time.monotonic()<deadline and process.poll() is None:
                if len(app.snapshot()['ai_drafts'])==3:break
                time.sleep(.05)
            self.assertIsNone(process.poll(),'Server exited during healthy operation')
            drafts=app.snapshot()['ai_drafts']
            self.assertEqual(len(drafts),3,'Production startup must run all document roles')
            self.assertEqual({r['state'] for r in worker_store.list_runs(app,candidate_id=candidate)['runs']},{'succeeded'})
        finally:
            process.terminate();process.communicate(timeout=5)
