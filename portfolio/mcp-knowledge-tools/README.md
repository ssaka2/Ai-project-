# MCP Knowledge Tools

A working read-only Model Context Protocol server for a small, explicitly selected folder of Markdown notes. Uses the official Python MCP SDK 2.2.0, with tool discovery, structured tool results, a catalog resource, and stdio transport.

## Run

Python 3.11+:

```sh
python -m venv .venv
# Linux/macOS; on Windows use .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -r portfolio/mcp-knowledge-tools/requirements.txt
python portfolio/mcp-knowledge-tools/demo.py
python -m unittest discover -s portfolio/mcp-knowledge-tools -v
python portfolio/mcp-knowledge-tools/knowledge_server.py
```

The last command waits for an MCP client on stdin; it is not a web server. In your MCP client's stdio configuration, set `command` to the absolute path of the virtual environment's Python, `args` to the absolute path of `knowledge_server.py`, and optionally `env.KNOWLEDGE_ROOT` to your selected notes folder. Client configuration formats vary. The bundled demo uses an in-memory MCP client; the tests also launch a real stdio subprocess.

## Tools

- `list_documents`: document IDs and line counts.
- `search_documents(query, limit=5)`: literal word overlap ranking with source line citations.
- `read_document(document_id, start_line=1, line_count=30)`: read a catalog entry, capped at 50 lines.
- Resource `knowledge://catalog`: the same document catalog as JSON.

Documents are loaded once at startup, so reads and citations refer to the same snapshot. Restart to reload. Only visible top-level `.md` files are included; symlinks and arbitrary document paths are rejected. Limits: 100 files, 100 KB per file, 2 MB total. Use a trusted folder that is not being modified during startup. Choosing a folder authorizes its contents to be available to your connected MCP client.

## Design and limits

This is lexical retrieval, not embeddings or model inference. It has no write tools, shell execution, network listener, or paid-service requirement. Document contents are untrusted reference material; model prompt-injection resistance is not guaranteed. Synthetic notes are included. Tests cover discovery, source citations, line bounds, traversal rejection, snapshot stability, resources, file size limits, and stdio calls.

Reference: [official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
