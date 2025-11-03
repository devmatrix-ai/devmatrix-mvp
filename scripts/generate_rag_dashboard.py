#!/usr/bin/env python
"""
Generate a simple RAG dashboard markdown with collection stats and recent metrics.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from src.rag import create_embedding_model
from src.rag.vector_store import VectorStore
from src.observability import get_logger

logger = get_logger("rag.dashboard")

COLLECTIONS = [
    ("devmatrix_curated", "Curated Patterns"),
    ("devmatrix_project_code", "Project Code"),
    ("devmatrix_standards", "Standards & Guidelines"),
]


def main():
    embedding_model = create_embedding_model()
    lines = []
    lines.append("# RAG Dashboard")
    lines.append("")
    lines.append(f"Generated: {datetime.utcnow().isoformat()} UTC")
    lines.append("")

    total = 0
    lines.append("## Collections")
    lines.append("")
    lines.append("| Collection | Description | Count | Embedding | Dim |")
    lines.append("|-----------:|------------|------:|----------|----:|")

    for name, desc in COLLECTIONS:
        try:
            vs = VectorStore(embedding_model, collection_name=name)
            count = vs.collection.count()
            total += count
            lines.append(f"| `{name}` | {desc} | {count} | {embedding_model.model_name} | {embedding_model.get_dimension()} |")
        except Exception as e:
            lines.append(f"| `{name}` | {desc} | ERR | - | - |")
            logger.error(f"Failed stats for {name}: {e}")

    lines.append("")
    lines.append(f"**Total examples across collections:** {total}")

    out = Path("DOCS/rag/dashboard.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Dashboard written to {out} (total={total})")

if __name__ == "__main__":
    main()
