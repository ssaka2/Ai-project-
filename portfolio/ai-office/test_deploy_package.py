"""Verify the documented fresh-install bundle, not the source checkout."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


class DeploymentPackageTests(unittest.TestCase):
    def test_documented_runtime_bundle_starts_and_serves_worker_assets(self):
        root=Path(__file__).resolve().parent
        readme=(root/'deploy'/'README.md').read_text()
        lines=[line for line in readme.splitlines() if line.startswith('sudo install -m 0644 ') and line.endswith(' /opt/ai-office/')]
        self.assertEqual(len(lines),1,'Keep one explicit runtime installation command')
        files=shlex.split(lines[0])[4:-1]
        with tempfile.TemporaryDirectory() as folder:
            for name in files:
                self.assertEqual(Path(name).name,name,'Runtime files must be flat source files')
                shutil.copy2(root/name,Path(folder)/name)
            code='''
import json, threading
from urllib.request import urlopen
from pathlib import Path
import office
import worker_runtime
server=office.make_server('fixture.sqlite3',0)
thread=threading.Thread(target=server.serve_forever,daemon=True)
thread.start()
try:
    base=f'http://127.0.0.1:{server.server_port}'
    with urlopen(base+'/api/state') as response:
        state=json.load(response)
    assert len(state['agents'])==12
    with urlopen(base+'/workers.js') as response:
        assert 'refreshWorkflowWorkers' in response.read().decode()
    with urlopen(base+'/api/capabilities') as response:
        caps=json.load(response)['capabilities']
    assert any(c['key']=='cv_draft' for c in caps)
    assert Path('verify_pilot.py').is_file()
    assert Path('verify_workers.py').is_file()
finally:
    server.shutdown();server.server_close();thread.join(2)
'''
            env=dict(os.environ);env.pop('PYTHONPATH',None)
            result=subprocess.run([sys.executable,'-c',code],cwd=folder,env=env,text=True,capture_output=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
