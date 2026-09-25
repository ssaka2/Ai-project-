"""Verify a running Compose API before and after a container restart."""
import base64
import json
import os
import subprocess
import urllib.error
import urllib.request
import time

BASE = 'http://127.0.0.1:8090'
TOKEN = os.environ['VPN_API_TOKEN']


def call(method, path, data=None, token=TOKEN):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(data).encode() if data else None,
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=3)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


def ready():
    for _ in range(30):
        try:
            if call('GET', '/health')[0] == 200:
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError('Container readiness deadline exceeded')


ready()
assert call('GET', '/api/peers', token='wrong')[0] == 401
status, peer = call('POST', '/api/peers', {'name': 'Container demo', 'public_key': base64.b64encode(os.urandom(32)).decode()})
assert status == 201
subprocess.run(['docker', 'compose', 'restart', 'api'], check=True)
ready()
assert peer in call('GET', '/api/peers')[1]
assert call('DELETE', '/api/peers/' + peer['id'])[0] == 200
print('PASS: container authentication, create, restart persistence, and revoke')
