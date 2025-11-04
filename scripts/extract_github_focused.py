#!/usr/bin/env python
"""
Focused GitHub Extraction - Extract from smaller repos only

Targets specific smaller repos to avoid API rate limiting:
- facebook/react (50-100 examples)
- axios/axios (30-50 examples)
- lodash/lodash (30-50 examples)
- react-hook-form/react-hook-form (20-30 examples)
- expressjs/express (continue from 50 already extracted)

Total target: 150-280 examples
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability import get_logger

logger = get_logger(__name__)

# Use PyGithub for extraction
try:
    from github import Github, Auth
except ImportError:
    logger.error("PyGithub not installed. Install with: pip install PyGithub")
    sys.exit(1)


def extract_repo_files(g: Github, repo_name: str, max_files: int = 100) -> List[Tuple[str, Dict]]:
    """Extract TypeScript/JavaScript files from a repository."""

    logger.info(f"\n🔍 Extracting from {repo_name}...")

    try:
        repo = g.get_repo(repo_name)
        logger.info(f"   Stars: {repo.stargazers_count}")

        files = []
        examined = 0

        # Get code contents
        try:
            contents = repo.get_contents("")
        except Exception as e:
            logger.error(f"   ❌ Failed to read repo: {str(e)}")
            return []

        # Recursive function to traverse directory
        def traverse(contents_list, base_path=""):
            nonlocal examined, files

            for item in contents_list:
                if examined >= max_files:
                    break

                examined += 1

                # Skip certain directories
                skip_dirs = {'node_modules', '.git', 'dist', 'build', '.next', 'coverage', 'test'}
                if any(skip in item.path for skip in skip_dirs):
                    continue

                # Get files
                if item.type == "file":
                    if item.name.endswith(('.ts', '.tsx', '.js', '.jsx')):
                        try:
                            # Read file content
                            content = item.decoded_content.decode('utf-8', errors='ignore')

                            # Filter by size (avoid tiny snippets and huge generated files)
                            lines = content.strip().split('\n')
                            if 10 <= len(lines) <= 500:
                                files.append((
                                    content,
                                    {
                                        "file": item.path,
                                        "repo": repo_name,
                                        "language": "typescript" if item.name.endswith(('.ts', '.tsx')) else "javascript",
                                        "source": "github",
                                    }
                                ))
                                logger.debug(f"   ✓ {item.path} ({len(lines)} lines)")
                        except Exception as e:
                            logger.debug(f"   ✗ {item.path}: {str(e)}")

                elif item.type == "dir":
                    try:
                        # Recursively traverse subdirectories
                        sub_contents = repo.get_contents(item.path)
                        traverse(sub_contents, item.path)
                    except Exception as e:
                        logger.debug(f"   ✗ {item.path}/: {str(e)}")

        # Start traversal
        traverse(contents)

        logger.info(f"   ✅ Extracted {len(files)} files from {repo_name}")
        return files

    except Exception as e:
        logger.error(f"   ❌ Error: {str(e)}")
        return []


def main():
    logger.info("=" * 80)
    logger.info("🚀 FOCUSED GITHUB EXTRACTION - Smaller Repos Only")
    logger.info("=" * 80)

    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        logger.error("❌ GITHUB_TOKEN environment variable not set")
        return False

    # Initialize GitHub client
    logger.info("\n🔌 Initializing GitHub client...")
    g = Github(auth=Auth.Token(token))
    logger.info("✅ GitHub client ready")

    # Smaller repos to extract from
    repos = [
        ("facebook/react", 80),           # React library
        ("axios/axios", 50),              # HTTP client
        ("lodash/lodash", 50),            # Utility library
        ("react-hook-form/react-hook-form", 40),  # Form handling (we need this!)
        ("expressjs/express", 100),       # Continue from where we left off
    ]

    logger.info(f"\n📦 Targeting {len(repos)} repositories:")
    for repo, max_f in repos:
        logger.info(f"   • {repo} (max {max_f} files)")

    # Extract from each repo
    all_extracted = []

    for repo_name, max_files in repos:
        extracted = extract_repo_files(g, repo_name, max_files)
        all_extracted.extend(extracted)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 EXTRACTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files extracted: {len(all_extracted)}")

    # Analyze
    by_lang = {}
    by_repo = {}

    for code, meta in all_extracted:
        lang = meta.get("language", "unknown")
        by_lang[lang] = by_lang.get(lang, 0) + 1

        repo = meta.get("repo", "unknown")
        by_repo[repo] = by_repo.get(repo, 0) + 1

    logger.info("\nBy language:")
    for lang, count in sorted(by_lang.items(), key=lambda x: -x[1]):
        logger.info(f"  • {lang}: {count}")

    logger.info("\nBy repository:")
    for repo, count in sorted(by_repo.items(), key=lambda x: -x[1]):
        logger.info(f"  • {repo}: {count}")

    # Save to file for later ingestion
    output_file = Path("/tmp/phase4_github_extraction.json")

    extracted_data = []
    for code, meta in all_extracted:
        extracted_data.append({
            "code": code,
            "metadata": meta
        })

    with open(output_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)

    logger.info(f"\n💾 Saved extraction to {output_file}")
    logger.info("=" * 80)
    logger.info(f"✅ Extracted {len(all_extracted)} files ready for ingestion")
    logger.info("=" * 80)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
