#!/usr/bin/env python
"""
Project Standards Seeding Script

Extracts code examples from project standards and documentation:
- .specify/memory/constitution.md
- CONTRIBUTING.md
- agent-os/standards/

These examples show good/bad patterns and compliance with project standards.

Usage:
    python scripts/seed_project_standards.py [--clear]
"""

import sys
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag import (
    create_embedding_model,
    create_vector_store,
)
from src.observability import get_logger

logger = get_logger("seed_project_standards")


class StandardsExtractor:
    """Extract code examples from project standards documentation."""
    
    CODE_BLOCK_PATTERN = re.compile(
        r"```(\w+)\n(.*?)```",
        re.DOTALL | re.MULTILINE
    )
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.examples: List[Tuple[str, Dict[str, Any]]] = []
    
    def extract_from_constitution(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract examples from constitution.md."""
        constitution_path = self.project_root / ".specify/memory/constitution.md"
        
        if not constitution_path.exists():
            logger.warning(f"Constitution file not found: {constitution_path}")
            return []
        
        logger.info(f"Extracting from {constitution_path}")
        content = constitution_path.read_text(encoding="utf-8")
        
        examples = []
        
        # Extract code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1).lower()
            code = match.group(2).strip()
            
            # Only process Python and TypeScript
            if language not in ["python", "typescript", "javascript"]:
                continue
            
            # Skip very short examples
            if len(code) < 50:
                continue
            
            # Determine if good or bad example
            is_bad_example = any(marker in code for marker in ["BAD:", "# BAD", "// BAD", "DON'T", "AVOID"])
            is_good_example = any(marker in code for marker in ["GOOD:", "# GOOD", "// GOOD", "RECOMMENDED"])
            
            # Extract context (section heading)
            # Find the last heading before this code block
            code_start_pos = match.start()
            preceding_text = content[:code_start_pos]
            heading_matches = list(re.finditer(r"^#+\s+(.+)$", preceding_text, re.MULTILINE))
            section = heading_matches[-1].group(1) if heading_matches else "Unknown"
            
            metadata = {
                "source": "constitution",
                "language": language,
                "pattern": self._infer_pattern(code, section),
                "task_type": "code_standard",
                "quality": "anti_pattern" if is_bad_example else "production",
                "example_type": "bad" if is_bad_example else "good" if is_good_example else "neutral",
                "section": section,
                "tags": ["constitution", "standards", "compliance"],
                "approved": not is_bad_example,
            }
            
            examples.append((code, metadata))
        
        logger.info(f"Extracted {len(examples)} examples from constitution")
        return examples
    
    def extract_from_contributing(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract examples from CONTRIBUTING.md."""
        contributing_path = self.project_root / "CONTRIBUTING.md"
        
        if not contributing_path.exists():
            logger.warning(f"CONTRIBUTING.md not found: {contributing_path}")
            return []
        
        logger.info(f"Extracting from {contributing_path}")
        content = contributing_path.read_text(encoding="utf-8")
        
        examples = []
        
        # Extract code blocks
        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1).lower()
            code = match.group(2).strip()
            
            # Only process Python, TypeScript, bash
            if language not in ["python", "typescript", "javascript", "bash", "shell"]:
                continue
            
            # Skip very short examples
            if len(code) < 50:
                continue
            
            # Determine if good or bad example
            is_bad_example = any(marker in code for marker in ["BAD:", "# BAD", "// BAD", "❌"])
            is_good_example = any(marker in code for marker in ["GOOD:", "# GOOD", "// GOOD", "✅"])
            
            # Extract context
            code_start_pos = match.start()
            preceding_text = content[:code_start_pos]
            heading_matches = list(re.finditer(r"^#+\s+(.+)$", preceding_text, re.MULTILINE))
            section = heading_matches[-1].group(1) if heading_matches else "Unknown"
            
            metadata = {
                "source": "contributing",
                "language": language,
                "pattern": self._infer_pattern(code, section),
                "task_type": "code_standard",
                "quality": "anti_pattern" if is_bad_example else "production",
                "example_type": "bad" if is_bad_example else "good" if is_good_example else "neutral",
                "section": section,
                "tags": ["contributing", "best_practices", "workflow"],
                "approved": not is_bad_example,
            }
            
            examples.append((code, metadata))
        
        logger.info(f"Extracted {len(examples)} examples from CONTRIBUTING.md")
        return examples
    
    def extract_from_standards(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract examples from agent-os/standards/ directory."""
        standards_dir = self.project_root / "agent-os/standards"
        
        if not standards_dir.exists():
            logger.warning(f"Standards directory not found: {standards_dir}")
            return []
        
        logger.info(f"Extracting from {standards_dir}")
        examples = []
        
        # Find all markdown files in standards
        for md_file in standards_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                
                # Extract code blocks
                for match in self.CODE_BLOCK_PATTERN.finditer(content):
                    language = match.group(1).lower()
                    code = match.group(2).strip()
                    
                    # Only process Python, TypeScript, bash
                    if language not in ["python", "typescript", "javascript", "bash", "shell"]:
                        continue
                    
                    # Skip very short examples
                    if len(code) < 50:
                        continue
                    
                    # Determine example type
                    is_bad_example = any(marker in code for marker in ["BAD:", "# BAD", "// BAD", "❌", "AVOID"])
                    is_good_example = any(marker in code for marker in ["GOOD:", "# GOOD", "// GOOD", "✅", "RECOMMENDED"])
                    
                    # Get standard name from file path
                    standard_name = md_file.stem.replace("-", "_")
                    
                    metadata = {
                        "source": "agent_os_standards",
                        "language": language,
                        "pattern": self._infer_pattern(code, standard_name),
                        "task_type": "code_standard",
                        "quality": "anti_pattern" if is_bad_example else "production",
                        "example_type": "bad" if is_bad_example else "good" if is_good_example else "neutral",
                        "standard": standard_name,
                        "file": str(md_file.relative_to(self.project_root)),
                        "tags": ["standards", "agent_os", standard_name],
                        "approved": not is_bad_example,
                    }
                    
                    examples.append((code, metadata))
            
            except Exception as e:
                logger.warning(f"Failed to parse {md_file}: {e}")
                continue
        
        logger.info(f"Extracted {len(examples)} examples from standards")
        return examples
    
    def _infer_pattern(self, code: str, context: str) -> str:
        """Infer pattern type from code and context."""
        code_lower = code.lower()
        context_lower = context.lower()
        
        # Pattern inference rules
        if any(kw in code_lower for kw in ["async def", "await", "asyncio"]):
            return "async_pattern"
        elif any(kw in code_lower for kw in ["test_", "pytest", "@pytest"]):
            return "testing"
        elif any(kw in code_lower for kw in ["logger", "log.", "logging"]):
            return "logging"
        elif any(kw in code_lower for kw in ["validate", "validator", "pydantic"]):
            return "validation"
        elif any(kw in code_lower for kw in ["error", "exception", "try:", "except"]):
            return "error_handling"
        elif any(kw in code_lower for kw in ["def ", "class "]):
            if "type" in context_lower:
                return "type_safety"
            elif "doc" in context_lower:
                return "documentation"
            elif "naming" in context_lower:
                return "naming_convention"
        elif "git" in context_lower or "commit" in context_lower:
            return "git_workflow"
        
        return "general"
    
    def extract_all(self) -> List[Tuple[str, Dict[str, Any]]]:
        """Extract from all sources."""
        all_examples = []
        
        all_examples.extend(self.extract_from_constitution())
        all_examples.extend(self.extract_from_contributing())
        all_examples.extend(self.extract_from_standards())
        
        logger.info(f"Total examples extracted: {len(all_examples)}")
        return all_examples


def seed_standards(
    vector_store,
    examples: List[Tuple[str, Dict[str, Any]]],
    batch_size: int = 50,
    clear_first: bool = False,
) -> int:
    """
    Seed vector store with project standards examples.
    
    Args:
        vector_store: Vector store instance
        examples: List of (code, metadata) tuples
        batch_size: Batch size for indexing
        clear_first: Whether to clear collection first
    
    Returns:
        Number of examples indexed
    """
    if clear_first:
        logger.info("Clearing existing collection...")
        count = vector_store.clear_collection()
        logger.info(f"Cleared {count} existing examples")
    
    if not examples:
        logger.warning("No examples to index")
        return 0
    
    logger.info(f"Seeding {len(examples)} project standards examples...")
    
    # Process in batches
    total_indexed = 0
    
    for i in range(0, len(examples), batch_size):
        batch = examples[i : i + batch_size]
        codes = [code for code, _ in batch]
        
        # Convert list values to strings for ChromaDB compatibility
        metadatas = []
        for _, metadata in batch:
            cleaned_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, list):
                    cleaned_metadata[key] = ",".join(str(v) for v in value)
                else:
                    cleaned_metadata[key] = value
            metadatas.append(cleaned_metadata)
        
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
            logger.error(f"Batch indexing failed", batch_num=i // batch_size + 1, error=str(e))
            continue
    
    return total_indexed


def main():
    """Main seeding script."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed RAG with project standards")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing collection before seeding",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for indexing (default: 50)",
    )
    parser.add_argument(
        "--source",
        choices=["all", "constitution", "contributing", "standards"],
        default="all",
        help="Source to extract from",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Project Standards Seeding Script")
    print("=" * 60)
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Initialize extractor
    extractor = StandardsExtractor(project_root)
    
    # Extract examples based on source
    if args.source == "all":
        examples = extractor.extract_all()
    elif args.source == "constitution":
        examples = extractor.extract_from_constitution()
    elif args.source == "contributing":
        examples = extractor.extract_from_contributing()
    elif args.source == "standards":
        examples = extractor.extract_from_standards()
    
    if not examples:
        print("\n⚠️  No examples found to index")
        return 1
    
    # Initialize RAG components
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
    
    # Seed examples
    try:
        print(f"\n📦 Seeding {len(examples)} standards examples from {args.source}...")
        if args.clear:
            print("⚠️  Clearing existing collection first...")
        
        indexed_count = seed_standards(
            vector_store,
            examples,
            batch_size=args.batch_size,
            clear_first=args.clear,
        )
        
        print(f"\n✅ Successfully indexed {indexed_count} examples")
        
        # Show stats
        stats = vector_store.get_stats()
        print(f"\n📊 Vector Store Stats:")
        print(f"  Total examples: {stats.get('total_examples', 0)}")
        
        # Breakdown by type
        good_examples = sum(1 for _, m in examples if m.get("example_type") == "good")
        bad_examples = sum(1 for _, m in examples if m.get("example_type") == "bad")
        neutral_examples = len(examples) - good_examples - bad_examples
        
        print(f"\n📋 Examples Breakdown:")
        print(f"  ✅ Good examples: {good_examples}")
        print(f"  ❌ Bad examples (anti-patterns): {bad_examples}")
        print(f"  ⚪ Neutral examples: {neutral_examples}")
    
    except Exception as e:
        logger.error("Seeding failed", error=str(e))
        print(f"\n❌ Seeding failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

