# Embedding Model Guide

## Model
- Name: `jinaai/jina-embeddings-v2-base-code`
- Dimension: 768
- Device: GPU by default (`EMBEDDING_DEVICE=cuda`), fallback to CPU for ingestion if needed

## Configuration
```bash
grep EMBEDDING_MODEL src/config/constants.py
```

## Reindexing Steps
- Clear collections and re-index with the new model to avoid dimension mismatch.
- Use orchestrator with `--clear` or run individual scripts.

## Benchmarks
- See `DOCS/rag/embedding_benchmark.md` for metrics and comparisons.

## Tips
- For large ingestion jobs: `EMBEDDING_DEVICE=cpu python scripts/seed_github_repos.py`
- Use chunking and truncation to prevent OOM.
