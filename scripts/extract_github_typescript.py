#!/usr/bin/env python
"""
GitHub TypeScript/JavaScript Repository Extractor for RAG

Extracts code examples from popular GitHub repositories for JavaScript/TypeScript.
Focuses on:
- Express.js repositories (servers, middleware, API patterns)
- React repositories (components, hooks, state management)
- TypeScript repositories (type patterns, utilities)
- Node.js repositories (CLI, utilities, backend patterns)

Usage:
    python scripts/extract_github_typescript.py --language typescript
    python scripts/extract_github_typescript.py --min-stars 1000
    python scripts/extract_github_typescript.py --framework express
"""

import sys
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.observability import get_logger

logger = get_logger(__name__)


# ============================================================
# POPULAR JAVASCRIPT/TYPESCRIPT REPOSITORIES
# ============================================================

POPULAR_REPOS: Dict[str, Dict[str, Any]] = {
    # Express.js ecosystem
    "express-js/express": {
        "framework": "express",
        "language": "javascript",
        "category": "web_framework",
        "pattern_types": ["server_setup", "middleware", "routing", "error_handling"],
        "example_count": 50,
    },
    "vercel/next.js": {
        "framework": "nextjs",
        "language": "typescript",
        "category": "fullstack_framework",
        "pattern_types": ["api_routes", "ssr", "components", "middleware"],
        "example_count": 80,
    },
    "nestjs/nest": {
        "framework": "nestjs",
        "language": "typescript",
        "category": "web_framework",
        "pattern_types": ["controllers", "services", "modules", "decorators", "pipes"],
        "example_count": 60,
    },
    # React ecosystem
    "facebook/react": {
        "framework": "react",
        "language": "typescript",
        "category": "ui_library",
        "pattern_types": ["hooks", "components", "state_management", "optimization"],
        "example_count": 100,
    },
    "reduxjs/redux": {
        "framework": "redux",
        "language": "typescript",
        "category": "state_management",
        "pattern_types": ["reducers", "selectors", "middleware", "devtools"],
        "example_count": 50,
    },
    "react-hook-form/react-hook-form": {
        "framework": "react",
        "language": "typescript",
        "category": "forms",
        "pattern_types": ["form_validation", "state_management", "integration"],
        "example_count": 40,
    },
    # TypeScript ecosystem
    "microsoft/typescript": {
        "framework": "typescript",
        "language": "typescript",
        "category": "language",
        "pattern_types": ["type_system", "generics", "decorators", "modules"],
        "example_count": 70,
    },
    # Utilities and tools
    "lodash/lodash": {
        "framework": "lodash",
        "language": "javascript",
        "category": "utilities",
        "pattern_types": ["array_methods", "object_methods", "functional", "async"],
        "example_count": 60,
    },
    "axios/axios": {
        "framework": "axios",
        "language": "typescript",
        "category": "http_client",
        "pattern_types": ["requests", "error_handling", "interceptors", "auth"],
        "example_count": 50,
    },
    "prisma/prisma": {
        "framework": "prisma",
        "language": "typescript",
        "category": "orm",
        "pattern_types": ["queries", "relations", "migrations", "testing"],
        "example_count": 60,
    },
}


# ============================================================
# EXTRACTION TEMPLATES - File patterns to look for
# ============================================================

FILE_PATTERNS = {
    "express": [
        "*/server.js",
        "*/index.js",
        "*/app.js",
        "*/routes/*.js",
        "*/middleware/*.js",
    ],
    "react": [
        "*/components/*.jsx",
        "*/components/*.tsx",
        "*/hooks/*.ts",
        "*/hooks/*.js",
        "*/pages/*.jsx",
        "*/pages/*.tsx",
    ],
    "typescript": [
        "*/src/**/*.ts",
        "*/*.ts",
        "*/lib/**/*.ts",
        "*/utils/**/*.ts",
    ],
}


# ============================================================
# EXTRACTION CONFIGURATION
# ============================================================

EXTRACTION_CONFIG = {
    "min_lines": 10,  # Minimum code lines per example
    "max_lines": 200,  # Maximum code lines per example
    "min_quality_score": 70,  # Minimum quality score (0-100)
    "languages": ["typescript", "javascript"],
    "batch_size": 100,
    "max_repos": 20,
    "min_repo_stars": 500,
}


# ============================================================
# MOCK EXTRACTION FUNCTIONS (Placeholder for actual GitHub API)
# ============================================================

def extract_patterns_from_code(code: str, repo_name: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Extract code patterns from file content.

    This is a placeholder that would be replaced with actual GitHub API calls
    or local repository cloning and parsing.

    Args:
        code: Source code content
        repo_name: Repository name for metadata

    Returns:
        List of (code, metadata) tuples
    """
    examples: List[Tuple[str, Dict[str, Any]]] = []

    # This function would:
    # 1. Parse the code into logical sections
    # 2. Extract function/class definitions
    # 3. Identify patterns and purpose
    # 4. Rate quality
    # 5. Generate metadata

    # Placeholder: Return empty list
    # In production, this would use AST parsing or regex patterns
    return examples


def get_repository_files(repo_name: str, file_patterns: List[str]) -> List[str]:
    """
    Get list of files matching patterns from a GitHub repository.

    Placeholder for GitHub API integration.

    Args:
        repo_name: Repository name (owner/repo)
        file_patterns: List of file glob patterns to match

    Returns:
        List of file paths
    """
    # In production, this would:
    # 1. Connect to GitHub API
    # 2. Use GraphQL to query repository
    # 3. Filter files by patterns
    # 4. Handle pagination

    logger.info(f"Extracting from {repo_name}")
    return []


def estimate_quality_score(code: str, repo_stars: int) -> int:
    """
    Estimate code quality score (0-100).

    Factors:
    - Code length (too short or too long is bad)
    - Repository popularity (higher stars = better examples)
    - Code patterns (use of best practices)
    - Comments/documentation

    Args:
        code: Source code
        repo_stars: Number of GitHub stars

    Returns:
        Quality score 0-100
    """
    score = 50

    # Repository quality bonus
    if repo_stars > 10000:
        score += 25
    elif repo_stars > 5000:
        score += 15
    elif repo_stars > 1000:
        score += 10

    # Code structure quality
    lines = len(code.split('\n'))
    if 10 <= lines <= 200:
        score += 15
    elif 200 < lines <= 300:
        score += 10

    # Best practices detection
    if 'async/await' in code:
        score += 5
    if 'TypeScript' in code or 'interface' in code:
        score += 5
    if 'error' in code.lower() and 'catch' in code:
        score += 5
    if '///' in code or '/**' in code:
        score += 5

    return min(100, max(0, score))


class GitHubExtractor:
    """Extracts TypeScript/JavaScript examples from GitHub repositories."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize extractor with configuration."""
        self.config = {**EXTRACTION_CONFIG, **(config or {})}
        self.examples: List[Tuple[str, Dict[str, Any]]] = []
        self.total_extracted = 0

    def extract_from_repo(self, repo_name: str, repo_info: Dict[str, Any]) -> int:
        """
        Extract examples from a single repository.

        Args:
            repo_name: Repository name (owner/repo)
            repo_info: Repository metadata

        Returns:
            Number of examples extracted
        """
        logger.info(f"Processing {repo_name}...")

        framework = repo_info.get('framework', 'general')
        patterns = FILE_PATTERNS.get(framework, FILE_PATTERNS.get('typescript'))

        # Get files from repository
        files = get_repository_files(repo_name, patterns)
        logger.debug(f"Found {len(files)} matching files")

        extracted_count = 0
        for file_path in files:
            # In production: read file from GitHub API
            # For now: placeholder
            pass

        self.total_extracted += extracted_count
        return extracted_count

    def extract_all(self) -> int:
        """
        Extract examples from all configured repositories.

        Returns:
            Total number of examples extracted
        """
        logger.info("Starting GitHub repository extraction...")
        logger.info(f"Target repositories: {len(POPULAR_REPOS)}")

        for repo_name, repo_info in POPULAR_REPOS.items():
            try:
                self.extract_from_repo(repo_name, repo_info)
            except Exception as e:
                logger.error(f"Failed to extract from {repo_name}", error=str(e))
                continue

        logger.info(f"Extraction complete: {self.total_extracted} examples extracted")
        return self.total_extracted

    def save_examples(self, vector_store) -> int:
        """
        Save extracted examples to vector store.

        Args:
            vector_store: ChromaDB vector store

        Returns:
            Number of examples indexed
        """
        if not self.examples:
            logger.warning("No examples to save")
            return 0

        logger.info(f"Saving {len(self.examples)} examples to vector store...")

        batch_size = self.config['batch_size']
        total_indexed = 0

        for i in range(0, len(self.examples), batch_size):
            batch = self.examples[i:i + batch_size]
            codes = [code for code, _ in batch]

            # Clean metadata
            metadatas = []
            for _, metadata in batch:
                cleaned = {}
                for key, value in metadata.items():
                    if isinstance(value, list):
                        cleaned[key] = ",".join(str(v) for v in value)
                    else:
                        cleaned[key] = value
                metadatas.append(cleaned)

            try:
                code_ids = vector_store.add_batch(codes, metadatas)
                total_indexed += len(code_ids)
                logger.info(
                    f"Batch indexed",
                    batch_num=i // batch_size + 1,
                    batch_size=len(code_ids),
                    total=total_indexed,
                )
            except Exception as e:
                logger.error(f"Batch indexing failed", error=str(e))
                continue

        return total_indexed


def main():
    """Main extraction script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract JavaScript/TypeScript examples from GitHub"
    )
    parser.add_argument(
        "--language",
        choices=["typescript", "javascript", "all"],
        default="all",
        help="Language to extract (default: all)",
    )
    parser.add_argument(
        "--framework",
        choices=["express", "react", "typescript", "all"],
        default="all",
        help="Framework to extract (default: all)",
    )
    parser.add_argument(
        "--min-stars",
        type=int,
        default=500,
        help="Minimum GitHub stars (default: 500)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without actually indexing",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("GitHub TypeScript/JavaScript Extractor")
    print("=" * 60)

    # Create extractor
    config = {
        'min_repo_stars': args.min_stars,
    }

    extractor = GitHubExtractor(config)

    print(f"\n📦 Configured repositories: {len(POPULAR_REPOS)}")
    for repo_name, repo_info in POPULAR_REPOS.items():
        framework = repo_info.get('framework')
        language = repo_info.get('language')
        print(f"  • {repo_name} ({language}/{framework})")

    # Run extraction
    try:
        print(f"\n🔍 Starting extraction (min_stars={args.min_stars})...")

        if args.dry_run:
            print("  (DRY RUN MODE - no indexing)")
            # Would show statistics of what would be extracted
        else:
            extracted_count = extractor.extract_all()
            print(f"\n✅ Extracted {extracted_count} examples from GitHub")

            if extracted_count > 0:
                print(f"  Ready to index into vector store")
                print(f"  Next: python scripts/extract_github_typescript.py --index")

    except Exception as e:
        logger.error("Extraction failed", error=str(e))
        print(f"\n❌ Extraction failed: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
