import tempfile
import unittest
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from inventory import connect, add_product, move, report


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / 'test.db')
        self.db = connect(self.path)
        add_product(self.db, 'USB', 'USB hub', 2)

    def tearDown(self):
        self.db.close()
        self.directory.cleanup()

    def test_retry_is_idempotent(self):
        self.assertTrue(move(self.db, 'USB', 10, 'receipt-1'))
        self.assertFalse(move(self.db, 'USB', 10, 'receipt-1'))
        self.assertEqual(report(self.db)[0]['stock'], 10)

    def test_insufficient_stock_rolls_back(self):
        move(self.db, 'USB', 2, 'receipt')
        with self.assertRaises(ValueError):
            move(self.db, 'USB', -3, 'sale')
        self.assertEqual(report(self.db)[0]['stock'], 2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM movements').fetchone()[0], 1)

    def test_conflicting_request_rejected(self):
        move(self.db, 'USB', 5, 'same')
        with self.assertRaises(ValueError):
            move(self.db, 'USB', 6, 'same')
        self.assertEqual(report(self.db)[0]['stock'], 5)

    def test_low_stock_boundary(self):
        move(self.db, 'USB', 2, 'receipt')
        self.assertEqual(len(report(self.db, True)), 1)
        move(self.db, 'USB', 1, 'receipt-2')
        self.assertEqual(report(self.db, True), [])

    def test_concurrent_sales_cannot_oversell(self):
        move(self.db, 'USB', 1, 'receipt')
        def sell(index):
            db = connect(self.path)
            try:
                return move(db, 'USB', -1, f'sale-{index}')
            except ValueError:
                return False
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(sell, range(2))), 1)
        self.assertEqual(report(self.db)[0]['stock'], 0)

    def test_invalid_and_unknown_movements(self):
        for sku, delta, key in [('USB', 0, 'x'), ('USB', 1, ''), ('NO', 1, 'x')]:
            with self.assertRaises(ValueError):
                move(self.db, sku, delta, key)

    def test_stock_overflow_preserves_integer_balance(self):
        move(self.db, 'USB', 2**63 - 1, 'maximum')
        with self.assertRaises(ValueError):
            move(self.db, 'USB', 1, 'overflow')
        self.assertEqual(report(self.db)[0]['stock'], 2**63 - 1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM movements').fetchone()[0], 1)

    def test_out_of_range_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            move(self.db, 'USB', 2**63, 'too-large')

    def test_sku_whitespace_is_consistent(self):
        move(self.db, ' USB ', 1, 'receipt')
        self.assertFalse(move(self.db, 'USB', 1, 'receipt'))
        self.assertEqual(report(self.db)[0]['stock'], 1)

    def test_reorder_point_must_be_integer(self):
        for value in [1.5, True, 2**63]:
            with self.assertRaises(ValueError):
                add_product(self.db, 'NEW', 'New product', value)

    def test_invalid_database_path_has_clean_cli_error(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('inventory.py')),
            '--db', str(Path(self.directory.name) / 'missing' / 'test.db'), 'list'],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
