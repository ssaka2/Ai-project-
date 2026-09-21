"""Persistent, namespaced agent memory with provenance and expiration."""
import argparse
import json
import math
import re
import sqlite3
import time
import uuid


def text(value, label, maximum):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f'{label} must contain 1–{maximum} characters')
    return value


class MemoryStore:
    def __init__(self, path, clock=time.time):
        self.clock = clock
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute('''CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY, namespace TEXT NOT NULL, content TEXT NOT NULL,
            source TEXT NOT NULL, created REAL NOT NULL, expires REAL)''')
        self.db.execute('CREATE INDEX IF NOT EXISTS memory_namespace ON memories(namespace, expires)')
        self.db.commit()

    def close(self):
        self.db.close()

    def add(self, namespace, content, source, ttl=None):
        text(namespace, 'namespace', 100)
        text(content, 'content', 10000)
        text(source, 'source', 1000)
        if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, (int, float))
                                or not math.isfinite(ttl) or ttl <= 0):
            raise ValueError('ttl must be a positive finite number of seconds')
        now = self.clock()
        identifier = uuid.uuid4().hex
        with self.db:
            self.db.execute('INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)',
                            (identifier, namespace, content, source, now,
                             None if ttl is None else now + ttl))
        return identifier

    def recall(self, namespace, query, limit=5):
        text(namespace, 'namespace', 100)
        text(query, 'query', 1000)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('limit must be an integer from 1 to 100')
        tokens = set(re.findall(r'\w+', query.casefold()))
        matches = []
        for row in self.db.execute('SELECT * FROM memories WHERE namespace=? AND (expires IS NULL OR expires>?)',
                                   (namespace, self.clock())):
            item = dict(row)
            words = set(re.findall(r'\w+', item['content'].casefold()))
            score = len(tokens & words) / len(tokens) if tokens else 0
            if score:
                matches.append(item | {'score': score})
        return sorted(matches, key=lambda item: (-item['score'], -item['created'], item['id']))[:limit]

    def delete(self, namespace, identifier):
        text(namespace, 'namespace', 100)
        with self.db:
            return self.db.execute('DELETE FROM memories WHERE namespace=? AND id=?',
                                   (namespace, identifier)).rowcount == 1

    def purge_expired(self):
        with self.db:
            return self.db.execute('DELETE FROM memories WHERE expires<=?', (self.clock(),)).rowcount


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='memory.sqlite3')
    sub = parser.add_subparsers(dest='command', required=True)
    add = sub.add_parser('add')
    add.add_argument('namespace'); add.add_argument('content'); add.add_argument('--source', required=True)
    add.add_argument('--ttl', type=float)
    recall = sub.add_parser('recall')
    recall.add_argument('namespace'); recall.add_argument('query'); recall.add_argument('--limit', type=int, default=5)
    delete = sub.add_parser('delete')
    delete.add_argument('namespace'); delete.add_argument('id')
    sub.add_parser('purge')
    sub.add_parser('demo')
    args = parser.parse_args()
    store = MemoryStore(':memory:' if args.command == 'demo' else args.db)
    try:
        if args.command == 'add':
            result = store.add(args.namespace, args.content, args.source, args.ttl)
        elif args.command == 'recall':
            result = store.recall(args.namespace, args.query, args.limit)
        elif args.command == 'delete':
            result = store.delete(args.namespace, args.id)
        elif args.command == 'purge':
            result = store.purge_expired()
        else:
            store.add('demo-agent', 'User prefers Python examples with unit tests.', 'synthetic-session:1')
            store.add('other-agent', 'Private Python preference.', 'synthetic-session:2')
            result = store.recall('demo-agent', 'Python tests')
        print(json.dumps(result, indent=2))
    except (ValueError, sqlite3.Error) as exc:
        parser.exit(1, f'Memory operation failed: {exc}\n')
    finally:
        store.close()


if __name__ == '__main__':
    main()
