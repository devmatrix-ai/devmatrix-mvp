# Adding Examples to RAG

## Programmatic (preferred)
- Use scripts: `seed_enhanced_patterns.py`, `seed_project_standards.py`, `seed_official_docs.py`, `seed_github_repos.py`.
- Use `VectorStore.add_batch(codes, metadatas, example_ids)`.

## Manual Curation
1. Create a small code snippet (<= ~2000 chars recommended for embedding pass).
2. Provide rich metadata: `source`, `category`, `language`, `file`, `tags`.
3. Index via a short script calling `VectorStore.add_example`.

## Collections
- `devmatrix_curated`: curated patterns
- `devmatrix_project_code`: project + GitHub code
- `devmatrix_standards`: standards and guidelines

## Verification
- Run `scripts/verify_rag_quality.py` and review `DOCS/rag/dashboard.md`.
