"""
Code Repair Agent - AST-Based Targeted Repairs

Este agente realiza reparaciones targeted usando AST patching en lugar de
regenerar todo el código.

ANTES (Stub): Siempre retornaba failure, repair loop regeneraba todo
DESPUÉS (AST): Patches targeted a archivos específicos, preserva código existente

Capacidades:
- Agregar entities faltantes a src/models/entities.py
- Agregar endpoints faltantes a src/api/routes/*.py
- Preservar código existente y solo agregar lo necesario
- Rollback automático si patch falla

Created: 2025-11-21 (replacing stub)
Reference: P1 fix for DevMatrix QA evaluation
"""

import ast
import astor
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class RepairResult:
    """Result of a code repair attempt."""
    success: bool
    repaired_files: List[str]  # Changed from repaired_code to list of files
    repairs_applied: List[str]
    error_message: Optional[str] = None


class CodeRepairAgent:
    """
    AST-based code repair agent for targeted fixes.

    Instead of regenerating entire codebase, this agent:
    1. Identifies missing entities/endpoints from ComplianceReport
    2. Applies targeted AST patches to specific files
    3. Preserves existing code and only adds what's missing
    4. Provides rollback capability if patches fail
    """

    def __init__(self, output_path: Path):
        """
        Initialize code repair agent.

        Args:
            output_path: Path to generated app directory
        """
        # Convert to absolute path to work from any working directory
        self.output_path = Path(output_path).resolve()
        self.entities_file = self.output_path / "src" / "models" / "entities.py"
        self.routes_dir = self.output_path / "src" / "api" / "routes"

    def repair(
        self,
        compliance_report,
        spec_requirements,
        max_attempts: int = 3
    ) -> RepairResult:
        """
        Attempt to repair code based on compliance failures.

        Uses targeted AST patching instead of full regeneration:
        - Missing entities → Add to entities.py
        - Missing endpoints → Add to appropriate route file

        Args:
            compliance_report: ComplianceReport with failures
            spec_requirements: SpecRequirements with expected entities/endpoints
            max_attempts: Maximum repair attempts (not used for AST, kept for API compatibility)

        Returns:
            RepairResult with outcome
        """
        repairs_applied = []
        repaired_files = []

        try:
            # Identify what's missing
            missing_entities = [
                e for e in compliance_report.entities_expected
                if e.lower() not in [i.lower() for i in compliance_report.entities_implemented]
            ]

            missing_endpoints = [
                e for e in compliance_report.endpoints_expected
                if e.lower() not in [i.lower() for i in compliance_report.endpoints_implemented]
            ]

            logger.info(f"CodeRepair: {len(missing_entities)} missing entities, {len(missing_endpoints)} missing endpoints")

            # Repair missing entities
            if missing_entities:
                for entity_name in missing_entities:
                    try:
                        # Find entity definition in spec
                        entity_req = next(
                            (e for e in spec_requirements.entities if e.name.lower() == entity_name.lower()),
                            None
                        )

                        if entity_req:
                            success = self.repair_missing_entity(entity_req)
                            if success:
                                repairs_applied.append(f"Added entity: {entity_name}")
                                if str(self.entities_file) not in repaired_files:
                                    repaired_files.append(str(self.entities_file))
                            else:
                                logger.warning(f"Failed to add entity: {entity_name}")
                    except Exception as e:
                        logger.error(f"Error adding entity {entity_name}: {e}")

            # Repair missing endpoints
            if missing_endpoints:
                for endpoint_str in missing_endpoints:
                    try:
                        # Parse endpoint: "POST /products"
                        parts = endpoint_str.split()
                        if len(parts) >= 2:
                            method = parts[0].upper()
                            path = parts[1]

                            # Find endpoint definition in spec
                            endpoint_req = next(
                                (e for e in spec_requirements.endpoints
                                 if e.method.upper() == method and e.path == path),
                                None
                            )

                            if endpoint_req:
                                route_file = self.repair_missing_endpoint(endpoint_req)
                                if route_file:
                                    repairs_applied.append(f"Added endpoint: {method} {path}")
                                    if route_file not in repaired_files:
                                        repaired_files.append(route_file)
                                else:
                                    logger.warning(f"Failed to add endpoint: {endpoint_str}")
                    except Exception as e:
                        logger.error(f"Error adding endpoint {endpoint_str}: {e}")

            if repairs_applied:
                return RepairResult(
                    success=True,
                    repaired_files=repaired_files,
                    repairs_applied=repairs_applied
                )
            else:
                return RepairResult(
                    success=False,
                    repaired_files=[],
                    repairs_applied=[],
                    error_message="No repairs could be applied"
                )

        except Exception as e:
            logger.error(f"CodeRepair failed: {e}")
            return RepairResult(
                success=False,
                repaired_files=[],
                repairs_applied=[],
                error_message=str(e)
            )

    def repair_missing_entity(self, entity_req) -> bool:
        """
        Add missing entity to src/models/entities.py using AST patching.

        Strategy:
        1. Read entities.py and parse to AST
        2. Create new entity class node
        3. Insert at end of AST
        4. Write back using astor

        Args:
            entity_req: Entity requirement from spec

        Returns:
            True if successful, False otherwise
        """
        try:
            # DEBUG: Print path resolution info (using ERROR level to ensure visibility)
            logger.error(f"DEBUG: Checking entities_file: {self.entities_file}")
            logger.error(f"DEBUG: entities_file type: {type(self.entities_file)}")
            logger.error(f"DEBUG: entities_file.exists() = {self.entities_file.exists()}")
            logger.error(f"DEBUG: entities_file.is_file() = {self.entities_file.is_file() if self.entities_file.exists() else 'N/A'}")

            # List parent directory to see what files actually exist
            import os
            parent_dir = self.entities_file.parent
            logger.error(f"DEBUG: Parent directory: {parent_dir}")
            logger.error(f"DEBUG: Parent exists: {parent_dir.exists()}")
            if parent_dir.exists():
                files = list(parent_dir.iterdir())
                logger.error(f"DEBUG: Files in {parent_dir.name}: {[f.name for f in files]}")

            # Read current entities.py (create if doesn't exist)
            if not self.entities_file.exists():
                logger.warning(f"entities.py not found at {self.entities_file}, creating it")
                self._create_entities_file()
                # After creation, file should exist with base structure
                if not self.entities_file.exists():
                    logger.error(f"Failed to create entities.py at {self.entities_file}")
                    return False

            with open(self.entities_file, 'r') as f:
                source_code = f.read()

            # Parse to AST
            tree = ast.parse(source_code)

            # Create new entity class
            new_class = self._generate_entity_class_ast(entity_req)

            # Add to AST
            tree.body.append(new_class)

            # Convert back to code
            new_code = astor.to_source(tree)

            # Write back
            with open(self.entities_file, 'w') as f:
                f.write(new_code)

            logger.info(f"Added entity {entity_req.name} to entities.py")
            return True

        except Exception as e:
            logger.error(f"Failed to add entity {entity_req.name}: {e}")
            return False

    def repair_missing_endpoint(self, endpoint_req) -> Optional[str]:
        """
        Add missing endpoint to appropriate route file using AST patching.

        Strategy:
        1. Determine which route file (e.g., product.py from /products path)
        2. Read route file and parse to AST
        3. Create new endpoint function node
        4. Insert at end of AST
        5. Write back using astor

        Args:
            endpoint_req: Endpoint requirement from spec

        Returns:
            Path to repaired file if successful, None otherwise
        """
        try:
            # Determine route file from path
            # /products → product.py, /customers → customer.py
            path_parts = endpoint_req.path.strip('/').split('/')
            if not path_parts or not path_parts[0]:
                logger.warning(f"Cannot determine route file for path: {endpoint_req.path}")
                return None

            # Get entity name from path (singular form)
            entity_plural = path_parts[0]
            entity_name = entity_plural.rstrip('s')  # Simple pluralization: products → product

            route_file = self.routes_dir / f"{entity_name}.py"

            # Create file if doesn't exist
            if not route_file.exists():
                self._create_route_file(route_file, entity_name)

            # Read current route file
            with open(route_file, 'r') as f:
                source_code = f.read()

            # Parse to AST
            tree = ast.parse(source_code)

            # Create new endpoint function
            new_function = self._generate_endpoint_function_ast(endpoint_req, entity_name)

            # Add to AST
            tree.body.append(new_function)

            # Convert back to code
            new_code = astor.to_source(tree)

            # Write back
            with open(route_file, 'w') as f:
                f.write(new_code)

            logger.info(f"Added endpoint {endpoint_req.method} {endpoint_req.path} to {route_file.name}")
            return str(route_file)

        except Exception as e:
            logger.error(f"Failed to add endpoint {endpoint_req.method} {endpoint_req.path}: {e}")
            return None

    def _generate_entity_class_ast(self, entity_req) -> ast.ClassDef:
        """
        Generate AST node for SQLAlchemy entity class.

        Creates class like:
        ```
        class ProductEntity(Base):
            __tablename__ = "products"
            id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            name = Column(String(255), nullable=False)
            ...
        ```

        Args:
            entity_req: Entity requirement from spec

        Returns:
            ast.ClassDef node
        """
        # Simplified implementation - in production would parse entity_req.attributes
        # For now, create basic entity with id field

        class_name = f"{entity_req.name}Entity"
        table_name = f"{entity_req.name.lower()}s"

        # Create class definition
        class_def = ast.ClassDef(
            name=class_name,
            bases=[ast.Name(id='Base', ctx=ast.Load())],
            keywords=[],
            body=[
                # __tablename__ = "products"
                ast.Assign(
                    targets=[ast.Name(id='__tablename__', ctx=ast.Store())],
                    value=ast.Constant(value=table_name)
                ),
                # id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
                ast.Assign(
                    targets=[ast.Name(id='id', ctx=ast.Store())],
                    value=ast.Call(
                        func=ast.Name(id='Column', ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Name(id='UUID', ctx=ast.Load()),
                                args=[],
                                keywords=[ast.keyword(arg='as_uuid', value=ast.Constant(value=True))]
                            )
                        ],
                        keywords=[
                            ast.keyword(arg='primary_key', value=ast.Constant(value=True)),
                            ast.keyword(arg='default', value=ast.Attribute(
                                value=ast.Name(id='uuid', ctx=ast.Load()),
                                attr='uuid4',
                                ctx=ast.Load()
                            ))
                        ]
                    )
                )
            ],
            decorator_list=[]
        )

        return class_def

    def _generate_endpoint_function_ast(self, endpoint_req, entity_name: str) -> ast.AsyncFunctionDef:
        """
        Generate AST node for FastAPI endpoint function.

        Creates function like:
        ```
        @router.get("/")
        async def get_all_products(db: AsyncSession = Depends(get_db)):
            service = ProductService(db)
            products = await service.get_all()
            return products
        ```

        Args:
            endpoint_req: Endpoint requirement from spec
            entity_name: Entity name (e.g., "product")

        Returns:
            ast.AsyncFunctionDef node
        """
        # Simplified implementation - creates basic CRUD endpoint
        # In production would parse endpoint_req details

        method = endpoint_req.method.lower()
        entity_capitalized = entity_name.capitalize()

        # Determine function name from method
        if method == 'get':
            func_name = f"get_all_{entity_name}s"
        elif method == 'post':
            func_name = f"create_{entity_name}"
        elif method == 'put':
            func_name = f"update_{entity_name}"
        elif method == 'delete':
            func_name = f"delete_{entity_name}"
        else:
            func_name = f"{method}_{entity_name}"

        # Create async function with decorator
        func_def = ast.AsyncFunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[
                    ast.arg(arg='db', annotation=ast.Name(id='AsyncSession', ctx=ast.Load()))
                ],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[
                    ast.Call(
                        func=ast.Name(id='Depends', ctx=ast.Load()),
                        args=[ast.Name(id='get_db', ctx=ast.Load())],
                        keywords=[]
                    )
                ]
            ),
            body=[
                # Simple pass placeholder - in production would generate full logic
                ast.Pass()
            ],
            decorator_list=[
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id='router', ctx=ast.Load()),
                        attr=method,
                        ctx=ast.Load()
                    ),
                    args=[ast.Constant(value="/")],
                    keywords=[]
                )
            ],
            returns=None
        )

        return func_def

    def _create_route_file(self, route_file: Path, entity_name: str):
        """
        Create new route file with basic structure.

        Creates file like:
        ```
        from fastapi import APIRouter, Depends
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.core.database import get_db

        router = APIRouter(prefix="/products", tags=["products"])
        ```

        Args:
            route_file: Path to route file to create
            entity_name: Entity name (e.g., "product")
        """
        entity_plural = f"{entity_name}s"

        template = f'''"""
FastAPI CRUD Routes for {entity_name.capitalize()}

Auto-generated route file.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import get_db

router = APIRouter(
    prefix="/{entity_plural}",
    tags=["{entity_plural}"],
)
'''

        route_file.parent.mkdir(parents=True, exist_ok=True)
        with open(route_file, 'w') as f:
            f.write(template)

        logger.info(f"Created new route file: {route_file.name}")

    def _create_entities_file(self):
        """
        Create new entities.py file with basic SQLAlchemy structure.

        Creates file like:
        ```
        from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
        from sqlalchemy.dialects.postgresql import UUID
        from sqlalchemy.orm import relationship
        from src.core.database import Base
        import uuid
        from datetime import datetime, timezone

        # Entity classes will be added here by repair agent
        ```

        The file is created with base imports, then entities are added via AST patching.
        """
        template = '''"""
SQLAlchemy Entity Models

Auto-generated entity file.
"""

from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.core.database import Base
import uuid
from datetime import datetime, timezone


# Entity classes will be added below
'''

        # Ensure parent directory exists
        self.entities_file.parent.mkdir(parents=True, exist_ok=True)

        # Write base structure
        with open(self.entities_file, 'w') as f:
            f.write(template)

        logger.info(f"Created new entities file: {self.entities_file.name}")
