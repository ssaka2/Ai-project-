import sqlite3
import csv
import tempfile
import unittest
import subprocess
import sys
from pathlib import Path
from pipeline import FIELDS, load, report


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / 'flights.csv'

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def write(self, rows):
        self.csv.write_text(','.join(FIELDS) + '\n' + rows, encoding='utf-8')

    def test_sample_metrics_and_cancelled_denominator(self):
        load(self.db, Path(__file__).with_name('sample_flights.csv'))
        airports = {row['origin']: row for row in report(self.db)}
        self.assertEqual(airports['ORD']['on_time_pct'], 50)
        self.assertEqual(airports['ORD']['mean_delay_minutes'], 15)
        self.assertEqual(airports['ORD']['cancellation_pct'], 33.33)
        self.assertIsNone(airports['SEA']['on_time_pct'])

    def test_rerun_and_correction(self):
        self.write('A,2026-09-01,ORD,JFK,20,0\n')
        load(self.db, self.csv)
        load(self.db, self.csv)
        self.write('A,2026-09-01,ORD,JFK,2,0\n')
        load(self.db, self.csv)
        self.assertEqual(report(self.db)[0]['total_flights'], 1)
        self.assertEqual(report(self.db)[0]['mean_delay_minutes'], 2)

    def test_invalid_rows_are_quarantined(self):
        self.write('A,2026-09-01,ORD,JFK,14,0\n'
                   'B,2026-02-30,ORD,JFK,1,0\n'
                   'C,2026-09-01,ORD,ORD,1,0\n'
                   'D,2026-09-01,ORD,JFK,1,2\n'
                   'E,2026-09-01,ORD,JFK,9999,0\n'
                   'A,2026-09-01,ORD,JFK,20,0\n')
        quality = load(self.db, self.csv)
        self.assertEqual(quality['accepted'], 1)
        self.assertEqual(len(quality['rejected']), 5)
        self.assertEqual(report(self.db)[0]['on_time_pct'], 100)

    def test_exact_on_time_boundary(self):
        self.write('A,2026-09-01,ORD,JFK,15,0\n')
        load(self.db, self.csv)
        self.assertEqual(report(self.db)[0]['on_time_pct'], 0)

    def test_bad_header_preserves_existing_data(self):
        self.write('A,2026-09-01,ORD,JFK,1,0\n')
        load(self.db, self.csv)
        self.csv.write_text('wrong,header\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            load(self.db, self.csv)
        self.assertEqual(report(self.db)[0]['total_flights'], 1)

    def test_invalid_database_path_has_clean_cli_error(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('pipeline.py')),
            str(self.csv), '--db', str(Path(self.tmp.name) / 'missing' / 'test.db')],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Error:', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_malformed_csv_preserves_existing_data(self):
        self.write('A,2026-09-01,ORD,JFK,1,0\n')
        load(self.db, self.csv)
        self.write('B,2026-09-01,ORD,JFK,1,0\n"unterminated')
        with self.assertRaises(csv.Error):
            load(self.db, self.csv)
        self.assertEqual(report(self.db)[0]['total_flights'], 1)

    def test_rejected_line_after_multiline_record_is_physical_line(self):
        self.write('"A\n1",2026-09-01,ORD,JFK,1,0\nB,invalid,ORD,JFK,1,0\n')
        quality = load(self.db, self.csv)
        self.assertEqual(quality['rejected'][0]['line'], 4)


if __name__ == '__main__':
    unittest.main()
