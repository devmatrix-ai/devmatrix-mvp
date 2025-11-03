#!/usr/bin/env python3
"""
Check that frontend bundle size is within limits.
Part of DevMatrix Constitution compliance.
"""

import sys
import json
from pathlib import Path
import argparse

def get_bundle_size(dist_dir: Path) -> int:
    """Get total gzipped bundle size in KB."""
    total_size = 0
    
    for file in dist_dir.rglob('*.js'):
        if file.name.endswith('.gz'):
            total_size += file.stat().st_size
        else:
            # Estimate gzip size (roughly 30% of original)
            total_size += file.stat().st_size * 0.3
    
    return int(total_size / 1024)  # Convert to KB

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-size', type=int, default=300, help='Max bundle size in KB')
    args = parser.parse_args()
    
    dist_dir = Path('src/ui/dist')
    if not dist_dir.exists():
        print("ERROR: dist/ not found. Run 'npm run build' first.", file=sys.stderr)
        sys.exit(1)
    
    bundle_size = get_bundle_size(dist_dir)
    
    print(f"Bundle size: {bundle_size}KB (max: {args.max_size}KB)")
    
    if bundle_size > args.max_size:
        print(f"❌ Bundle size exceeds limit by {bundle_size - args.max_size}KB")
        sys.exit(1)
    else:
        print(f"✅ Bundle size within limits")
        sys.exit(0)

if __name__ == '__main__':
    main()

