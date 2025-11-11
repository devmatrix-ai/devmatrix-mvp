# RAG Troubleshooting

## Common Issues

### 1) Dimension Mismatch (384 vs 768)
- Symptom: `Collection expecting embedding with dimension of 384, got 768`.
- Fix: Clear collections and re-index with the active model.

### 2) GPU OOM during ingestion
- Symptom: `CUDA out of memory`.
- Fixes:
  - Lower batch size (e.g., 32 or chunk uploads to 50).
  - Set `EMBEDDING_DEVICE=cpu` for heavy ingestion.
  - Truncate long code blocks for ingestion.

### 3) Chroma connection errors
- Symptom: Host/port NoneType or connection refused.
- Fix: Ensure `CHROMADB_HOST` and `CHROMADB_PORT` are set and service running.

### 4) Telemetry warnings from Chroma
- Symptom: `Failed to send telemetry event`.
- Status: Benign; can be ignored.

### 5) Low retrieval quality
- Fixes:
  - Ensure re-index with 768-dim model.
  - Check thresholds per collection (0.65/0.55/0.60).
  - Add more curated examples.
