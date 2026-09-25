"""Small WireGuard peer registry. Run behind private access or a TLS reverse proxy."""
import base64
import binascii
from contextlib import contextmanager
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import uuid


class Registry:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS peers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, public_key TEXT UNIQUE NOT NULL,
                address TEXT UNIQUE NOT NULL, active INTEGER NOT NULL DEFAULT 1)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM peers ORDER BY rowid')]

    def create(self, data):
        if not isinstance(data, dict) or set(data) != {'name', 'public_key'}:
            raise ValueError('Provide exactly name and public_key; never send a private key.')
        name, key = data['name'], data['public_key']
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(c) < 32 for c in name):
            raise ValueError('Name must contain 1–80 printable characters.')
        try:
            decoded = base64.b64decode(key, validate=True) if isinstance(key, str) else b''
        except (ValueError, binascii.Error):
            decoded = b''
        if len(decoded) != 32 or decoded == bytes(32) or base64.b64encode(decoded).decode() != key:
            raise ValueError('public_key must be a canonical base64 WireGuard public key (32 bytes).')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            used = {row[0] for row in db.execute('SELECT address FROM peers')}
            address = next((f'10.77.0.{n}/32' for n in range(2, 255) if f'10.77.0.{n}/32' not in used), None)
            if address is None:
                raise OverflowError('Address pool exhausted; revoked addresses are reserved.')
            peer = dict(id=str(uuid.uuid4()), name=name.strip(), public_key=key, address=address, active=1)
            db.execute('INSERT INTO peers (id,name,public_key,address,active) VALUES (:id,:name,:public_key,:address,:active)', peer)
            return peer

    def revoke(self, peer_id):
        with self.connect() as db:
            return db.execute('UPDATE peers SET active=0 WHERE id=?', (peer_id,)).rowcount > 0

    def config(self):
        return '\n'.join(f"[Peer]\nPublicKey = {p['public_key']}\nAllowedIPs = {p['address']}\n" for p in self.list() if p['active'])


def make_server(host, port, database, token):
    if len(token) < 32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('VPN_API_TOKEN must be at least 32 ASCII characters without whitespace.')
    registry = Registry(database)

    class Handler(BaseHTTPRequestHandler):
        server_version = 'VPNRegistry/1.0'

        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass  # Never log authorization headers or request bodies.

        def reply(self, status, value, content_type='application/json'):
            body = json.dumps(value).encode() if content_type == 'application/json' else value.encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if status == 401:
                self.send_header('WWW-Authenticate', 'Bearer')
            self.end_headers()
            self.wfile.write(body)

        def dispatch(self):
            if self.command == 'GET' and self.path == '/health':
                with registry.connect() as db:
                    db.execute('SELECT count(*) FROM peers').fetchone()
                return self.reply(200, {'status': 'ready', 'tunnel_status': 'not-managed'})
            if not hmac.compare_digest(self.headers.get('Authorization', '').encode(), ('Bearer ' + token).encode()):
                return self.reply(401, {'error': 'Bearer token required.'})
            if self.command == 'GET' and self.path == '/api/peers':
                return self.reply(200, registry.list())
            if self.command == 'GET' and self.path == '/api/wireguard/peers.conf':
                return self.reply(200, registry.config(), 'text/plain; charset=utf-8')
            if self.command == 'DELETE' and self.path.startswith('/api/peers/'):
                peer_id = self.path[len('/api/peers/'):]
                if registry.revoke(peer_id):
                    return self.reply(200, {'revoked': True, 'apply_required': True})
                return self.reply(404, {'error': 'Peer not found.'})
            if self.command == 'POST' and self.path == '/api/peers':
                if self.headers.get('Transfer-Encoding'):
                    return self.reply(400, {'error': 'Chunked bodies are not supported.'})
                lengths = self.headers.get_all('Content-Length', [])
                if len(lengths) != 1 or not lengths[0].isdigit():
                    return self.reply(400, {'error': 'One valid Content-Length is required.'})
                length = int(lengths[0])
                if not 0 < length <= 4096:
                    return self.reply(413, {'error': 'Body must be 1–4096 bytes.'})
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    return self.reply(415, {'error': 'Use application/json.'})
                data = json.loads(self.rfile.read(length))
                return self.reply(201, registry.create(data))
            self.reply(404, {'error': 'Route not found.'})

        def handle_request(self):
            try:
                self.dispatch()
            except (ValueError, UnicodeError):
                self.reply(400, {'error': 'Invalid JSON or peer fields. Use name and a valid public_key only.'})
            except sqlite3.IntegrityError:
                self.reply(409, {'error': 'Public key already registered, including revoked peers.'})
            except OverflowError:
                self.reply(409, {'error': 'Address pool exhausted.'})
            except (sqlite3.Error, OSError):
                self.reply(503, {'error': 'Storage or connection unavailable.'})

        do_GET = do_POST = do_DELETE = handle_request

    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    server = make_server(os.environ.get('VPN_API_HOST', '127.0.0.1'), int(os.environ.get('PORT', '8090')),
                         os.environ.get('VPN_DATABASE', 'data/peers.db'), os.environ.get('VPN_API_TOKEN', ''))
    print(f'VPN registry listening on {server.server_address}; tunnel changes require manual application.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
