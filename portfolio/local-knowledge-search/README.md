# Local Knowledge Search

An offline retrieval engine for a folder of Markdown and text documents. It builds a SQLite FTS5 index, ranks matching chunks with BM25, and returns original passages with file/line citations and SHA-256 hashes.

This implements the retrieval stage used in many retrieval-augmented generation (RAG) systems. It does not generate answers, call an LLM, use embeddings, or send documents to a service.

## Run in two minutes

Requires Python 3.11+ with SQLite FTS5 support. No pip packages or API keys are required. From this directory:

```sh
python search.py index documents
python search.py search "deployment readiness rollback" --limit 3
python search.py evaluate cases.json --limit 1
python -m unittest discover -v
```

Use `python search.py --db another.db index documents` for a separate corpus. The default index is `knowledge.db`. Each index command replaces that database's complete corpus snapshot; use a separate database for each collection.

The first search should return `deployment.md`, its line range, passage text, document hash, and BM25 rank. Lower BM25 values rank first. The three synthetic evaluation cases each retrieve their expected document at rank 1; this tiny fixture is a reproducibility check, not a general retrieval benchmark.

## Architecture and decisions

| Stage | Behavior |
| --- | --- |
| Read | Recursively load nonhidden `.md`/`.txt` files as UTF-8; reject symlink files and oversized corpora |
| Chunk | Default 24 lines with 4 lines of overlap; preserve original line positions |
| Index | Replace all chunks in one transaction, removing deleted files and outdated content |
| Search | Literal query tokens joined by OR; parameterized FTS5 query; BM25 ranking |
| Cite | Return source-relative path, original line range, full passage, and hash of indexed bytes |
| Evaluate | Mean document recall and reciprocal rank for expected source files |

Search limits apply to chunks. Evaluation deduplicates retrieved sources in rank order before scoring; multiple chunks from a source can reduce the number of distinct documents evaluated. Negative or zero results are valid and are returned without an invented answer.

Changes to source files become visible after reindexing. Citations describe the indexed snapshot; compare the SHA-256 digest before treating a modified source file as identical. Invalid UTF-8, an empty corpus, or a read failure preserves the previous index. Hidden files and unsupported formats are skipped. Each file is limited to 1 MB and each corpus to 20 MB; the implementation buffers a small corpus in memory.

## Quality checks and limits

Tests cover exact source citations, overlapping chunks, deletion/replacement, rollback after bad input, literal FTS operator handling, hidden files, invalid parameters, and retrieval scores.

This is lexical retrieval: synonyms and paraphrases without shared terms can be missed. It has no PDF parsing, semantic search, reranking, authentication, or web server. Retrieved text remains untrusted input if a future extension passes it to a language model.

## Why this project

Retrieval quality is a practical part of building useful AI applications. This small baseline makes ranking and citation behavior inspectable before adding a model or vector database. See [Anthropic's contextual retrieval discussion](https://www.anthropic.com/engineering/contextual-retrieval) for the broader engineering context; this project does not implement that article's contextual embedding technique.

All bundled documents are synthetic. No license has been selected; the parent repository's licensing status applies.
