"""Transactional stock ledger with retry-safe movement identifiers."""
import argparse
import json
import sqlite3


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY, name TEXT NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0 CHECK(stock >= 0),
            reorder_point INTEGER NOT NULL CHECK(reorder_point >= 0));
        CREATE TABLE IF NOT EXISTS movements (
            request_id TEXT PRIMARY KEY,
            sku TEXT NOT NULL REFERENCES products(sku),
            delta INTEGER NOT NULL CHECK(delta != 0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE INDEX IF NOT EXISTS ix_movements_sku ON movements(sku);
    ''')
    return db


def add_product(db, sku, name, reorder_point=5):
    if not sku.strip() or not name.strip() or reorder_point < 0:
        raise ValueError('SKU, name and a nonnegative reorder point are required')
    with db:
        db.execute('INSERT INTO products(sku,name,reorder_point) VALUES (?,?,?)',
                   (sku.strip(), name.strip(), reorder_point))


def move(db, sku, delta, request_id):
    if type(delta) is not int or delta == 0 or not request_id.strip():
        raise ValueError('A nonzero integer quantity and request ID are required')
    # A reserved write lock serializes check-and-update across CLI processes.
    with db:
        db.execute('BEGIN IMMEDIATE')
        existing = db.execute('SELECT sku,delta FROM movements WHERE request_id=?',
                              (request_id,)).fetchone()
        if existing:
            if tuple(existing) != (sku, delta):
                raise ValueError('Request ID already belongs to another movement')
            return False
        changed = db.execute('UPDATE products SET stock=stock+? WHERE sku=? AND stock+? >= 0',
                             (delta, sku, delta)).rowcount
        if not changed:
            raise ValueError('Unknown SKU or insufficient stock')
        db.execute('INSERT INTO movements(request_id,sku,delta) VALUES (?,?,?)',
                   (request_id, sku, delta))
    return True


def report(db, low_stock=False):
    query = 'SELECT sku,name,stock,reorder_point FROM products'
    if low_stock:
        query += ' WHERE stock <= reorder_point'
    return [dict(row) for row in db.execute(query + ' ORDER BY sku')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='inventory.db')
    commands = parser.add_subparsers(dest='command', required=True)
    add = commands.add_parser('add')
    add.add_argument('sku')
    add.add_argument('name')
    add.add_argument('--reorder-point', type=int, default=5)
    movement = commands.add_parser('move')
    movement.add_argument('sku')
    movement.add_argument('delta', type=int)
    movement.add_argument('--request-id', required=True)
    listing = commands.add_parser('list')
    listing.add_argument('--low-stock', action='store_true')
    commands.add_parser('history').add_argument('sku')
    args = parser.parse_args()
    db = connect(args.db)
    try:
        if args.command == 'add':
            add_product(db, args.sku, args.name, args.reorder_point)
            result = {'created': args.sku}
        elif args.command == 'move':
            result = {'applied': move(db, args.sku, args.delta, args.request_id)}
        elif args.command == 'history':
            result = [dict(row) for row in db.execute(
                'SELECT * FROM movements WHERE sku=? ORDER BY rowid', (args.sku,))]
        else:
            result = report(db, args.low_stock)
        print(json.dumps(result, indent=2))
    except (ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    finally:
        db.close()


if __name__ == '__main__':
    main()
