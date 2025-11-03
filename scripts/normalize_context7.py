import json, os, uuid
from pathlib import Path
IN_DIR = Path("./data/context7/raw")
OUT_DIR = Path("./data/context7/normalized"); OUT_DIR.mkdir(parents=True, exist_ok=True)
count_in, count_out = 0, 0
for fp in IN_DIR.glob("*.jsonl"):
    with fp.open() as f, (OUT_DIR / (fp.stem + ".jsonl")).open("w") as out:
        for line in f:
            count_in += 1
            try:
                o = json.loads(line)
            except Exception:
                continue
            code = o.get("content", "")
            meta = o.get("metadata", {})
            normalized = {
                "id": str(uuid.uuid4()),
                "code": code,
                "metadata": {
                    "language": meta.get("language") or "python",
                    "framework": meta.get("framework") or "",
                    "tags": meta.get("tags") if isinstance(meta.get("tags"), list) else [],
                    "approved": bool(meta.get("approved", True)),
                    "task_type": meta.get("task_type") or "",
                    "pattern": meta.get("pattern") or "",
                    "source": meta.get("source") or "context7",
                }
            }
            out.write(json.dumps(normalized) + "\n"); count_out += 1
print(f"normalized_in={count_in} out={count_out}")
