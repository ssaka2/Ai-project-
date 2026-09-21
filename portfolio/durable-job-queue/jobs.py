"""SQLite job queue with idempotent enqueue, expiring leases, and retry limits."""
import argparse
import hashlib
import json
import sqlite3
import time
import uuid


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, job_key TEXT UNIQUE NOT NULL,
        kind TEXT NOT NULL, payload TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('pending','running','succeeded','dead')),
        attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL,
        available_at REAL NOT NULL, lease_until REAL, token TEXT,
        result TEXT, error TEXT)''')
    db.execute('CREATE INDEX IF NOT EXISTS ix_jobs_ready ON jobs(state,available_at)')
    return db


def enqueue(db, key, kind, payload, max_attempts=3, now=None):
    if not isinstance(key, str) or not key.strip() or len(key) > 100:
        raise ValueError('Job key must be 1–100 characters')
    if kind not in ('sha256', 'word_count', 'fail'):
        raise ValueError('Supported jobs: sha256, word_count, fail')
    if not isinstance(payload, dict) or set(payload) != {'text'} or not isinstance(payload['text'], str):
        raise ValueError('Payload must contain only a text string')
    if len(payload['text']) > 10_000 or type(max_attempts) is not int or not 1 <= max_attempts <= 10:
        raise ValueError('Text limit: 10000 characters; max attempts: 1–10')
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    now = time.time() if now is None else now
    with db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT * FROM jobs WHERE job_key=?', (key,)).fetchone()
        if existing:
            if (existing['kind'], existing['payload'], existing['max_attempts']) != (kind, encoded, max_attempts):
                raise ValueError('Job key is already used for different work')
            return existing['id']
        identifier = str(uuid.uuid4())
        db.execute('''INSERT INTO jobs(id,job_key,kind,payload,state,max_attempts,available_at)
                      VALUES (?,?,?,?,'pending',?,?)''', (identifier, key, kind, encoded, max_attempts, now))
    return identifier


def claim(db, lease_seconds=30, now=None):
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
        raise ValueError('Lease must be 1–3600 seconds')
    now = time.time() if now is None else now
    with db:
        db.execute('BEGIN IMMEDIATE')
        # Recover abandoned attempts. Exhausted jobs become dead, not infinite retries.
        db.execute('''UPDATE jobs SET state=CASE WHEN attempts >= max_attempts THEN 'dead' ELSE 'pending' END,
            token=NULL, lease_until=NULL, available_at=?, error='Worker lease expired'
            WHERE state='running' AND lease_until <= ?''', (now, now))
        job = db.execute('''SELECT * FROM jobs WHERE state='pending' AND available_at <= ?
                            ORDER BY available_at,id LIMIT 1''', (now,)).fetchone()
        if job is None:
            return None
        token = str(uuid.uuid4())
        db.execute('''UPDATE jobs SET state='running', attempts=attempts+1, token=?, lease_until=? WHERE id=?''',
                   (token, now + lease_seconds, job['id']))
        return dict(db.execute('SELECT * FROM jobs WHERE id=?', (job['id'],)).fetchone())


def finish(db, identifier, token, result=None, error=None, now=None):
    now = time.time() if now is None else now
    with db:
        db.execute('BEGIN IMMEDIATE')
        job = db.execute('''SELECT * FROM jobs WHERE id=? AND token=? AND state='running' AND lease_until > ?''',
                         (identifier, token, now)).fetchone()
        if job is None:
            raise ValueError('Lease expired or this worker no longer owns the job')
        state = 'succeeded' if error is None else ('dead' if job['attempts'] >= job['max_attempts'] else 'pending')
        delay = min(60, 2 ** job['attempts']) if error is not None else 0
        db.execute('''UPDATE jobs SET state=?,result=?,error=?,available_at=?,token=NULL,lease_until=NULL WHERE id=?''',
                   (state, json.dumps(result, allow_nan=False) if error is None else None,
                    str(error)[:500] if error is not None else None, now + delay, identifier))
    return state


def renew(db, identifier, token, lease_seconds=30, now=None):
    """Extend an unexpired owned lease; expired/stale workers cannot revive it."""
    if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
        raise ValueError('Lease must be 1–3600 seconds')
    now = time.time() if now is None else now
    with db:
        changed = db.execute('''UPDATE jobs SET lease_until=MAX(lease_until, ?)
            WHERE id=? AND token=? AND state='running' AND lease_until > ?''',
            (now + lease_seconds, identifier, token, now)).rowcount
        if not changed:
            raise ValueError('Lease expired or this worker no longer owns the job')


def execute(job):
    text = json.loads(job['payload'])['text']
    if job['kind'] == 'sha256':
        return {'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()}
    if job['kind'] == 'word_count':
        return {'words': len(text.split())}
    raise RuntimeError('Intentional demo failure')


def work_once(db):
    job = claim(db)
    if job is None:
        return {'worked': False}
    try:
        result = execute(job)
    except Exception as exc:
        state = finish(db, job['id'], job['token'], error=str(exc))
        return {'worked': True, 'id': job['id'], 'state': state}
    state = finish(db, job['id'], job['token'], result=result)
    return {'worked': True, 'id': job['id'], 'state': state, 'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='jobs.db')
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('enqueue')
    add.add_argument('key')
    add.add_argument('kind', choices=['sha256', 'word_count', 'fail'])
    add.add_argument('text')
    add.add_argument('--max-attempts', type=int, default=3)
    commands.add_parser('work')
    commands.add_parser('list')
    args = parser.parse_args()
    db = None
    try:
        db = connect(args.db)
        if args.command == 'enqueue':
            output = {'id': enqueue(db, args.key, args.kind, {'text': args.text}, args.max_attempts)}
        elif args.command == 'work':
            output = work_once(db)
        else:
            output = [dict(row) for row in db.execute('''SELECT id,job_key,kind,state,attempts,max_attempts,
                       available_at,lease_until,result,error FROM jobs ORDER BY available_at,id''')]
        print(json.dumps(output, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    main()
