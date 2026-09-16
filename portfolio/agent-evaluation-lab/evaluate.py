"""Grade recorded AI responses with deterministic checks and regression gates."""
import argparse
import html
import json
import math
from pathlib import Path

CASE_KEYS = {'id', 'expected_answer', 'must_include', 'required_tools', 'forbidden_tools',
             'max_latency_ms', 'max_cost_usd'}
RUN_KEYS = {'id', 'answer', 'tools', 'latency_ms', 'cost_usd'}


def number(value, name):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{name} must be a finite nonnegative number')
    return value


def strings(value, name):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f'{name} must be an array of nonempty strings')
    return value


def read_jsonl(path):
    records = []
    with Path(path).open(encoding='utf-8') as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as exc:
                raise ValueError(f'{path}:{line_number}: invalid JSON') from exc
            if not isinstance(record, dict):
                raise ValueError(f'{path}:{line_number}: each record must be an object')
            records.append(record)
    return records


def validate(records, kind):
    indexed = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f'{kind}: each record must be an object')
        identifier = record.get('id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in indexed:
            raise ValueError(f'{kind}: IDs must be nonempty strings without duplicates')
        allowed = CASE_KEYS if kind == 'suite' else RUN_KEYS
        if set(record) - allowed:
            raise ValueError(f'{identifier}: unknown fields: {sorted(set(record) - allowed)}')
        if kind == 'suite':
            if 'expected_answer' in record and not isinstance(record['expected_answer'], str):
                raise ValueError(f'{identifier}: expected_answer must be text')
            for key in ('must_include', 'required_tools', 'forbidden_tools'):
                strings(record.get(key, []), key)
            for key in ('max_latency_ms', 'max_cost_usd'):
                if key in record:
                    number(record[key], key)
            if set(record.get('required_tools', [])) & set(record.get('forbidden_tools', [])):
                raise ValueError(f'{identifier}: a tool cannot be both required and forbidden')
            if not ('expected_answer' in record or any(record.get(k) for k in
                    ('must_include', 'required_tools', 'forbidden_tools')) or
                    any(k in record for k in ('max_latency_ms', 'max_cost_usd'))):
                raise ValueError(f'{identifier}: at least one check is required')
        else:
            if set(record) != RUN_KEYS or not isinstance(record['answer'], str):
                raise ValueError(f'{identifier}: run requires id, answer, tools, latency_ms, cost_usd')
            strings(record['tools'], 'tools')
            number(record['latency_ms'], 'latency_ms')
            number(record['cost_usd'], 'cost_usd')
        indexed[identifier] = record
    if kind == 'suite' and not indexed:
        raise ValueError('Evaluation suite cannot be empty')
    return indexed


def normalize(text):
    return ' '.join(text.casefold().split())


def evaluate(suite, runs):
    cases, recorded = validate(suite, 'suite'), validate(runs, 'runs')
    if set(recorded) - set(cases):
        raise ValueError('Run contains unknown case IDs: ' + ', '.join(sorted(set(recorded) - set(cases))))
    results = []
    for identifier, case in cases.items():
        run = recorded.get(identifier)
        if run is None:
            results.append({'id': identifier, 'passed': False, 'checks': {'response_present': False}})
            continue
        checks = {'response_present': True}
        if 'expected_answer' in case:
            checks['exact_answer'] = normalize(run['answer']) == normalize(case['expected_answer'])
        for term in case.get('must_include', []):
            checks['contains:' + term] = normalize(term) in normalize(run['answer'])
        for tool in case.get('required_tools', []):
            checks['required_tool:' + tool] = tool in run['tools']
        for tool in case.get('forbidden_tools', []):
            checks['forbidden_tool:' + tool] = tool not in run['tools']
        for metric, maximum in (('latency_ms', 'max_latency_ms'), ('cost_usd', 'max_cost_usd')):
            if maximum in case:
                checks[maximum] = run[metric] <= case[maximum]
        results.append({'id': identifier, 'passed': all(checks.values()), 'checks': checks,
                        'answer': run['answer'], 'latency_ms': run['latency_ms'], 'cost_usd': run['cost_usd']})
    passed = sum(row['passed'] for row in results)
    total_latency = number(sum(x['latency_ms'] for x in recorded.values()), 'total latency')
    total_cost = number(sum(x['cost_usd'] for x in recorded.values()), 'total cost')
    return {'total': len(cases), 'passed': passed, 'failed': len(cases) - passed,
            'missing': len(cases) - len(recorded), 'pass_rate': passed / len(cases),
            'mean_latency_ms': total_latency / len(recorded) if recorded else None,
            'total_cost_usd': total_cost, 'results': results}


def compare(candidate, baseline):
    before = {row['id']: row['passed'] for row in baseline['results']}
    return {'pass_rate_delta': candidate['pass_rate'] - baseline['pass_rate'],
            'regressed_cases': [row['id'] for row in candidate['results'] if before[row['id']] and not row['passed']],
            'improved_cases': [row['id'] for row in candidate['results'] if not before[row['id']] and row['passed']]}


def render_html(report):
    escape = html.escape
    rows = []
    for case in report['results']:
        failures = ', '.join(key for key, passed in case['checks'].items() if not passed) or 'All checks passed'
        status = 'Pass' if case['passed'] else 'Fail'
        rows.append(f'<tr><th scope="row">{escape(case["id"])}</th><td>{status}</td>'
                    f'<td>{escape(failures)}</td><td>{escape(case.get("answer", "Missing response"))}</td></tr>')
    comparison = ''
    if 'comparison' in report:
        comparison = '<h2>Baseline comparison</h2><pre>' + escape(json.dumps(report['comparison'], indent=2)) + '</pre>'
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Evaluation Report</title><style>
body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f2f5fa;color:#18263b}
main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:36px;line-height:1.2}
.eyebrow{color:#375886;text-transform:uppercase;letter-spacing:.12em;font-size:12px}
.summary{background:#fff;border-left:4px solid #2563eb;padding:20px;margin:24px 0}
table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:14px;border-bottom:1px solid #dbe3ee;vertical-align:top;overflow-wrap:anywhere}
thead{background:#e3eaf5}pre{white-space:pre-wrap}footer{margin-top:24px;color:#526277}.table-wrap{overflow:auto}
</style><main><p class="eyebrow">Engineering quality / recorded runs</p>
<h1>Agent Evaluation Report</h1>''' + (
        f'<div class="summary"><strong>{report["passed"]}/{report["total"]} cases passed '
        f'({report["pass_rate"]:.0%})</strong><br>{report["missing"]} missing responses · '
        f'Reported cost: ${report["total_cost_usd"]:.4f}</div>'
        '<div class="table-wrap"><table><thead><tr><th>Case</th><th>Status</th><th>Checks</th><th>Recorded answer</th></tr></thead>'
        '<tbody>' + ''.join(rows) + '</tbody></table></div>' + comparison +
        '<footer>Deterministic checks on supplied records. Tool traces, timings, and costs are supplied by the caller; '
        'this report does not independently verify them or judge semantic correctness.</footer></main></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite', type=Path)
    parser.add_argument('runs', type=Path)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--min-pass-rate', type=float, default=1.0)
    args = parser.parse_args()
    try:
        if not math.isfinite(args.min_pass_rate) or not 0 <= args.min_pass_rate <= 1:
            raise ValueError('Minimum pass rate must be between 0 and 1')
        suite = read_jsonl(args.suite)
        report = evaluate(suite, read_jsonl(args.runs))
        if args.baseline:
            baseline = evaluate(suite, read_jsonl(args.baseline))
            report['comparison'] = compare(report, baseline)
        gate = report['pass_rate'] >= args.min_pass_rate and not report.get('comparison', {}).get('regressed_cases')
        report['gate_passed'] = bool(gate)
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            (args.output / 'report.html').write_text(render_html(report), encoding='utf-8')
        print(json.dumps(report, indent=2))
        return 0 if gate else 1
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Error: {exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
