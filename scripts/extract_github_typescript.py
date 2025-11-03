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

def extract_patterns_from_code(code: str, repo_name: str, file_path: str) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Extract code patterns from file content.

    Identifies functions, classes, and meaningful code blocks.

    Args:
        code: Source code content
        repo_name: Repository name for metadata
        file_path: Path to the file in repository

    Returns:
        List of (code, metadata) tuples
    """
    import re

    examples: List[Tuple[str, Dict[str, Any]]] = []

    # Determine language
    if file_path.endswith('.ts') or file_path.endswith('.tsx'):
        language = 'typescript'
    else:
        language = 'javascript'

    # Extract functions/classes/exports
    # Pattern for function/class declarations
    patterns = [
        # Function declarations
        (r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*{', 'function'),
        # Arrow functions
        (r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::\s*\w+)?\s*=>', 'arrow_function'),
        # Classes
        (r'(?:export\s+)?class\s+(\w+)', 'class'),
        # Interfaces/Types
        (r'(?:export\s+)?(?:interface|type)\s+(\w+)', 'type_definition'),
    ]

    # Find pattern matches
    found_patterns = set()
    for pattern, pattern_type in patterns:
        matches = re.finditer(pattern, code)
        for match in matches:
            found_patterns.add(pattern_type)

    if not found_patterns:
        # No clear patterns found, skip this file
        return []

    # Split code into logical chunks (functions/classes)
    chunks = []

    # Simple splitting by function/class boundaries
    lines = code.split('\n')
    current_chunk = []
    indent_level = 0

    for line in lines:
        current_chunk.append(line)

        # Track braces to find complete blocks
        indent_level += line.count('{') - line.count('}')

        # When we close a block, save the chunk
        if indent_level == 0 and '{' in ''.join(current_chunk) and current_chunk:
            chunk_code = '\n'.join(current_chunk).strip()
            if len(chunk_code.split('\n')) >= 5:  # At least 5 lines
                chunks.append(chunk_code)
                current_chunk = []

    # If we have remaining code, add it
    if current_chunk:
        chunk_code = '\n'.join(current_chunk).strip()
        if len(chunk_code.split('\n')) >= 5:
            chunks.append(chunk_code)

    # Create examples from chunks
    for i, chunk in enumerate(chunks):
        # Skip very long chunks
        if len(chunk.split('\n')) > 200:
            continue

        # Infer pattern name from content
        pattern_name = 'github_extracted'
        if 'export' in chunk:
            pattern_name += '_export'
        if 'async' in chunk:
            pattern_name += '_async'
        if 'class' in chunk:
            pattern_name += '_class'
        if 'interface' in chunk:
            pattern_name += '_interface'

        # Determine task type
        task_type = 'github_pattern'
        if 'test' in file_path.lower():
            task_type = 'testing'
        elif 'component' in file_path.lower():
            task_type = 'component'
        elif 'hook' in file_path.lower():
            task_type = 'component'
        elif 'middleware' in file_path.lower():
            task_type = 'middleware'

        metadata = {
            'language': language,
            'source': 'github',
            'framework': 'github_extracted',
            'docs_section': f'GitHub - {file_path}',
            'pattern': f'{pattern_name}_{i}',
            'task_type': task_type,
            'complexity': 'medium',
            'quality': 'github_example',
            'tags': f'github,{repo_name.split("/")[1]},{language}',
            'approved': True,
        }

        examples.append((chunk, metadata))

    return examples


def get_repository_files(repo_name: str, file_patterns: List[str]) -> List[Tuple[str, str]]:
    """
    Get list of files matching patterns from a GitHub repository.

    Uses GitHub API (requires GITHUB_TOKEN environment variable).

    Args:
        repo_name: Repository name (owner/repo)
        file_patterns: List of file glob patterns to match

    Returns:
        List of (file_path, file_content) tuples
    """
    import os
    import fnmatch
    from github import Github, GithubException

    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.warning("GITHUB_TOKEN not set. Set it to enable GitHub extraction.")
        return []

    try:
        # Connect to GitHub
        g = Github(github_token)
        repo = g.get_repo(repo_name)

        logger.info(f"Extracting from {repo_name} (Stars: {repo.stargazers_count})")

        files = []

        # Get all files from repository
        try:
            contents = repo.get_contents("")
            queue = [contents]

            while queue:
                current = queue.pop(0)

                for item in current:
                    # Skip non-Python/JS/TS files
                    if not any(item.name.endswith(ext) for ext in ['.ts', '.tsx', '.js', '.jsx']):
                        continue

                    # Check if matches pattern
                    matches_pattern = False
                    for pattern in file_patterns:
                        # Simple pattern matching
                        if fnmatch.fnmatch(item.path, pattern):
                            matches_pattern = True
                            break

                    if item.type == 'dir':
                        # Add directory to queue
                        queue.append(repo.get_contents(item.path))
                    elif item.type == 'file' and matches_pattern:
                        # Extract file content
                        try:
                            content = item.decoded_content.decode('utf-8')
                            files.append((item.path, content))
                            logger.debug(f"Extracted: {item.path}")

                            # Limit files per repo to avoid rate limits
                            if len(files) >= 50:
                                logger.info(f"Reached file limit (50) for {repo_name}")
                                return files

                        except Exception as e:
                            logger.debug(f"Failed to decode {item.path}: {str(e)}")
                            continue

        except GithubException as e:
            logger.error(f"GitHub API error for {repo_name}: {str(e)}")
            return files

        logger.info(f"Extracted {len(files)} files from {repo_name}")
        return files

    except Exception as e:
        logger.error(f"Failed to extract from {repo_name}", error=str(e))
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

        # Get files from repository (now with real GitHub API)
        files = get_repository_files(repo_name, patterns)
        logger.debug(f"Found {len(files)} matching files")

        extracted_count = 0
        repo_stars = repo_info.get('stars', 0)

        for file_path, file_content in files:
            # Extract patterns from file
            patterns_found = extract_patterns_from_code(file_content, repo_name, file_path)

            for code, metadata in patterns_found:
                # Calculate quality score
                quality_score = estimate_quality_score(code, repo_stars)

                # Skip low-quality examples
                if quality_score < self.config['min_quality_score']:
                    logger.debug(f"Skipped {metadata['pattern']}: quality {quality_score} < {self.config['min_quality_score']}")
                    continue

                # Add quality score to metadata
                metadata['quality_score'] = quality_score

                # Add to examples
                self.examples.append((code, metadata))
                extracted_count += 1

                logger.debug(f"Extracted: {metadata['pattern']} (quality: {quality_score})")

        self.total_extracted += extracted_count
        return extracted_count

    def extract_all(self) -> int:
        """
        Extract examples from all configured repositories.

        Returns:
            Total number of examples extracted
        """
        import os
        from github import Github, GithubException

        logger.info("Starting GitHub repository extraction...")
        logger.info(f"Target repositories: {len(POPULAR_REPOS)}")

        # Get GitHub token for API calls
        github_token = os.getenv('GITHUB_TOKEN')

        for repo_name, repo_info in POPULAR_REPOS.items():
            try:
                # Get real star count from GitHub if token available
                if github_token:
                    try:
                        g = Github(github_token)
                        repo = g.get_repo(repo_name)
                        repo_info['stars'] = repo.stargazers_count
                        logger.info(f"{repo_name}: {repo.stargazers_count} stars")
                    except GithubException as e:
                        logger.warning(f"Could not fetch star count for {repo_name}: {str(e)}")

                self.extract_from_repo(repo_name, repo_info)

            except Exception as e:
                logger.error(f"Failed to extract from {repo_name}", error=str(e))
                continue

        logger.info(f"Extraction complete: {self.total_extracted} examples extracted")
        logger.info(f"Total examples in memory: {len(self.examples)}")
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
