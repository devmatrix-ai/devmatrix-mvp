#!/usr/bin/env python
"""
Phase 3: GitHub Repository Extractor

Extracts high-quality code examples from popular open-source Python repositories.

Repos target:
- FastAPI: Popular REST API patterns
- SQLModel: ORM and database patterns
- Pydantic: Data validation patterns
- Pytest: Testing and fixtures
- HTTPX: HTTP client patterns
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

from src.rag import create_embedding_model
from src.rag.vector_store import VectorStore
from src.observability import get_logger

logger = get_logger("github_extractor")

@dataclass
class Repository:
    """GitHub repository configuration"""
    url: str
    name: str
    extract_paths: List[str]  # Patterns to extract (e.g., ["fastapi/routing.py", "fastapi/*.py"])
    target_count: int
    category: str


REPOSITORIES = [
    Repository(
        url="https://github.com/tiangolo/fastapi.git",
        name="FastAPI",
        extract_paths=[
            "fastapi/*.py",  # Core patterns
            "fastapi/routing.py",
            "fastapi/security/*.py",
        ],
        target_count=80,
        category="FastAPI Patterns"
    ),
    Repository(
        url="https://github.com/tiangolo/sqlmodel.git",
        name="SQLModel",
        extract_paths=[
            "sqlmodel/*.py",
            "sqlmodel/sql/*.py",
        ],
        target_count=60,
        category="SQLModel ORM"
    ),
    Repository(
        url="https://github.com/pydantic/pydantic.git",
        name="Pydantic",
        extract_paths=[
            "pydantic/*.py",
            "pydantic/main.py",
            "pydantic/fields.py",
            "pydantic/validators.py",
        ],
        target_count=70,
        category="Pydantic Validation"
    ),
    Repository(
        url="https://github.com/pytest-dev/pytest.git",
        name="Pytest",
        extract_paths=[
            "src/_pytest/*.py",
            "src/_pytest/fixtures.py",
            "src/_pytest/mark.py",
        ],
        target_count=50,
        category="Pytest Testing"
    ),
    Repository(
        url="https://github.com/encode/httpx.git",
        name="HTTPX",
        extract_paths=[
            "_httpx/*.py",
            "_httpx/models.py",
            "_httpx/client.py",
        ],
        target_count=40,
        category="HTTPX HTTP Client"
    ),
]


def clone_repo(repo: Repository, work_dir: Path) -> Optional[Path]:
    """Clone repository to temporary directory"""
    try:
        repo_path = work_dir / repo.name.lower()
        
        if repo_path.exists():
            logger.info(f"Using existing repo: {repo.name}")
            return repo_path
        
        logger.info(f"Cloning {repo.name} from {repo.url}")
        subprocess.run(
            ["git", "clone", "--depth", "1", repo.url, str(repo_path)],
            capture_output=True,
            timeout=60,
            check=True
        )
        logger.info(f"Cloned {repo.name} successfully")
        return repo_path
    except Exception as e:
        logger.error(f"Failed to clone {repo.name}: {str(e)}")
        return None


def extract_python_files(repo_path: Path, patterns: List[str], max_files: int = 50) -> List[Path]:
    """Extract Python files matching patterns"""
    files = []
    
    try:
        for pattern in patterns:
            # Simple glob-based extraction
            if "*" in pattern:
                base_dir = repo_path / pattern.split("*")[0].rstrip("/")
                if base_dir.exists():
                    for py_file in base_dir.glob("*.py"):
                        if len(files) < max_files and py_file.is_file():
                            files.append(py_file)
            else:
                py_file = repo_path / pattern
                if py_file.exists() and py_file.is_file() and len(files) < max_files:
                    files.append(py_file)
    except Exception as e:
        logger.error(f"Error extracting files: {str(e)}")
    
    return files[:max_files]


def extract_code_chunks(file_path: Path, max_chunk_size: int = 1000) -> List[str]:
    """Extract code chunks from a Python file"""
    chunks = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Split by class/function definitions
        lines = content.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            current_chunk.append(line)
            current_size += len(line)
            
            # Extract complete functions/classes
            if current_size > max_chunk_size and (
                line.strip() and not line[0].isspace()
            ):
                chunk_text = '\n'.join(current_chunk)
                if chunk_text.strip() and len(chunk_text) > 50:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0
        
        # Add final chunk
        if current_chunk:
            chunk_text = '\n'.join(current_chunk)
            if chunk_text.strip() and len(chunk_text) > 50:
                chunks.append(chunk_text)
    
    except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")
    
    return chunks


def extract_from_repo(repo: Repository) -> List[Dict[str, Any]]:
    """Extract examples from a repository"""
    examples = []
    
    with tempfile.TemporaryDirectory() as work_dir:
        work_path = Path(work_dir)
        repo_path = clone_repo(repo, work_path)
        
        if not repo_path:
            return examples
        
        # Extract Python files
        py_files = extract_python_files(repo_path, repo.extract_paths, max_files=50)
        logger.info(f"Found {len(py_files)} Python files in {repo.name}")
        
        # Extract code chunks
        for py_file in py_files:
            chunks = extract_code_chunks(py_file)
            
            for i, chunk in enumerate(chunks):
                if len(examples) >= repo.target_count:
                    break
                
                rel_path = str(py_file.relative_to(repo_path))
                example = {
                    "code": chunk,
                    "metadata": {
                        "source": f"github_{repo.name.lower()}",
                        "repository": repo.name,
                        "category": repo.category,
                        "file": rel_path,
                        "chunk": i,
                        "language": "python",
                    },
                    "id": f"github_{repo.name.lower()}_{rel_path.replace('/', '_')}_{i}"
                }
                examples.append(example)
        
        logger.info(f"Extracted {len(examples)}/{repo.target_count} examples from {repo.name}")
    
    return examples


def seed_github_repositories():
    """Main function to seed RAG from GitHub repositories"""
    print("\n" + "="*80)
    print("PHASE 3: GITHUB REPOSITORY EXTRACTION")
    print("="*80)
    
    try:
        # Initialize
        embedding_model = create_embedding_model()
        vector_store = VectorStore(embedding_model, collection_name="devmatrix_project_code")
        
        total_extracted = 0
        all_examples = []
        
        # Extract from each repository
        print("\n📦 Extracting from repositories:\n")
        
        for repo in REPOSITORIES:
            print(f"  🔍 {repo.name} (target: {repo.target_count})...", end="", flush=True)
            examples = extract_from_repo(repo)
            total_extracted += len(examples)
            all_examples.extend(examples)
            print(f" ✅ {len(examples)} examples")
        
        if not all_examples:
            print("\n⚠️  No examples extracted from any repository!")
            return False
        
        # Index examples in safe chunks to avoid GPU OOM
        print(f"\n📇 Indexing {len(all_examples)} examples to ChromaDB in chunks...")
        CHUNK = 50
        total = len(all_examples)
        for start in range(0, total, CHUNK):
            end = min(start + CHUNK, total)
            batch = all_examples[start:end]
            # Truncate overly long code blocks to prevent OOM during embedding
            codes = [ex["code"][:2000] for ex in batch]
            metadatas = [ex["metadata"] for ex in batch]
            example_ids = [ex["id"] for ex in batch]
            vector_store.add_batch(
                codes=codes,
                metadatas=metadatas,
                example_ids=example_ids
            )
            print(f"   ✓ Indexed {end}/{total}")
        
        # Verify
        collection_count = vector_store.collection.count()
        print(f"\n✅ Successfully indexed {len(all_examples)} GitHub examples")
        print(f"   Collection total: {collection_count} examples")
        
        # Summary by repo
        print("\n📊 Summary by Repository:")
        for repo in REPOSITORIES:
            repo_examples = [ex for ex in all_examples if ex["metadata"]["repository"] == repo.name]
            print(f"  • {repo.name}: {len(repo_examples)} examples")
        
        return True
        
    except Exception as e:
        logger.error(f"Extraction failed: {str(e)}")
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = seed_github_repositories()
    sys.exit(0 if success else 1)

