import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from evaluate import compare, evaluate, render_html, read_jsonl


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.suite = [{'id': 'one', 'expected_answer': 'Correct answer', 'required_tools': ['read'],
                       'forbidden_tools': ['send'], 'max_latency_ms': 100, 'max_cost_usd': 0.01}]
        self.runs = [{'id': 'one', 'answer': 'correct  ANSWER', 'tools': ['read'], 'latency_ms': 100, 'cost_usd': 0.01}]

    def test_normalization_and_inclusive_budgets(self):
        self.assertEqual(evaluate(self.suite, self.runs)['pass_rate'], 1)

    def test_missing_responses_count_as_failures(self):
        result = evaluate(self.suite, [])
        self.assertEqual(result['missing'], 1)
        self.assertEqual(result['pass_rate'], 0)
        self.assertIsNone(result['mean_latency_ms'])

    def test_forbidden_tool_and_budget_overrun(self):
        self.runs[0].update(tools=['read', 'send'], latency_ms=101)
        case = evaluate(self.suite, self.runs)['results'][0]
        self.assertFalse(case['checks']['forbidden_tool:send'])
        self.assertFalse(case['checks']['max_latency_ms'])

    def test_invalid_numeric_values_rejected(self):
        for value in [True, -1, math.nan, math.inf, '100', 10**400]:
            self.runs[0]['latency_ms'] = value
            with self.assertRaises(ValueError):
                evaluate(self.suite, self.runs)

    def test_duplicate_unknown_and_typo_ids_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(self.suite, self.runs * 2)
        self.runs[0]['id'] = 'unknown'
        with self.assertRaises(ValueError):
            evaluate(self.suite, self.runs)
        self.suite[0]['max_latncy_ms'] = 10
        with self.assertRaises(ValueError):
            evaluate(self.suite, [])

    def test_empty_or_contradictory_suite_rejected(self):
        for suite in [[], [{'id': 'one'}], [{'id': 'one', 'required_tools': ['read'], 'forbidden_tools': ['read']}]]:
            with self.assertRaises(ValueError):
                evaluate(suite, [])

    def test_regression_detected_even_when_total_passes_equal(self):
        suite = [{'id': 'a', 'expected_answer': 'yes'}, {'id': 'b', 'expected_answer': 'yes'}]
        first = [dict(self.runs[0], id='a', answer='yes'), dict(self.runs[0], id='b', answer='no')]
        second = [dict(self.runs[0], id='a', answer='no'), dict(self.runs[0], id='b', answer='yes')]
        result = compare(evaluate(suite, second), evaluate(suite, first))
        self.assertEqual(result['pass_rate_delta'], 0)
        self.assertEqual(result['regressed_cases'], ['a'])
        self.assertEqual(result['improved_cases'], ['b'])

    def test_html_escapes_recorded_content(self):
        self.runs[0]['answer'] = '<script>alert(1)</script>'
        output = render_html(evaluate(self.suite, self.runs))
        self.assertNotIn('<script>', output)
        self.assertIn('&lt;script&gt;', output)

    def test_cli_gate_and_reports(self):
        project = Path(__file__).parent
        with tempfile.TemporaryDirectory() as temp:
            base = [sys.executable, str(project / 'evaluate.py'), str(project / 'examples/suite.jsonl')]
            success = subprocess.run(base + [str(project / 'examples/candidate.jsonl'), '--baseline',
                str(project / 'examples/baseline.jsonl'), '--output', temp], capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertTrue((Path(temp) / 'report.html').is_file())
            failure = subprocess.run(base + [str(project / 'examples/baseline.jsonl')], capture_output=True, text=True)
            self.assertEqual(failure.returncode, 1)
            invalid = subprocess.run(base + [str(project / 'examples/candidate.jsonl'), '--min-pass-rate', 'nan'], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)

    def test_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'runs.jsonl'
            path.write_text('{"id":"one","answer":"wrong","answer":"correct"}\n')
            with self.assertRaises(ValueError):
                read_jsonl(path)


if __name__ == '__main__':
    unittest.main()
