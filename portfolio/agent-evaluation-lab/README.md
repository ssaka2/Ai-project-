# Agent Evaluation Lab

A deterministic quality gate for recorded AI responses. Grade expected answers, required phrases, required/forbidden tool names, latency, and cost. Compare a candidate with a baseline and generate a readable HTML report alongside machine-readable JSON.

The evaluator runs offline on supplied records. It does not call a model, execute an agent's tools, or spend API credits. Example answers, traces, timings, and costs are synthetic.

## Run in two minutes

Python 3.11+, standard library only. From this directory:

```sh
python evaluate.py examples/suite.jsonl examples/candidate.jsonl --baseline examples/baseline.jsonl --output output
python -m unittest discover -v
```

Open `output/report.html`. The candidate passes all three synthetic cases and improves two cases from the baseline. The baseline intentionally fails phrase and forbidden-tool checks, so this command exits 1:

```sh
python evaluate.py examples/suite.jsonl examples/baseline.jsonl
```

## Input contract

Both input files contain one JSON object per line. Blank lines are ignored. IDs must be unique within each file. Unknown fields, duplicate IDs, unknown result IDs, nonfinite numbers, negative metrics, and contradictory tool requirements are rejected. Missing responses fail their case and remain in the denominator.

| Suite field | Meaning |
| --- | --- |
| `id` | Required unique case identifier |
| `expected_answer` | Exact match after case folding and whitespace normalization |
| `must_include` | Array of phrases that must appear after the same normalization |
| `required_tools` | Array of tool names that must appear in the recorded trace |
| `forbidden_tools` | Array of tool names that must be absent |
| `max_latency_ms` | Inclusive per-case latency ceiling |
| `max_cost_usd` | Inclusive per-case reported cost ceiling |

At least one check is required per case. Each result requires `id`, text `answer`, a `tools` array of names, nonnegative finite `latency_ms`, and nonnegative finite `cost_usd`. Tool names are case sensitive; ordering, arguments, side effects, and tool outputs are not evaluated.

## CI behavior

All declared checks must pass for a case to pass. Default minimum pass rate is 1.0; change it with `--min-pass-rate 0.9`. With `--baseline`, any previously passing case that now fails blocks the gate even if the overall pass rate stayed the same.

| Exit code | Meaning |
| --- | --- |
| 0 | Pass-rate target met and no baseline regressions |
| 1 | Quality gate failed; JSON/HTML still available |
| 2 | Invalid input or I/O failure |

Output files are overwritten on each run. Mean latency covers supplied responses only; missing responses contribute failures but no measured latency or cost. Costs and timing are caller-provided, not independently measured. HTML escapes all record content and loads no external scripts.

## Design and limitations

Code-based grading is cheap, deterministic, and easy to debug, but substring checks can accept misleading answers and exact matches can reject reasonable paraphrases. Passing these checks is not proof of factual accuracy, safe behavior, or real-world task completion. Trace checks validate only supplied names. Production evaluation should also inspect outcomes and use calibrated human or model review where needed.

The implementation evaluates one recorded trial per case; it does not estimate reliability across repeated stochastic runs. Baseline and candidate are graded against the same current suite.

Tests cover missing results, exact matches, tool/budget violations, malformed inputs, case-level regressions, escaped HTML, and CLI/report behavior. See [Anthropic's January 2026 agent evaluation guide](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) for the broader practice motivating this project.

No license has been selected; the parent repository's licensing status applies.

Duplicate field names inside a JSON object are rejected before grading; they cannot silently replace an earlier answer or check.
