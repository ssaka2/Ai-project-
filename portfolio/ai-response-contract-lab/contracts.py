"""Validate model output before downstream code consumes it."""
import argparse
import json
import math
import urllib.request
from pathlib import Path
from jsonschema import Draft202012Validator

MAX_BYTES = 1_048_576


def strict_json(raw):
    if len(raw.encode('utf-8')) > MAX_BYTES:
        raise ValueError('JSON exceeds 1 MiB')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'duplicate key: {key}')
            result[key] = value
        return result
    def constant(value):
        raise ValueError(f'non-finite number: {value}')
    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError('non-finite JSON number')
        return parsed
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=finite_float)


def validator(schema):
    # This lab accepts self-contained schemas only: no retrieval or recursive refs.
    def walk(value):
        if isinstance(value, dict):
            if any(k in value for k in ('$ref', '$dynamicRef', '$recursiveRef')):
                raise ValueError('references are unsupported; use a self-contained schema')
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(schema)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def validate(raw, schema):
    check = validator(schema)
    value = strict_json(raw)
    check.validate(value)
    return value


def generate(prompt, schema, model, port=11434):
    """Use a local Ollama instance; validate its response independently."""
    validator(schema)
    if not isinstance(model, str) or not model.strip():
        raise ValueError('model is required')
    if not 1 <= port <= 65535:
        raise ValueError('invalid local port')
    payload = json.dumps({'model': model, 'stream': False, 'format': schema,
                          'messages': [{'role': 'user', 'content': prompt}],
                          'options': {'temperature': 0}}).encode()
    if len(payload) > MAX_BYTES:
        raise ValueError('request exceeds 1 MiB')
    request = urllib.request.Request(f'http://127.0.0.1:{port}/api/chat',
                                     data=payload, headers={'Content-Type': 'application/json'})
    # Do not send local prompts through environment-configured HTTP proxies.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    with opener.open(request, timeout=30) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('model response exceeds 1 MiB')
    envelope = strict_json(raw.decode('utf-8'))
    try:
        content = envelope['message']['content']
    except (KeyError, TypeError) as exc:
        raise ValueError('missing model message content') from exc
    if not isinstance(content, str):
        raise ValueError('model content must be a JSON string')
    return validate(content, schema)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--response', type=Path)
    group.add_argument('--prompt')
    parser.add_argument('--model', default='')
    args = parser.parse_args()
    try:
        schema = strict_json(args.schema.read_text(encoding='utf-8'))
        result = (validate(args.response.read_text(encoding='utf-8'), schema)
                  if args.response else generate(args.prompt, schema, args.model))
        print(json.dumps(result, indent=2))
    except Exception as exc:
        parser.exit(1, f'Contract rejected: {exc}\n')


if __name__ == '__main__':
    main()
