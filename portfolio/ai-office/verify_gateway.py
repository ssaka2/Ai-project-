"""Exercise the real Caddy gateway locally using temporary credentials and data."""
import argparse
import base64
import json
import os
import secrets
import socket
import ssl
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from office import make_server


def verify(binary):
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        server=make_server(root/'office.sqlite3',0)
        worker=threading.Thread(target=server.serve_forever,daemon=True)
        worker.start()
        proxy=None
        try:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
            password=secrets.token_urlsafe(32)
            hashed=subprocess.run([binary,'hash-password'],input=password+"\n",text=True,capture_output=True,check=True).stdout.strip()
            env=dict(os.environ,AI_OFFICE_DOMAIN=f'localhost:{port}',AI_OFFICE_OPERATOR='fixture',AI_OFFICE_PASSWORD_HASH=hashed,XDG_DATA_HOME=str(root/'data'),XDG_CONFIG_HOME=str(root/'config'))
            source=Path(__file__).with_name('deploy').joinpath('Caddyfile').read_text()
            source=source.replace('127.0.0.1:4521',f'127.0.0.1:{server.server_port}')
            source='{\n admin off\n skip_install_trust\n auto_https disable_redirects\n}\n'+source.replace('    route {','    tls internal\n    route {',1)
            config=root/'Caddyfile';config.write_text(source)
            subprocess.run([binary,'validate','--config',str(config),'--adapter','caddyfile'],env=env,check=True,capture_output=True)
            with (root/'gateway.log').open('w') as log:
                proxy=subprocess.Popen([binary,'run','--config',str(config),'--adapter','caddyfile'],env=env,stdout=log,stderr=log)
                ca=root/'data/caddy/pki/authorities/local/root.crt'
                deadline=time.monotonic()+15
                while not ca.exists():
                    if proxy.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Gateway did not start')
                    time.sleep(.1)
                context=ssl.create_default_context(cafile=str(ca))
                origin=f'https://localhost:{port}'
                auth='Basic '+base64.b64encode(f'fixture:{password}'.encode()).decode()
                def call(path,body=None,headers=None,authenticated=True):
                    hdr={'Authorization':auth} if authenticated else {}
                    if body is not None:hdr['Content-Type']='application/json'
                    hdr.update(headers or {})
                    request=Request(origin+path,data=json.dumps(body).encode() if body is not None else None,headers=hdr)
                    try:
                        with urlopen(request,context=context,timeout=5) as response:return response.status,response.read()
                    except HTTPError as error:return error.code,error.read()
                for _ in range(50):
                    try:code,_=call('/',authenticated=False);break
                    except URLError:time.sleep(.1)
                else:raise RuntimeError('Gateway not reachable')
                for path in ('/','/api/state','/api/export','/app.js'):
                    assert call(path,authenticated=False)[0]==401,path
                assert call('/api/state',headers={'Authorization':'Basic Zm9vOmJhcg=='})[0]==401
                status,raw=call('/api/state');assert status==200
                state=json.loads(raw)
                payload={'title':'Gateway fixture','brief':'Synthetic only','agent':state['agents'][0]['id']}
                assert call('/api/tasks',payload,{'Origin':origin})[0]==403
                hdr={'Origin':'https://foreign.example','X-Office-Token':state['token']}
                assert call('/api/tasks',payload,hdr)[0]==403
                hdr['Origin']=origin
                assert call('/api/tasks',payload,hdr)[0]==200
                status,raw=call('/api/state');assert status==200
                assert len(json.loads(raw)['tasks'])==1
                assert call('/api/export')[0]==200
            print('PASS: TLS verification, page/API/export authentication, origin protection, write-token enforcement, and persisted API write through Caddy.')
        finally:
            if proxy is not None:
                proxy.terminate();proxy.wait(timeout=10)
            server.shutdown();worker.join();server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--caddy',required=True,help='Path to official Caddy executable')
    verify(parser.parse_args().caddy)
