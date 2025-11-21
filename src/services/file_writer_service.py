"""
File Writer Service - MGE V2

Writes generated atoms to the filesystem, creating the project structure.

Flow:
1. Load atoms from database
2. Group atoms by target file
3. Merge atoms into complete files
4. Write files to workspace directory
5. Track written files in database

Author: DevMatrix Team
Date: 2025-11-10
"""

import os
import uuid
import ast
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from src.models import AtomicUnit, MasterPlan
from src.observability import StructuredLogger

logger = StructuredLogger("file_writer_service", output_json=False)


class FileWriterService:
    """
    Service for writing atoms to filesystem.

    Features:
    - Groups atoms by target file
    - Creates directory structure
    - Merges atoms into complete files
    - Validates file structure
    - Tracks written files
    """

    def __init__(
        self,
        db: Session,
        workspace_base: str = "/tmp/mge_v2_workspace"
    ):
        """
        Initialize file writer service.

        Args:
            db: Database session
            workspace_base: Base directory for generated code
        """
        self.db = db
        self.workspace_base = workspace_base

        logger.info(
            "FileWriterService initialized",
            extra={"workspace_base": workspace_base}
        )

    async def write_atoms_to_files(
        self,
        masterplan_id: uuid.UUID,
        workspace_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write all atoms for a masterplan to filesystem.

        Args:
            masterplan_id: MasterPlan UUID
            workspace_name: Optional workspace subdirectory name

        Returns:
            Dict with write results
        """
        logger.info(
            "Starting file write process",
            extra={"masterplan_id": str(masterplan_id)}
        )

        # Load masterplan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise ValueError(f"MasterPlan {masterplan_id} not found")

        # Create workspace directory
        if not workspace_name:
            workspace_name = masterplan.project_name.lower().replace(" ", "-")

        workspace_path = Path(self.workspace_base) / str(masterplan_id) / workspace_name
        workspace_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Created workspace directory",
            extra={"workspace_path": str(workspace_path)}
        )

        # Load all atoms
        atoms = self.db.query(AtomicUnit).filter(
            AtomicUnit.masterplan_id == masterplan_id
        ).order_by(AtomicUnit.atom_number).all()

        if not atoms:
            logger.warning(f"No atoms found for masterplan {masterplan_id}")
            return {
                "success": False,
                "error": "No atoms to write",
                "files_written": 0
            }

        logger.info(
            f"Loaded {len(atoms)} atoms for writing",
            extra={"atom_count": len(atoms)}
        )

        # Group atoms by file
        files_map = self._group_atoms_by_file(atoms)

        logger.info(
            f"Grouped atoms into {len(files_map)} files",
            extra={"file_count": len(files_map)}
        )

        # Write each file
        files_written = []
        errors = []

        for file_path, file_atoms in files_map.items():
            try:
                full_path = workspace_path / file_path

                # Create parent directories
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Merge atoms into file content
                file_content = self._merge_atoms_to_file(file_atoms)

                # Write file
                full_path.write_text(file_content, encoding='utf-8')

                files_written.append({
                    "path": str(file_path),
                    "full_path": str(full_path),
                    "atoms": len(file_atoms),
                    "size": len(file_content)
                })

                logger.info(
                    f"Wrote file: {file_path}",
                    extra={
                        "file_path": str(file_path),
                        "atoms": len(file_atoms),
                        "size": len(file_content)
                    }
                )

            except Exception as e:
                error_msg = f"Failed to write {file_path}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    error_msg,
                    extra={"file_path": str(file_path)},
                    exc_info=True
                )

        # Summary
        result = {
            "success": len(errors) == 0,
            "workspace_path": str(workspace_path),
            "files_written": len(files_written),
            "total_atoms": len(atoms),
            "files": files_written,
            "errors": errors if errors else None
        }

        logger.info(
            "File write process completed",
            extra={
                "masterplan_id": str(masterplan_id),
                "files_written": len(files_written),
                "errors": len(errors)
            }
        )

        return result

    def _group_atoms_by_file(
        self,
        atoms: List[AtomicUnit]
    ) -> Dict[str, List[AtomicUnit]]:
        """
        Group atoms by their target file path.

        Args:
            atoms: List of atoms

        Returns:
            Dict mapping file paths to lists of atoms
        """
        files_map = {}

        for atom in atoms:
            # Get file path from atom metadata or task
            file_path = self._get_atom_file_path(atom)

            if file_path not in files_map:
                files_map[file_path] = []

            files_map[file_path].append(atom)

        return files_map

    def _get_atom_file_path(self, atom: AtomicUnit) -> str:
        """
        Determine the file path for an atom using intelligent strategies.

        Priority:
        1. Atom metadata (explicitly set)
        2. Atom file_path field
        3. Task target_files
        4. Parse from code (AST analysis)
        5. Infer from task name/description
        6. Fallback to generic path

        Args:
            atom: Atomic unit

        Returns:
            Relative file path
        """
        # Strategy 1: Explicit metadata
        if atom.metadata and 'file_path' in atom.metadata:
            return atom.metadata['file_path']

        # Strategy 2: Atom file_path field
        if atom.file_path:
            return atom.file_path

        # Strategy 3: Task target_files
        if atom.task and atom.task.target_files:
            return atom.task.target_files[0]

        # Strategy 4: Parse from code (AST analysis)
        if atom.code_to_generate:
            inferred_path = self._infer_path_from_code(atom.code_to_generate, atom.language or 'python')
            if inferred_path:
                return inferred_path

        # Strategy 5: Infer from task name
        if atom.task:
            inferred_path = self._infer_path_from_task(atom.task)
            if inferred_path:
                return inferred_path

        # Strategy 6: Fallback
        logger.warning(f"Could not infer path for atom {atom.atom_id}, using fallback")
        return f"src/generated/atom_{atom.atom_number}.py"

    def _infer_path_from_code(self, code: str, language: str) -> Optional[str]:
        """
        Infer file path from code content using AST analysis.

        Strategies:
        - Check for class definitions → src/models/{class_name}.py
        - Check for FastAPI router → src/api/routers/{router_name}.py
        - Check for service class → src/services/{service_name}.py
        - Check for schema class → src/schemas/{schema_name}.py

        Args:
            code: Source code
            language: Programming language

        Returns:
            Inferred file path or None
        """
        if language != 'python':
            # TODO: Add JS/TS support
            return None

        try:
            tree = ast.parse(code)

            # Look for class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name.lower()

                    # Check for model indicators (SQLAlchemy, Pydantic)
                    bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
                    if any(b in ['BaseModel', 'Base', 'Model'] for b in bases):
                        return f"src/models/{class_name}.py"

                    # Check for service indicators
                    if 'service' in class_name:
                        return f"src/services/{class_name}.py"

                    # Check for schema indicators (Pydantic schemas)
                    if any(keyword in class_name for keyword in ['schema', 'request', 'response', 'create', 'update']):
                        return f"src/schemas/{class_name}.py"

                    # Check for router/endpoint class
                    if 'router' in class_name or 'endpoint' in class_name:
                        return f"src/api/routers/{class_name}.py"

                    # Default: model
                    return f"src/models/{class_name}.py"

                # Look for FastAPI route decorators
                elif isinstance(node, ast.FunctionDef):
                    func_name = node.name.lower()

                    # Check for route decorators (@app.get, @router.post, etc.)
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if isinstance(decorator.func, ast.Attribute):
                                attr = decorator.func.attr
                                if attr in ['get', 'post', 'put', 'delete', 'patch']:
                                    # This is a route handler
                                    return f"src/api/routers/{func_name}_routes.py"

        except SyntaxError:
            # Invalid Python code, skip AST parsing
            logger.debug(f"Failed to parse code for path inference (syntax error)")
            return None
        except Exception as e:
            logger.debug(f"Failed to infer path from code: {e}")
            return None

        return None

    def _infer_path_from_task(self, task) -> Optional[str]:
        """
        Infer file path from task name and description using pattern matching.

        Args:
            task: MasterPlanTask object

        Returns:
            Inferred file path or None
        """
        text = f"{task.name} {task.description}".lower()

        # Model patterns
        model_patterns = [
            (r'create (\w+) model', r'src/models/\1.py'),
            (r'(\w+) database model', r'src/models/\1.py'),
            (r'define (\w+) entity', r'src/models/\1.py'),
            (r'(\w+) table schema', r'src/models/\1.py'),
        ]

        # Service patterns
        service_patterns = [
            (r'create (\w+) service', r'src/services/\1_service.py'),
            (r'(\w+) business logic', r'src/services/\1_service.py'),
            (r'implement (\w+) service', r'src/services/\1_service.py'),
        ]

        # API patterns
        api_patterns = [
            (r'create (\w+) api', r'src/api/routers/\1.py'),
            (r'(\w+) endpoints', r'src/api/routers/\1.py'),
            (r'(\w+) routes', r'src/api/routers/\1.py'),
            (r'(\w+) router', r'src/api/routers/\1.py'),
        ]

        # Schema patterns
        schema_patterns = [
            (r'create (\w+) schema', r'src/schemas/\1_schemas.py'),
            (r'(\w+) validation', r'src/schemas/\1_schemas.py'),
            (r'(\w+) pydantic', r'src/schemas/\1_schemas.py'),
        ]

        # Try all patterns
        all_patterns = model_patterns + service_patterns + api_patterns + schema_patterns

        for pattern, template in all_patterns:
            match = re.search(pattern, text)
            if match:
                # Extract captured group and apply template
                entity_name = match.group(1)
                return template.replace(r'\1', entity_name)

        return None

    def _merge_atoms_to_file(
        self,
        atoms: List[AtomicUnit]
    ) -> str:
        """
        Merge multiple atoms into a single file content.

        Args:
            atoms: List of atoms for the same file

        Returns:
            Complete file content
        """
        # Sort atoms by atom_number to maintain order
        sorted_atoms = sorted(atoms, key=lambda a: a.atom_number)

        # Collect all code snippets
        snippets = []
        for atom in sorted_atoms:
            if atom.code_to_generate:
                snippets.append(atom.code_to_generate)

        # Join with newlines
        file_content = "\n\n".join(snippets)

        return file_content
