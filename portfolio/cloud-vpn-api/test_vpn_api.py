import base64
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from vpn_api import make_server

TOKEN = 'test-only-' + 'a' * 40


def peer(n=1):
    return {'name': 'Demo laptop', 'public_key': base64.b64encode(bytes([n]) * 32).decode()}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / 'peers.db'
        self.start()

    def start(self):
        self.server = make_server('127.0.0.1', 0, self.database, TOKEN)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.stop()
        self.temp.cleanup()

    def call(self, method, path, data=None, token=TOKEN, raw=None, content_type='application/json'):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(self.base + path, data=body, method=method,
                                     headers={'Authorization': 'Bearer ' + token, 'Content-Type': content_type})
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            body = response.read().decode()
            return response.status, json.loads(body) if response.headers['Content-Type'] == 'application/json' else body

    def test_health_does_not_claim_tunnel(self):
        status, data = self.call('GET', '/health', token='')
        self.assertEqual(status, 200)
        self.assertEqual(data['tunnel_status'], 'not-managed')

    def test_auth_every_management_route(self):
        for method, path in [('GET', '/api/peers'), ('POST', '/api/peers'), ('DELETE', '/api/peers/x'), ('GET', '/api/wireguard/peers.conf')]:
            self.assertEqual(self.call(method, path, token='wrong')[0], 401)

    def test_create_export_revoke(self):
        status, p = self.call('POST', '/api/peers', peer())
        self.assertEqual(status, 201)
        self.assertEqual(p['address'], '10.77.0.2/32')
        self.assertEqual(self.call('GET', '/api/wireguard/peers.conf')[1], f"[Peer]\nPublicKey = {p['public_key']}\nAllowedIPs = 10.77.0.2/32\n")
        self.assertTrue(self.call('DELETE', '/api/peers/' + p['id'])[1]['apply_required'])
        self.assertEqual(self.call('GET', '/api/wireguard/peers.conf')[1], '')
        self.assertEqual(self.call('GET', '/api/peers')[1][0]['active'], 0)
        self.assertEqual(self.call('POST', '/api/peers', peer(2))[1]['address'], '10.77.0.3/32')

    def test_restart_preserves_records(self):
        p = self.call('POST', '/api/peers', peer())[1]
        self.stop()
        self.start()
        self.assertEqual(self.call('GET', '/api/peers')[1], [p])

    def test_duplicate_key(self):
        self.call('POST', '/api/peers', peer())
        self.assertEqual(self.call('POST', '/api/peers', peer())[0], 409)

    def test_invalid_fields_and_private_key_rejected(self):
        for changes in [{'name': ''}, {'name': 'x\n[Peer]'}, {'public_key': 'invalid'}, {'public_key': base64.b64encode(bytes(32)).decode()}, {'private_key': 'never upload secrets'}]:
            self.assertEqual(self.call('POST', '/api/peers', peer() | changes)[0], 400)
        self.assertEqual(self.call('POST', '/api/peers', [peer()])[0], 400)

    def test_http_body_validation(self):
        self.assertEqual(self.call('POST', '/api/peers', raw=b'{bad')[0], 400)
        self.assertEqual(self.call('POST', '/api/peers', raw=b'x'*4097)[0], 413)
        self.assertEqual(self.call('POST', '/api/peers', peer(), content_type='text/plain')[0], 415)

    def test_concurrent_allocations(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda n: self.call('POST', '/api/peers', peer(n)), range(1, 7)))
        self.assertTrue(all(s == 201 for s, _ in results))
        self.assertEqual(len({p['address'] for _, p in results}), 6)

    def test_unknown_routes(self):
        self.assertEqual(self.call('GET', '/unknown')[0], 404)
        self.assertEqual(self.call('DELETE', '/api/peers/missing')[0], 404)

    def test_weak_token_refused(self):
        with self.assertRaises(ValueError):
            make_server('127.0.0.1', 0, self.database, 'short')


if __name__ == '__main__':
    unittest.main()
