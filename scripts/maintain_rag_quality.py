#!/usr/bin/env python
"""
Monthly RAG quality maintenance script.

Functions:
- Run verification suite and write a short summary
- Regenerate dashboard
- Optionally warm embedding cache
"""

import sys
from pathlib import Path
import subprocess
from datetime import datetime


def run(cmd: list[str]) -> int:
    print(f"\n$ {' '.join(cmd)}")
    proc = subprocess.run(cmd)
    return proc.returncode


def main():
    root = Path(__file__).parent.parent
    docs = root / "DOCS" / "rag"
    docs.mkdir(parents=True, exist_ok=True)

    print("\n==============================")
    print("RAG QUALITY MAINTENANCE")
    print("==============================")

    # 1) Verification suite
    ret = run([sys.executable, str(root / "scripts" / "verify_rag_quality.py"), "--detailed", "--top-k", "3", "--min-similarity", "0.6"])
    if ret != 0:
        print("Verification returned non-zero exit code (continuing)")

    # 2) Dashboard
    run([sys.executable, str(root / "scripts" / "generate_rag_dashboard.py")])

    # 3) Summary file
    (docs / "maintenance_log.md").write_text(
        f"""# RAG Maintenance Log\n\n- Timestamp: {datetime.utcnow().isoformat()} UTC\n- Verification exit code: {ret}\n- Dashboard regenerated: yes\n""",
        encoding="utf-8",
    )
    print(f"\n✓ Maintenance summary written to {docs / 'maintenance_log.md'}")


if __name__ == "__main__":
    sys.exit(main())


