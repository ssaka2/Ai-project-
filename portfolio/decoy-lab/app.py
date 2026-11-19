"""Local-only, synthetic decoy-server learning lab. Python 3.11+."""
import argparse
from collections import Counter, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import unquote, urlsplit
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

LESSONS = {
    'reconnaissance': ('Service discovery', 'Requests to common admin or status paths can reveal services. Disable unused endpoints and monitor repeated probes.'),
    'credential_attempt': ('Login attempt', 'Repeated rejected logins can indicate password guessing. Use MFA, rate limits, and alerts across accounts and source addresses.'),
    'secret_probe': ('Secret-file probe', 'Requests for environment or source-control files seek exposed configuration. Keep secrets outside the web root and rotate any exposed credentials.'),
    'traversal_probe': ('Path traversal probe', 'Parent-directory markers may indicate attempts to escape a web directory. Resolve paths safely and use strict file allowlists.'),
    'injection_probe': ('Injection-like input', 'SQL-like input can signal an injection attempt. Parameterized queries and least-privileged database accounts reduce the risk.'),
    'ordinary_request': ('Ordinary request', 'A request alone does not prove malicious intent. Compare patterns with expected traffic and investigate context.'),
}


def classify(path, body=''):
    decoded = unquote(urlsplit(path).path).lower()
    if '..' in decoded:
        return 'traversal_probe'
    if decoded in ('/.env', '/.git/config'):
        return 'secret_probe'
    if "' or '1'='1" in body.lower():
        return 'injection_probe'
    if decoded == '/login':
        return 'credential_attempt'
    if decoded in ('/admin', '/server-status', '/api/status'):
        return 'reconnaissance'
    return 'ordinary_request'


class Lab(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, port=8080):
        self.events = deque(maxlen=1000)
        self.lock = threading.Lock()
        self.simulation_lock = threading.Lock()
        self.token = secrets.token_urlsafe(32)
        super().__init__(('127.0.0.1', port), Handler)

    def record(self, method, path, body, status):
        kind = classify(path, body)
        # Store categories only: never retain passwords, raw bodies, or query strings.
        safe_path = urlsplit(path).path[:160]
        with self.lock:
            self.events.append({'time': datetime.now(timezone.utc).isoformat(),
                                'method': method, 'path': safe_path,
                                'category': kind, 'status': status,
                                'source': 'loopback'})

    def snapshot(self):
        with self.lock:
            rows = list(self.events)
        return {'events': rows, 'counts': dict(Counter(e['category'] for e in rows)),
                'lessons': LESSONS, 'capacity': 1000}

    def simulate(self):
        # No target option, external URLs, proxy use, redirects, shells, or exploits.
        # Every request goes to this instance's exact loopback address and port.
        opener = build_opener(ProxyHandler({}))
        base = f'http://127.0.0.1:{self.server_port}'
        cases = [('/', None), ('/admin', None), ('/server-status', None),
                 ('/.env', None), ('/.git/config', None),
                 ('/files/..%2F..%2Flab-marker.txt', None),
                 ('/login', b'username=demo&password=synthetic-one'),
                 ('/login', b'username=demo&password=synthetic-two'),
                 ('/login', b"username=' OR '1'='1&password=synthetic")]
        with self.simulation_lock:
            for path, data in cases:
                request = Request(base + path, data=data,
                                  headers={'User-Agent': 'DecoyLab-Synthetic/1.0'})
                try:
                    with opener.open(request, timeout=5) as response:
                        response.read()
                except HTTPError as error:
                    error.read()
                    error.close()
        return len(cases)


class Handler(BaseHTTPRequestHandler):
    server_version = 'DecoyLab/1.0'
    sys_version = ''

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self, *_):
        pass  # Avoid retaining request bodies, credentials, or terminal control text.

    def reply(self, status, value, content_type='application/json'):
        payload = (json.dumps(value) if content_type == 'application/json' else value).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type + '; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def allowed_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',
                                            f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.allowed_host():
            return self.reply(403, {'error': 'Use the printed localhost URL.'})
        path = urlsplit(self.path).path
        if path == '/lab/events':
            return self.reply(200, self.server.snapshot())
        static = {'/lab': ('index.html', 'text/html'), '/lab/app.js': ('app.js', 'text/javascript'),
                  '/lab/style.css': ('style.css', 'text/css')}
        if path in static:
            filename, mime = static[path]
            text = (Path(__file__).parent / filename).read_text()
            if filename == 'index.html':
                text = text.replace('{{TOKEN}}', self.server.token)
            return self.reply(200, text, mime)
        status = 200 if path == '/' else 404
        self.server.record('GET', self.path, '', status)
        return self.reply(status, {'service': 'Synthetic company portal',
                                   'message': 'Decoy only; no real files or accounts.'})

    def do_POST(self):
        if not self.allowed_host():
            return self.reply(403, {'error': 'Invalid host'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.reply(400, {'error': 'Invalid body length'})
        if not 0 <= length <= 4096 or self.headers.get('Transfer-Encoding'):
            self.close_connection = True
            return self.reply(413, {'error': 'Body too large or unsupported framing'})
        body = self.rfile.read(length).decode('utf-8', errors='replace')
        path = urlsplit(self.path).path
        if path.startswith('/lab/'):
            origin = self.headers.get('Origin')
            if (self.headers.get('X-Lab-Token') != self.server.token or
                (origin and origin not in (f'http://localhost:{self.server.server_port}',
                                          f'http://127.0.0.1:{self.server.server_port}'))):
                return self.reply(403, {'error': 'Dashboard token and same origin required'})
            if path == '/lab/simulate':
                return self.reply(200, {'requests': self.server.simulate()})
            if path == '/lab/clear':
                with self.server.lock:
                    self.server.events.clear()
                return self.reply(200, {'cleared': True})
            return self.reply(404, {'error': 'Unknown lab operation'})
        status = 401 if path == '/login' else 404
        self.server.record('POST', self.path, body, status)
        return self.reply(status, {'message': 'Rejected by synthetic decoy; no authentication performed.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    lab = Lab(args.port)
    print(f'Open http://127.0.0.1:{lab.server_port}/lab', flush=True)
    try:
        lab.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        lab.server_close()
