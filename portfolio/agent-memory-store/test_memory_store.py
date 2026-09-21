import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from memory_store import MemoryStore

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'memory.db'
        self.now = 100.0
        self.store = MemoryStore(self.path, clock=lambda: self.now)
    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_persistence_and_provenance(self):
        identifier = self.store.add('a', 'Python tests', 'session:1')
        other = MemoryStore(self.path, clock=lambda: self.now)
        try:
            result = other.recall('a', 'PYTHON')[0]
            self.assertEqual((result['id'], result['source']), (identifier, 'session:1'))
        finally:
            other.close()

    def test_namespace_isolation_and_delete(self):
        identifier = self.store.add('a', 'Python', 'test')
        self.assertEqual(self.store.recall('b', 'Python'), [])
        self.assertFalse(self.store.delete('b', identifier))
        self.assertTrue(self.store.delete('a', identifier))
        self.assertEqual(self.store.recall('a', 'Python'), [])

    def test_expiration_boundary_and_purge(self):
        self.store.add('a', 'Python', 'test', ttl=5)
        self.store.add('a', 'Python permanent', 'test')
        self.assertEqual(len(self.store.recall('a', 'Python')), 2)
        self.now = 105
        self.assertEqual(len(self.store.recall('a', 'Python')), 1)
        self.assertEqual(self.store.purge_expired(), 1)
        self.assertEqual(self.store.purge_expired(), 0)

    def test_ranking_and_limit(self):
        self.store.add('a', 'Python only', 'test')
        expected = self.store.add('a', 'Python tests', 'test')
        result = self.store.recall('a', 'python tests', 1)
        self.assertEqual(result[0]['id'], expected)
        self.assertEqual(result[0]['score'], 1)
        self.assertEqual(self.store.recall('a', 'unmatched'), [])

    def test_invalid_inputs_leave_no_rows(self):
        for ttl in (0, -1, float('nan'), float('inf'), True, '1'):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                self.store.add('a', 'Python', 'test', ttl)
        for namespace, content, source in (('', 'Python', 'test'), ('a', '', 'test'), ('a', 'Python', '')):
            with self.assertRaises(ValueError):
                self.store.add(namespace, content, source)
        self.assertEqual(self.store.recall('a', 'Python'), [])

    def test_query_validation_and_literal_sql(self):
        self.store.add('a', 'Python', 'test')
        self.assertEqual(self.store.recall("a' OR 1=1--", 'Python'), [])
        for limit in (0, 101, True, 1.5):
            with self.assertRaises(ValueError):
                self.store.recall('a', 'Python', limit)

    def test_concurrent_writers(self):
        def write(index):
            connection = MemoryStore(self.path)
            try:
                return connection.add('a', f'Python memory {index}', 'test')
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            ids = list(pool.map(write, range(20)))
        self.assertEqual(len(set(ids)), 20)
        self.assertEqual(len(self.store.recall('a', 'Python', 100)), 20)

if __name__ == '__main__':
    unittest.main()
