#!/usr/bin/env python
"""
Migrate Existing Code to RAG Script

Indexes existing project code into ChromaDB for RAG-enhanced code generation.
Analyzes project structure and selectively indexes quality code examples.

Usage:
    python scripts/migrate_existing_code.py [--path src] [--batch-size 100] [--dry-run]
"""

import sys
import ast
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
)
from src.observability import get_logger

logger = get_logger("migrate_existing_code")


@dataclass
class CodeSnippet:
    """Represents a code snippet to be indexed."""

    code: str
    file_path: str
    start_line: int
    end_line: int
    name: str
    type: str  # function, class, method
    docstring: Optional[str] = None
    complexity: str = "medium"
    imports: List[str] = None


class PythonCodeExtractor:
    """Extract meaningful code snippets from Python files."""

    def __init__(self):
        self.snippets: List[CodeSnippet] = []

    def extract_from_file(self, file_path: Path) -> List[CodeSnippet]:
        """
        Extract code snippets from a Python file.

        Args:
            file_path: Path to Python file

        Returns:
            List of code snippets
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            snippets = []
            lines = content.split("\n")

            # Extract top-level imports
            imports = self._extract_imports(tree)

            # Extract functions and classes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    snippet = self._extract_function(node, lines, file_path, imports)
                    if snippet:
                        snippets.append(snippet)

                elif isinstance(node, ast.ClassDef):
                    # Extract class and its methods
                    class_snippets = self._extract_class(node, lines, file_path, imports)
                    snippets.extend(class_snippets)

            return snippets

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}", error=str(e))
            return []

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports

    def _extract_function(
        self,
        node: ast.FunctionDef,
        lines: List[str],
        file_path: Path,
        imports: List[str],
    ) -> Optional[CodeSnippet]:
        """Extract a function definition."""
        # Skip private functions (unless they're special methods)
        if node.name.startswith("_") and not node.name.startswith("__"):
            return None

        # Skip test functions
        if node.name.startswith("test_"):
            return None

        # Extract code
        start_line = node.lineno - 1
        end_line = node.end_lineno

        if end_line is None:
            return None

        code = "\n".join(lines[start_line:end_line])

        # Extract docstring
        docstring = ast.get_docstring(node)

        # Determine complexity
        complexity = self._estimate_complexity(node)

        return CodeSnippet(
            code=code,
            file_path=str(file_path),
            start_line=start_line + 1,
            end_line=end_line,
            name=node.name,
            type="function",
            docstring=docstring,
            complexity=complexity,
            imports=imports,
        )

    def _extract_class(
        self,
        node: ast.ClassDef,
        lines: List[str],
        file_path: Path,
        imports: List[str],
    ) -> List[CodeSnippet]:
        """Extract a class and its public methods."""
        snippets = []

        # Extract the full class
        start_line = node.lineno - 1
        end_line = node.end_lineno

        if end_line is None:
            return snippets

        code = "\n".join(lines[start_line:end_line])
        docstring = ast.get_docstring(node)

        # Only include class if it has docstring or is not too large
        if docstring or (end_line - start_line) < 50:
            snippets.append(
                CodeSnippet(
                    code=code,
                    file_path=str(file_path),
                    start_line=start_line + 1,
                    end_line=end_line,
                    name=node.name,
                    type="class",
                    docstring=docstring,
                    complexity=self._estimate_complexity(node),
                    imports=imports,
                )
            )

        # Extract public methods
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                # Skip private methods
                if item.name.startswith("_") and not item.name.startswith("__"):
                    continue

                method_start = item.lineno - 1
                method_end = item.end_lineno

                if method_end is None:
                    continue

                method_code = "\n".join(lines[method_start:method_end])
                method_docstring = ast.get_docstring(item)

                snippets.append(
                    CodeSnippet(
                        code=method_code,
                        file_path=str(file_path),
                        start_line=method_start + 1,
                        end_line=method_end,
                        name=f"{node.name}.{item.name}",
                        type="method",
                        docstring=method_docstring,
                        complexity=self._estimate_complexity(item),
                        imports=imports,
                    )
                )

        return snippets

    def _estimate_complexity(self, node: ast.AST) -> str:
        """Estimate code complexity based on AST structure."""
        # Count control flow statements
        control_flow = 0

        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                control_flow += 1

        # Estimate complexity
        if control_flow == 0:
            return "low"
        elif control_flow <= 3:
            return "medium"
        else:
            return "high"


class CodeMigrator:
    """Migrate existing code to RAG system."""

    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.extractor = PythonCodeExtractor()
        self.stats = {
            "files_processed": 0,
            "snippets_extracted": 0,
            "snippets_indexed": 0,
            "errors": 0,
        }

    def migrate_directory(
        self,
        path: Path,
        batch_size: int = 100,
        dry_run: bool = False,
        exclude_patterns: List[str] = None,
    ) -> Dict[str, int]:
        """
        Migrate all Python files in a directory.

        Args:
            path: Directory path to migrate
            batch_size: Batch size for indexing
            dry_run: If True, only extract without indexing
            exclude_patterns: Patterns to exclude

        Returns:
            Migration statistics
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "test_*.py",
                "*_test.py",
                "tests/*",
                "__pycache__/*",
                "venv/*",
                ".venv/*",
                "build/*",
                "dist/*",
                "*.egg-info/*",
            ]

        logger.info(f"Starting migration from {path}")

        # Find all Python files
        python_files = self._find_python_files(path, exclude_patterns)

        logger.info(f"Found {len(python_files)} Python files")

        # Extract snippets from all files
        all_snippets = []

        for file_path in python_files:
            try:
                snippets = self.extractor.extract_from_file(file_path)
                all_snippets.extend(snippets)
                self.stats["files_processed"] += 1
                self.stats["snippets_extracted"] += len(snippets)

                logger.debug(f"Extracted {len(snippets)} snippets from {file_path}")

            except Exception as e:
                logger.error(f"Failed to process {file_path}", error=str(e))
                self.stats["errors"] += 1

        logger.info(f"Extracted {len(all_snippets)} total snippets")

        # Filter quality snippets
        quality_snippets = self._filter_quality_snippets(all_snippets)

        logger.info(
            f"Filtered to {len(quality_snippets)} quality snippets "
            f"({len(quality_snippets) / len(all_snippets) * 100:.1f}%)"
        )

        if dry_run:
            logger.info("Dry run mode - skipping indexing")
            self._print_sample_snippets(quality_snippets[:5])
            return self.stats

        # Index snippets in batches
        self._index_snippets(quality_snippets, batch_size)

        return self.stats

    def _find_python_files(
        self, path: Path, exclude_patterns: List[str]
    ) -> List[Path]:
        """Find all Python files excluding patterns."""
        python_files = []

        for file_path in path.rglob("*.py"):
            # Check exclusion patterns
            should_exclude = False

            for pattern in exclude_patterns:
                if file_path.match(pattern):
                    should_exclude = True
                    break

            if not should_exclude:
                python_files.append(file_path)

        return python_files

    def _filter_quality_snippets(
        self, snippets: List[CodeSnippet]
    ) -> List[CodeSnippet]:
        """Filter snippets to keep only quality examples."""
        quality = []

        for snippet in snippets:
            # Must have docstring for functions/classes
            if snippet.type in ["function", "class"] and not snippet.docstring:
                continue

            # Must not be too short
            if len(snippet.code.strip()) < 50:
                continue

            # Must not be too long (likely generated or boilerplate)
            if len(snippet.code.strip()) > 2000:
                continue

            quality.append(snippet)

        return quality

    def _index_snippets(self, snippets: List[CodeSnippet], batch_size: int):
        """Index snippets in batches."""
        logger.info(f"Indexing {len(snippets)} snippets in batches of {batch_size}")

        for i in range(0, len(snippets), batch_size):
            batch = snippets[i : i + batch_size]

            # Prepare batch data
            codes = [s.code for s in batch]
            metadatas = [self._create_metadata(s) for s in batch]

            try:
                code_ids = self.vector_store.add_batch(codes, metadatas)
                self.stats["snippets_indexed"] += len(code_ids)

                logger.info(
                    f"Batch indexed",
                    batch_num=i // batch_size + 1,
                    batch_size=len(code_ids),
                    total=self.stats["snippets_indexed"],
                )

            except Exception as e:
                logger.error(
                    f"Batch indexing failed",
                    batch_num=i // batch_size + 1,
                    error=str(e),
                )
                self.stats["errors"] += 1

    def _create_metadata(self, snippet: CodeSnippet) -> Dict[str, Any]:
        """Create metadata for a snippet."""
        metadata = {
            "language": "python",
            "file_path": snippet.file_path,
            "start_line": snippet.start_line,
            "end_line": snippet.end_line,
            "name": snippet.name,
            "type": snippet.type,
            "complexity": snippet.complexity,
            "source": "project_migration",
            "approved": False,  # Migrated code not pre-approved
        }

        if snippet.docstring:
            metadata["has_docstring"] = True
            metadata["description"] = snippet.docstring[:200]  # First 200 chars

        if snippet.imports:
            # Add framework detection
            frameworks = self._detect_frameworks(snippet.imports)
            if frameworks:
                metadata["frameworks"] = frameworks

            # Add common imports
            metadata["imports"] = snippet.imports[:10]  # First 10 imports

        return metadata

    def _detect_frameworks(self, imports: List[str]) -> List[str]:
        """Detect frameworks from imports."""
        frameworks = []

        framework_map = {
            "fastapi": "fastapi",
            "flask": "flask",
            "django": "django",
            "sqlalchemy": "sqlalchemy",
            "pydantic": "pydantic",
            "pytest": "pytest",
            "asyncio": "asyncio",
            "aiohttp": "aiohttp",
        }

        for imp in imports:
            for key, framework in framework_map.items():
                if key in imp.lower():
                    if framework not in frameworks:
                        frameworks.append(framework)

        return frameworks

    def _print_sample_snippets(self, snippets: List[CodeSnippet]):
        """Print sample snippets for dry run."""
        print("\n" + "=" * 60)
        print("Sample Snippets (first 5)")
        print("=" * 60)

        for i, snippet in enumerate(snippets, 1):
            print(f"\n{i}. {snippet.name} ({snippet.type})")
            print(f"   File: {snippet.file_path}:{snippet.start_line}")
            print(f"   Complexity: {snippet.complexity}")

            if snippet.docstring:
                print(f"   Docstring: {snippet.docstring[:100]}...")

            print(f"   Code preview:")
            preview_lines = snippet.code.split("\n")[:5]
            for line in preview_lines:
                print(f"     {line}")

            if len(snippet.code.split("\n")) > 5:
                print("     ...")


def main():
    """Main migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate existing code to RAG")
    parser.add_argument(
        "--path",
        type=str,
        default="src",
        help="Path to migrate (default: src)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for indexing (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract without indexing (for testing)",
    )
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        help="Additional exclusion patterns",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Migrate Existing Code to RAG")
    print("=" * 60)

    # Validate path
    path = Path(args.path)

    if not path.exists():
        print(f"\n❌ Path not found: {path}")
        return 1

    if not path.is_dir():
        print(f"\n❌ Path is not a directory: {path}")
        return 1

    print(f"\n📂 Source path: {path.absolute()}")
    print(f"📦 Batch size: {args.batch_size}")

    if args.dry_run:
        print("⚠️  DRY RUN MODE - No indexing will be performed")

    # Initialize RAG components
    if not args.dry_run:
        try:
            logger.info("Initializing RAG components...")
            embedding_model = create_embedding_model()
            vector_store = create_vector_store(embedding_model)

            logger.info("RAG components initialized")

        except Exception as e:
            logger.error("Failed to initialize RAG", error=str(e))
            print(f"\n❌ Initialization failed: {str(e)}")
            print("\nPlease ensure:")
            print("  1. ChromaDB is running: docker-compose up chromadb -d")
            print("  2. CHROMADB_HOST and CHROMADB_PORT are configured in .env")
            return 1
    else:
        vector_store = None

    # Create migrator
    migrator = CodeMigrator(vector_store)

    # Build exclusion patterns
    exclude_patterns = None
    if args.exclude:
        exclude_patterns = args.exclude

    # Run migration
    try:
        print("\n🔄 Starting migration...\n")

        stats = migrator.migrate_directory(
            path=path,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            exclude_patterns=exclude_patterns,
        )

        # Print results
        print("\n" + "=" * 60)
        print("Migration Complete")
        print("=" * 60)
        print(f"  Files processed: {stats['files_processed']}")
        print(f"  Snippets extracted: {stats['snippets_extracted']}")

        if not args.dry_run:
            print(f"  Snippets indexed: {stats['snippets_indexed']}")

        if stats["errors"] > 0:
            print(f"  ⚠️  Errors: {stats['errors']}")

        if not args.dry_run:
            # Get final stats
            vector_stats = vector_store.get_stats()
            print(f"\n  Total examples in RAG: {vector_stats.get('total_examples', 0)}")

        print("\n✅ Migration complete!")

        return 0

    except Exception as e:
        logger.error("Migration failed", error=str(e))
        print(f"\n❌ Migration failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
