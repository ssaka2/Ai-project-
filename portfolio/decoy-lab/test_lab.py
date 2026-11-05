import json
import threading
import unittest
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
from app import Lab


class LabTests(unittest.TestCase):
    def setUp(self):
        self.lab = Lab(0)
        self.thread = threading.Thread(target=self.lab.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.lab.server_port}'
        self.client = build_opener(ProxyHandler({}))

    def tearDown(self):
        self.lab.shutdown()
        self.lab.server_close()
        self.thread.join()

    def request(self, path, data=None, headers=None):
        request = Request(self.base + path, data=data, headers=headers or {})
        try:
            response = self.client.open(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read().decode()

    def test_simulation_uses_http_and_records_all_categories(self):
        status, body = self.request('/lab/simulate', b'', {'X-Lab-Token': self.lab.token})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['requests'], 9)
        snapshot = self.lab.snapshot()
        self.assertEqual(len(snapshot['events']), 9)
        self.assertEqual(snapshot['counts'], {'ordinary_request': 1, 'reconnaissance': 2,
                         'secret_probe': 2, 'traversal_probe': 1,
                         'credential_attempt': 2, 'injection_probe': 1})
        self.assertTrue(all(e['status'] == 401 for e in snapshot['events'] if e['method'] == 'POST'))
        self.assertNotIn('synthetic-one', json.dumps(snapshot))

    def test_dashboard_mutations_require_token_and_valid_origin(self):
        self.assertEqual(self.request('/lab/simulate', b'')[0], 403)
        self.assertEqual(self.request('/lab/clear', b'', {'X-Lab-Token': self.lab.token, 'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(self.lab.snapshot()['events'], [])

    def test_host_validation(self):
        self.assertEqual(self.request('/lab/events', headers={'Host': 'example.com'})[0], 403)

    def test_redaction_and_no_real_file_access(self):
        self.request('/login?password=private-query', b'username=x&password=private-body')
        status, body = self.request('/files/..%2F..%2Fetc/passwd')
        self.assertEqual(status, 404)
        self.assertNotIn('root:', body)
        serialized = json.dumps(self.lab.snapshot())
        self.assertNotIn('private-query', serialized)
        self.assertNotIn('private-body', serialized)

    def test_dashboard_and_clear(self):
        status, body = self.request('/lab')
        self.assertEqual(status, 200)
        self.assertIn(self.lab.token, body)
        self.request('/admin')
        self.assertEqual(self.request('/lab/clear', b'', {'X-Lab-Token': self.lab.token})[0], 200)
        self.assertEqual(self.lab.snapshot()['events'], [])

    def test_bounded_memory_and_oversized_body(self):
        for _ in range(1005):
            self.lab.record('GET', '/admin', '', 404)
        self.assertEqual(len(self.lab.snapshot()['events']), 1000)
        self.assertEqual(self.request('/login', b'x' * 4097)[0], 413)


if __name__ == '__main__':
    unittest.main()
