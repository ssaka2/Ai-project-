"""Persistent approval state machine for a trusted local agent executor."""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid


def canonical(tool, arguments):
    if not isinstance(tool, str) or not tool.strip() or len(tool) > 100:
        raise ValueError('tool must be a nonempty string up to 100 characters')
    if not isinstance(arguments, dict):
        raise ValueError('arguments must be an object')
    value = json.dumps({'tool': tool, 'arguments': arguments}, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(value.encode()) > 16384:
        raise ValueError('request exceeds 16 KiB')
    return value


class ApprovalQueue:
    def __init__(self, database, clock=time.time):
        self.database = str(database)
        self.clock = clock
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS requests (
                id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, digest TEXT NOT NULL, state TEXT NOT NULL,
                created REAL NOT NULL, expires REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL REFERENCES requests(id),
                action TEXT NOT NULL, actor TEXT NOT NULL, at REAL NOT NULL);
            ''')

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def submit(self, request_key, tool, arguments, ttl=300):
        if not isinstance(request_key, str) or not 1 <= len(request_key) <= 100:
            raise ValueError('request_key must contain 1–100 characters')
        if isinstance(ttl, bool) or not isinstance(ttl, int) or not 1 <= ttl <= 86400:
            raise ValueError('ttl must be 1–86400 seconds')
        payload = canonical(tool, arguments)
        now = self.clock()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT * FROM requests WHERE request_key=?', (request_key,)).fetchone()
            if existing:
                if existing['payload'] != payload:
                    raise ValueError('idempotency key already belongs to different arguments')
                return dict(existing)
            request_id = str(uuid.uuid4())
            db.execute('INSERT INTO requests VALUES (?,?,?,?,?,?,?)',
                       (request_id, request_key, payload, hashlib.sha256(payload.encode()).hexdigest(), 'pending', now, now + ttl))
            db.execute('INSERT INTO events(request_id,action,actor,at) VALUES (?,?,?,?)', (request_id, 'submitted', 'agent', now))
        return self.get(request_id)

    def get(self, request_id):
        with self.db() as db:
            row = db.execute('SELECT * FROM requests WHERE id=?', (request_id,)).fetchone()
        if row is None:
            raise KeyError('request not found')
        result = dict(row)
        result['effective_state'] = 'expired' if row['state'] in ('pending', 'approved') and self.clock() >= row['expires'] else row['state']
        return result

    def decide(self, request_id, approved, actor):
        if not isinstance(approved, bool) or not isinstance(actor, str) or not actor.strip() or len(actor) > 100:
            raise ValueError('a boolean decision and reviewer name are required')
        now = self.clock()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            state = 'approved' if approved else 'denied'
            changed = db.execute('UPDATE requests SET state=? WHERE id=? AND state=? AND expires>?', (state, request_id, 'pending', now)).rowcount
            if changed != 1:
                raise ValueError('request missing, expired, or already decided')
            db.execute('INSERT INTO events(request_id,action,actor,at) VALUES (?,?,?,?)', (request_id, state, actor.strip(), now))
        return self.get(request_id)

    def consume(self, request_id, tool, arguments):
        payload = canonical(tool, arguments)
        now = self.clock()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            changed = db.execute('UPDATE requests SET state=? WHERE id=? AND state=? AND expires>? AND payload=?', ('consumed', request_id, 'approved', now, payload)).rowcount
            if changed != 1:
                raise ValueError('no unused, unexpired approval for these exact arguments')
            db.execute('INSERT INTO events(request_id,action,actor,at) VALUES (?,?,?,?)', (request_id, 'consumed', 'executor', now))
        return json.loads(payload)

    def audit(self, request_id):
        self.get(request_id)
        with self.db() as db:
            return [dict(row) for row in db.execute('SELECT action,actor,at FROM events WHERE request_id=? ORDER BY sequence', (request_id,))]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='data/approvals.db')
    sub = parser.add_subparsers(dest='command', required=True)
    create = sub.add_parser('submit')
    create.add_argument('--key', required=True)
    create.add_argument('--tool', required=True)
    create.add_argument('--arguments', required=True, help='JSON object; use synthetic nonsecret data')
    create.add_argument('--ttl', type=int, default=300)
    for name in ('show', 'audit', 'approve', 'deny', 'consume'):
        action = sub.add_parser(name)
        action.add_argument('id')
        if name in ('approve', 'deny'):
            action.add_argument('--reviewer', required=True)
        if name == 'consume':
            action.add_argument('--tool', required=True)
            action.add_argument('--arguments', required=True)
    args = parser.parse_args()
    queue = ApprovalQueue(args.db)
    try:
        if args.command == 'submit':
            result = queue.submit(args.key, args.tool, json.loads(args.arguments), args.ttl)
        elif args.command in ('approve', 'deny'):
            result = queue.decide(args.id, args.command == 'approve', args.reviewer)
        elif args.command == 'consume':
            result = queue.consume(args.id, args.tool, json.loads(args.arguments))
        elif args.command == 'audit':
            result = queue.audit(args.id)
        else:
            result = queue.get(args.id)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
