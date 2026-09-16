"""Validate a synthetic flight CSV and atomically load a SQL reporting database."""
import argparse
import csv
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

FIELDS = ['flight_id', 'flight_date', 'origin', 'destination', 'delay_minutes', 'cancelled']


def validate(row):
    if None in row or any(row.get(key) is None for key in FIELDS):
        raise ValueError('Incorrect column count')
    if not row['flight_id'].strip():
        raise ValueError('Missing flight ID')
    day = date.fromisoformat(row['flight_date']).isoformat()
    origin, destination = row['origin'].strip().upper(), row['destination'].strip().upper()
    if not all(re.fullmatch('[A-Z]{3}', airport) for airport in (origin, destination)):
        raise ValueError('Airport codes must contain three letters')
    if origin == destination:
        raise ValueError('Origin and destination must differ')
    if row['cancelled'] not in ('0', '1'):
        raise ValueError('Cancelled must be 0 or 1')
    cancelled = int(row['cancelled'])
    delay = None if cancelled else int(row['delay_minutes'])
    if delay is not None and not -180 <= delay <= 2880:
        raise ValueError('Delay outside supported range (-180 to 2880 minutes)')
    return row['flight_id'].strip(), day, origin, destination, delay, cancelled


def load(db, source):
    db.execute('''CREATE TABLE IF NOT EXISTS flights (
        flight_id TEXT NOT NULL, flight_date TEXT NOT NULL,
        origin TEXT NOT NULL, destination TEXT NOT NULL,
        delay_minutes INTEGER, cancelled INTEGER NOT NULL CHECK(cancelled IN (0,1)),
        PRIMARY KEY(flight_id, flight_date))''')
    accepted, rejected, seen = [], [], set()
    with open(source, newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != FIELDS:
            raise ValueError('Expected CSV columns: ' + ','.join(FIELDS))
        for line, row in enumerate(reader, start=2):
            try:
                values = validate(row)
                if values[:2] in seen:
                    raise ValueError('Duplicate flight ID and date within input')
                seen.add(values[:2])
                accepted.append(values)
            except (ValueError, TypeError) as exc:
                rejected.append({'line': line, 'reason': str(exc)})
    # Upserts make rerunning a file safe and allow corrected records.
    with db:
        db.executemany('''INSERT INTO flights VALUES (?,?,?,?,?,?)
            ON CONFLICT(flight_id,flight_date) DO UPDATE SET
            origin=excluded.origin, destination=excluded.destination,
            delay_minutes=excluded.delay_minutes, cancelled=excluded.cancelled''', accepted)
    return {'accepted': len(accepted), 'rejected': rejected}


def report(db):
    db.row_factory = sqlite3.Row
    sql = Path(__file__).with_name('report.sql').read_text(encoding='utf-8')
    return [dict(row) for row in db.execute(sql)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--db', default='flights.db')
    args = parser.parse_args()
    db = None
    try:
        db = sqlite3.connect(args.db)
        quality = load(db, args.source)
        print(json.dumps({'quality': quality, 'airports': report(db)}, indent=2))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    main()
