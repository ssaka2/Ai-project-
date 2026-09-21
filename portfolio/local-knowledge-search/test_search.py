import json
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path
from search import chunk_text, evaluate, index_documents, open_index, search


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = open_index(':memory:')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_citation_matches_original_lines(self):
        lines = ['zero', 'one', 'idempotent movement', 'three', 'four']
        (self.root / 'stock.md').write_text('\n'.join(lines), encoding='utf-8')
        index_documents(self.db, self.root, 3, 1)
        for hit in search(self.db, 'idempotent'):
            self.assertEqual(hit['text'], '\n'.join(lines[hit['start_line']-1:hit['end_line']]))
            self.assertEqual(len(hit['sha256']), 64)

    def test_reindex_removes_deleted_and_old_content(self):
        doc = self.root / 'a.md'
        doc.write_text('oldtoken', encoding='utf-8')
        index_documents(self.db, self.root)
        doc.unlink()
        (self.root / 'b.txt').write_text('newtoken', encoding='utf-8')
        index_documents(self.db, self.root)
        self.assertEqual(search(self.db, 'oldtoken'), [])
        self.assertEqual(search(self.db, 'newtoken')[0]['source'], 'b.txt')

    def test_invalid_utf8_preserves_previous_index(self):
        (self.root / 'ok.md').write_text('retained', encoding='utf-8')
        index_documents(self.db, self.root)
        (self.root / 'bad.md').write_bytes(b'\xff')
        with self.assertRaises(UnicodeError):
            index_documents(self.db, self.root)
        self.assertEqual(len(search(self.db, 'retained')), 1)

    def test_fts_operators_are_literal(self):
        (self.root / 'a.md').write_text('ordinary words', encoding='utf-8')
        index_documents(self.db, self.root)
        self.assertEqual(search(self.db, '" OR NOT NEAR(*)'), [])
        self.assertEqual(len(search(self.db, 'ordinary"*')), 1)

    def test_empty_corpus_does_not_clear_index(self):
        doc = self.root / 'a.md'
        doc.write_text('retained', encoding='utf-8')
        index_documents(self.db, self.root)
        doc.unlink()
        with self.assertRaises(ValueError):
            index_documents(self.db, self.root)
        self.assertEqual(len(search(self.db, 'retained')), 1)

    def test_hidden_files_not_indexed(self):
        (self.root / '.hidden.md').write_text('privateword', encoding='utf-8')
        (self.root / 'a.md').write_text('publicword', encoding='utf-8')
        index_documents(self.db, self.root)
        self.assertEqual(search(self.db, 'privateword'), [])

    def test_chunk_overlap_and_parameter_validation(self):
        self.assertEqual(list(chunk_text('a\nb\nc\nd', 3, 1)), [(1, 3, 'a\nb\nc'), (3, 4, 'c\nd')])
        with self.assertRaises(ValueError):
            list(chunk_text('a', 3, 3))
        for query, limit in [('', 5), ('a', 0), ('a' * 1001, 5)]:
            with self.assertRaises(ValueError):
                search(self.db, query, limit)

    def test_sample_retrieval_evaluation(self):
        project = Path(__file__).parent
        index_documents(self.db, project / 'documents')
        result = evaluate(self.db, json.loads((project / 'cases.json').read_text()), 1)
        self.assertEqual(result['mean_recall'], 1)
        self.assertEqual(result['mean_reciprocal_rank'], 1)

    def test_no_match_scores_zero(self):
        result = evaluate(self.db, [{'query': 'absent', 'expected_sources': ['a.md']}])
        self.assertEqual(result['mean_recall'], 0)
        self.assertEqual(result['mean_reciprocal_rank'], 0)

    def test_oversized_file_and_symlink_rejected(self):
        doc = self.root / 'big.md'
        doc.write_bytes(b'x' * 1_000_001)
        with self.assertRaises(ValueError):
            index_documents(self.db, self.root)
        doc.write_text('normal', encoding='utf-8')
        link = self.root / 'link.md'
        link.symlink_to(doc)
        with self.assertRaises(ValueError):
            index_documents(self.db, self.root)

    def test_missing_index_cli_does_not_create_database(self):
        missing = self.root / 'missing.db'
        run = subprocess.run([sys.executable, str(Path(__file__).with_name('search.py')),
            '--db', str(missing), 'search', 'example'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(missing.exists())


if __name__ == '__main__':
    unittest.main()
