# Agent Memory Store

A SQLite memory component for agent applications. Store observations with source provenance, recall relevant text within a namespace, expire temporary memories, and explicitly delete records. No API key, model, or external database is required.

## Run from the repository root

```sh
python portfolio/agent-memory-store/memory_store.py demo
python portfolio/agent-memory-store/memory_store.py --db /tmp/agent-memory.sqlite3 add assistant 'Prefer Python examples with unit tests' --source synthetic-session:1 --ttl 3600
python portfolio/agent-memory-store/memory_store.py --db /tmp/agent-memory.sqlite3 recall assistant 'Python tests'
python portfolio/agent-memory-store/memory_store.py --db /tmp/agent-memory.sqlite3 purge
python -m unittest discover -s portfolio/agent-memory-store -v
```

Use a writable local path instead of `/tmp/agent-memory.sqlite3` on Windows. `add` prints an ID. Delete with `memory_store.py --db PATH delete assistant ID`. The demo uses a disposable in-memory database and synthetic examples; other commands persist across restarts.

## Python integration

```python
from memory_store import MemoryStore
store = MemoryStore('agent.sqlite3')
try:
    store.add('research-agent', 'Verify sources before writing summaries.', 'session:42')
    context = store.recall('research-agent', 'sources summaries')
    print(context)  # Supply content and source provenance as agent context.
finally:
    store.close()
```

Recall scores the fraction of distinct query words appearing in each memory. Ties use creation time, then record ID. Expired records stop appearing at their exact expiration timestamp; purge physically removes them. Writes and deletion commit atomically. Concurrent workers use separate connections with SQLite writer locking and a ten-second busy timeout.

Tests cover persistence, provenance, namespace filtering, deletion, expiration boundaries, invalid input, ranking, parameterized SQL, and concurrent writers.

This is deterministic storage and lexical retrieval for agents, not a language model or vector search. Recall scans the chosen namespace and suits modest local datasets. Namespaces are filters, not authentication. Data is unencrypted; callers must authorize access. Expiration does not erase backups. Treat recalled text as untrusted context, not instructions.

Agent memory is an active engineering theme represented by [ECC](https://github.com/affaan-m/ECC), observed on [GitHub Trending](https://github.com/trending) September 21, 2026. This is an independent implementation; the portfolio itself is not claimed to be trending.
