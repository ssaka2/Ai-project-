"""Local document retrieval with BM25 ranking and verifiable line citations."""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
MAX_CORPUS_BYTES = 20_000_000


def open_index(path):
    db = sqlite3.connect(path)
    try:
        db.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
            source UNINDEXED, start_line UNINDEXED, end_line UNINDEXED,
            sha256 UNINDEXED, body, tokenize='unicode61')''')
        db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        return db
    except sqlite3.Error:
        db.close()
        raise


def chunk_text(text, lines_per_chunk=24, overlap=4):
    if not 1 <= lines_per_chunk <= 200 or not 0 <= overlap < lines_per_chunk:
        raise ValueError('Chunk size must be 1–200 lines; overlap must be smaller')
    lines = text.splitlines()
    start = 0
    while start < len(lines):
        end = min(start + lines_per_chunk, len(lines))
        body = '\n'.join(lines[start:end])
        if body.strip():
            yield start + 1, end, body
        if end == len(lines):
            break
        start = end - overlap


def index_documents(db, root, lines_per_chunk=24, overlap=4):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Corpus must be a directory')
    # Validate configuration even for an empty corpus.
    list(chunk_text('', lines_per_chunk, overlap))
    rows, document_count, total_bytes = [], 0, 0
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part.startswith('.') for part in relative.parts):
            continue
        if path.suffix.lower() not in ('.md', '.txt') or not path.is_file():
            continue
        if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root):
            raise ValueError(f'Symlinks are not supported: {relative}')
        if not path.resolve().is_relative_to(root):
            raise ValueError(f'File lies outside corpus: {relative}')
        with path.open('rb') as handle:
            data = handle.read(MAX_FILE_BYTES + 1)
        total_bytes += len(data)
        if len(data) > MAX_FILE_BYTES or total_bytes > MAX_CORPUS_BYTES:
            raise ValueError('Corpus exceeds the 1 MB/file or 20 MB/corpus limit')
        text = data.decode('utf-8-sig')
        digest = hashlib.sha256(data).hexdigest()
        document_count += 1
        rows.extend((relative.as_posix(), start, end, digest, body)
                    for start, end, body in chunk_text(text, lines_per_chunk, overlap))
    if not rows:
        raise ValueError('Corpus has no nonempty Markdown or text documents')
    # A replacement snapshot removes stale documents and chunks. Failed reads
    # or failed inserts preserve the previously committed index.
    with db:
        db.execute('DELETE FROM chunks')
        db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?)', rows)
        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('root', str(root)))
    return {'documents': document_count, 'chunks': len(rows)}


def search(db, query, limit=5):
    if not isinstance(query, str) or len(query) > 1000 or not 1 <= limit <= 20:
        raise ValueError('Query must be at most 1000 characters; limit must be 1–20')
    # Treat all user input as literal terms, never as FTS query operators.
    terms = list(dict.fromkeys(re.findall(r'\w+', query, flags=re.UNICODE)))
    if not terms:
        raise ValueError('Query needs at least one word')
    expression = ' OR '.join('"' + term + '"' for term in terms)
    rows = db.execute('''SELECT source,start_line,end_line,sha256,body,bm25(chunks) AS rank
        FROM chunks WHERE chunks MATCH ? ORDER BY rank,source,start_line LIMIT ?''',
        (expression, limit)).fetchall()
    return [{'source': row[0], 'start_line': int(row[1]), 'end_line': int(row[2]),
             'sha256': row[3], 'text': row[4], 'rank': row[5],
             'citation': f'{row[0]}:L{row[1]}-L{row[2]}'} for row in rows]


def evaluate(db, cases, limit=5):
    if not cases:
        raise ValueError('Evaluation needs at least one case')
    details = []
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get('query'), str):
            raise ValueError('Each case needs a query')
        expected = case.get('expected_sources')
        if not isinstance(expected, list) or not expected or any(not isinstance(x, str) or not x for x in expected):
            raise ValueError('Each case needs nonempty expected_sources')
        expected = set(expected)
        # Rank documents by the first matching chunk; multiple chunks from
        # one document do not count as multiple relevant documents.
        sources = list(dict.fromkeys(hit['source'] for hit in search(db, case['query'], limit)))
        ranks = [index + 1 for index, source in enumerate(sources) if source in expected]
        details.append({'query': case['query'], 'sources': sources,
                        'recall': len(expected.intersection(sources)) / len(expected),
                        'reciprocal_rank': 1 / min(ranks) if ranks else 0})
    return {'queries': len(details), 'chunk_limit': limit,
            'mean_recall': sum(x['recall'] for x in details) / len(details),
            'mean_reciprocal_rank': sum(x['reciprocal_rank'] for x in details) / len(details),
            'details': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='knowledge.db')
    commands = parser.add_subparsers(dest='command', required=True)
    ingest = commands.add_parser('index')
    ingest.add_argument('folder')
    ingest.add_argument('--chunk-lines', type=int, default=24)
    ingest.add_argument('--overlap', type=int, default=4)
    find = commands.add_parser('search')
    find.add_argument('query')
    find.add_argument('--limit', type=int, default=5)
    score = commands.add_parser('evaluate')
    score.add_argument('cases', type=Path)
    score.add_argument('--limit', type=int, default=5)
    args = parser.parse_args()
    db = None
    try:
        db = open_index(args.db)
        if args.command == 'index':
            result = index_documents(db, args.folder, args.chunk_lines, args.overlap)
        elif args.command == 'search':
            result = {'query': args.query, 'matches': search(db, args.query, args.limit)}
        else:
            cases = json.loads(args.cases.read_text(encoding='utf-8'))
            if not isinstance(cases, list):
                raise ValueError('Cases file must contain a JSON array')
            result = evaluate(db, cases, args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (OSError, ValueError, sqlite3.Error) as exc:
        parser.exit(2, f'Error: {exc}\n')
    finally:
        if db is not None:
            db.close()


if __name__ == '__main__':
    main()
