import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from jsonschema.exceptions import ValidationError
from contracts import generate, strict_json, validate, validator

SCHEMA = json.loads(Path(__file__).with_name('schema.json').read_text())
GOOD = {'category': 'technical', 'summary': 'Test issue', 'priority': 2}

class ContractsTests(unittest.TestCase):
    def test_fixture(self):
        self.assertEqual(validate(json.dumps(GOOD), SCHEMA), GOOD)

    def test_contract_rejects_semantic_errors(self):
        for change in ({'priority': 4}, {'priority': True}, {'category': 'unknown'},
                       {'summary': ''}, {'extra': 'unsafe'}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate(json.dumps(GOOD | change), SCHEMA)

    def test_missing_field(self):
        with self.assertRaises(ValidationError):
            validate('{}', SCHEMA)

    def test_strict_json(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}', '```json\n{}\n```', '{} trailing'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                strict_json(raw)

    def test_size_limit(self):
        with self.assertRaises(ValueError):
            strict_json(' ' * 1_048_577)

    def test_no_external_or_recursive_refs(self):
        for ref in ('https://example.com/schema', '#'):
            with self.assertRaises(ValueError):
                validator({'properties': {'x': {'$ref': ref}}})

    def test_http_adapter_and_invalid_model_output(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append((self.path, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({'message': {'content': json.dumps(GOOD if len(captured) == 1 else {})}}).encode())
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            self.assertEqual(generate('Classify synthetic ticket', SCHEMA, 'test-model', server.server_port), GOOD)
            self.assertEqual(captured[0][0], '/api/chat')
            self.assertEqual(captured[0][1]['format'], SCHEMA)
            self.assertFalse(captured[0][1]['stream'])
            with self.assertRaises(ValidationError):
                generate('Classify ticket', SCHEMA, 'test-model', server.server_port)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

if __name__ == '__main__':
    unittest.main()
