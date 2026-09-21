# AI Response Contract Lab

Validate structured model output before application code consumes it. Includes a support-ticket classification contract and a local Ollama adapter using `/api/chat`.

## Run from the repository root

```sh
python -m pip install -r portfolio/ai-response-contract-lab/requirements.txt
python portfolio/ai-response-contract-lab/contracts.py --schema portfolio/ai-response-contract-lab/schema.json --response portfolio/ai-response-contract-lab/response.json
python -m unittest discover -s portfolio/ai-response-contract-lab -v
```

The bundled response is synthetic. This command performs real JSON parsing and schema validation, without model inference. Invalid output exits with status 1.

For live inference, separately install and start Ollama, pull a model supporting structured outputs, and substitute its installed name:

```sh
python portfolio/ai-response-contract-lab/contracts.py --schema portfolio/ai-response-contract-lab/schema.json --model YOUR_INSTALLED_MODEL --prompt 'Classify this ticket: I cannot reset my password. Return category, summary, and priority (1 to 3).'
```

## Design and verification

- Draft 2020-12 JSON Schema, required properties, enum/range checks, and format checks.
- Rejects duplicate keys, non-finite JSON numbers, fenced prose, and trailing content.
- Self-contained trusted schemas only: references are rejected, preventing remote schema downloads.
- Loopback-only Ollama URL, disabled proxies/redirects, 30-second socket timeout, and 1 MiB request/response limit.
- Tests exercise a real local HTTP server and reject an invalid model response.

This validates structure, not factual accuracy or prompt-injection safety. The timeout is a socket timeout, not a hard total generation deadline. CLI files and schemas are trusted local inputs; this is not an internet-facing service. Real model generation has not been verified in CI, which uses a controlled HTTP fixture. Malformed output is rejected rather than silently repaired.

Inspired by [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs), reviewed September 21, 2026.
