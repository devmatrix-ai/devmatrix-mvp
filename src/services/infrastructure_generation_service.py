"""
Infrastructure Generation Service - MGE V2

Generates complete project infrastructure (Docker, configs, docs) from MasterPlan.

Flow:
1. Detect project type (FastAPI, Node.js, React)
2. Extract metadata (ports, services, dependencies)
3. Generate infrastructure files using string composition
4. Write infrastructure files to workspace

Author: DevMatrix Team
Date: 2025-11-10
"""

import os
import re
import secrets
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import uuid

from src.models import MasterPlan, MasterPlanTask
from src.observability import StructuredLogger

logger = StructuredLogger("infrastructure_generation_service", output_json=True)


class InfrastructureGenerationService:
    """
    Service for generating complete project infrastructure.

    Features:
    - Detects project type from tasks and technologies
    - Extracts project metadata automatically
    - Generates Docker, docker-compose, .env, README, etc.
    - Uses string composition for infrastructure generation
    """

    def __init__(self, db: Session, templates_dir: str = None):
        """
        Initialize infrastructure generation service.

        Args:
            db: Database session
            templates_dir: Path to templates directory (legacy parameter, not used)
        """
        self.db = db

        # Templates directory
        if templates_dir is None:
            # Default to templates/ in project root
            project_root = Path(__file__).parent.parent.parent
            templates_dir = project_root / "templates"

        self.templates_dir = Path(templates_dir)

        logger.info(
            "InfrastructureGenerationService initialized",
            extra={"templates_dir": str(self.templates_dir)}
        )

    async def generate_infrastructure(
        self,
        masterplan_id: uuid.UUID,
        workspace_path: Path
    ) -> Dict[str, Any]:
        """
        Generate ALL infrastructure files for a masterplan.

        Args:
            masterplan_id: MasterPlan UUID
            workspace_path: Path to project workspace

        Returns:
            Dict with generation results
        """
        logger.info(
            "Starting infrastructure generation",
            extra={"masterplan_id": str(masterplan_id)}
        )

        # Load masterplan
        masterplan = self.db.query(MasterPlan).filter(
            MasterPlan.masterplan_id == masterplan_id
        ).first()

        if not masterplan:
            raise ValueError(f"MasterPlan {masterplan_id} not found")

        # Load tasks
        tasks = self.db.query(MasterPlanTask).filter(
            MasterPlanTask.masterplan_id == masterplan_id
        ).all()

        # Detect project type
        project_type = self._detect_project_type(masterplan, tasks)

        logger.info(
            f"Detected project type: {project_type}",
            extra={"project_type": project_type}
        )

        # Extract metadata
        metadata = self._extract_project_metadata(masterplan, tasks, project_type)

        # Generate infrastructure files
        files_generated = []
        errors = []

        try:
            # 1. Dockerfile
            dockerfile_content = self._generate_dockerfile(project_type, metadata)
            dockerfile_path = workspace_path / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content, encoding='utf-8')
            files_generated.append({"file": "Dockerfile", "size": len(dockerfile_content)})

            # 2. docker-compose.yml
            compose_content = self._generate_docker_compose(metadata)
            compose_path = workspace_path / "docker-compose.yml"
            compose_path.write_text(compose_content, encoding='utf-8')
            files_generated.append({"file": "docker-compose.yml", "size": len(compose_content)})

            # 3. .env.example
            env_content = self._generate_env_example(project_type, metadata)
            env_path = workspace_path / ".env.example"
            env_path.write_text(env_content, encoding='utf-8')
            files_generated.append({"file": ".env.example", "size": len(env_content)})

            # 4. .gitignore
            gitignore_content = self._generate_gitignore(project_type)
            gitignore_path = workspace_path / ".gitignore"
            gitignore_path.write_text(gitignore_content, encoding='utf-8')
            files_generated.append({"file": ".gitignore", "size": len(gitignore_content)})

            # 5. requirements.txt / package.json
            deps_content = self._generate_dependencies(project_type, metadata)
            deps_filename = "requirements.txt" if project_type == "fastapi" else "package.json"
            deps_path = workspace_path / deps_filename
            deps_path.write_text(deps_content, encoding='utf-8')
            files_generated.append({"file": deps_filename, "size": len(deps_content)})

            # 6. README.md
            readme_content = self._generate_readme(masterplan, metadata)
            readme_path = workspace_path / "README.md"
            readme_path.write_text(readme_content, encoding='utf-8')
            files_generated.append({"file": "README.md", "size": len(readme_content)})

        except Exception as e:
            error_msg = f"Failed to generate infrastructure: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg, exc_info=True)

        # Summary
        result = {
            "success": len(errors) == 0,
            "project_type": project_type,
            "files_generated": len(files_generated),
            "files": files_generated,
            "errors": errors if errors else None
        }

        logger.info(
            "Infrastructure generation completed",
            extra={
                "masterplan_id": str(masterplan_id),
                "files_generated": len(files_generated),
                "errors": len(errors)
            }
        )

        return result

    def _detect_project_type(
        self,
        masterplan: MasterPlan,
        tasks: List[MasterPlanTask]
    ) -> str:
        """
        Detect project type from tasks and descriptions.

        Args:
            masterplan: MasterPlan object
            tasks: List of tasks

        Returns:
            Project type: "fastapi", "express", "react", "nextjs", etc.
        """
        # Combine all text for analysis
        text = f"{masterplan.project_name} {masterplan.description or ''}"

        for task in tasks:
            text += f" {task.name} {task.description}"

        text = text.lower()

        # Detection patterns
        if any(keyword in text for keyword in ["fastapi", "uvicorn", "pydantic", "sqlalchemy", "alembic"]):
            return "fastapi"
        elif any(keyword in text for keyword in ["express", "node.js", "nodejs", "npm"]):
            return "express"
        elif any(keyword in text for keyword in ["react", "jsx", "tsx", "vite"]):
            return "react"
        elif any(keyword in text for keyword in ["next.js", "nextjs"]):
            return "nextjs"

        # Default to FastAPI if Python-related
        if "python" in text or any(".py" in task.name.lower() for task in tasks):
            return "fastapi"

        # Default to Express if JavaScript-related
        if "javascript" in text or "js" in text:
            return "express"

        # Final fallback
        return "fastapi"

    def _extract_project_metadata(
        self,
        masterplan: MasterPlan,
        tasks: List[MasterPlanTask],
        project_type: str
    ) -> Dict[str, Any]:
        """
        Extract project metadata for template rendering.

        Args:
            masterplan: MasterPlan object
            tasks: List of tasks
            project_type: Detected project type

        Returns:
            Metadata dictionary
        """
        # Project basics
        project_name = masterplan.project_name
        project_slug = project_name.lower().replace(" ", "-")
        project_description = masterplan.description or f"A {project_type} application"

        # Ports
        app_port = 8000 if project_type == "fastapi" else 3000
        db_port = 5432
        redis_port = 6379

        # Database
        db_user = "app_user"
        db_password = secrets.token_hex(16)
        db_name = project_slug.replace("-", "_")

        # Detect if Redis is needed
        text = f"{masterplan.project_name} {masterplan.description or ''}"
        for task in tasks:
            text += f" {task.name} {task.description}"
        text = text.lower()

        needs_redis = any(keyword in text for keyword in ["redis", "cache", "caching", "session"])

        # Extract API endpoints from tasks
        api_endpoints = self._extract_api_endpoints(tasks)

        # Custom environment variables
        custom_env_vars = []

        metadata = {
            "project_name": project_name,
            "project_slug": project_slug,
            "project_description": project_description,
            "project_type": project_type,
            "app_port": app_port,
            "db_port": db_port,
            "redis_port": redis_port,
            "db_user": db_user,
            "db_password": db_password,
            "db_name": db_name,
            "needs_redis": needs_redis,
            "has_init_script": False,  # Could be extended to detect migration scripts
            "api_endpoints": api_endpoints,
            "custom_env_vars": custom_env_vars
        }

        return metadata

    def _extract_api_endpoints(self, tasks: List[MasterPlanTask]) -> List[Dict]:
        """
        Extract API endpoints from task descriptions.

        Args:
            tasks: List of tasks

        Returns:
            List of endpoint categories with routes
        """
        endpoints = []

        # Common endpoint patterns
        patterns = {
            "Authentication": ["auth", "login", "register", "token"],
            "Users": ["user", "profile", "account"],
            "Items": ["item", "todo", "task", "product"],
        }

        for category, keywords in patterns.items():
            routes = []

            for task in tasks:
                task_text = f"{task.name} {task.description}".lower()

                if any(kw in task_text for kw in keywords):
                    # Try to extract HTTP methods
                    if "create" in task_text or "post" in task_text:
                        method = "POST"
                        action = "Create"
                    elif "get" in task_text or "list" in task_text or "retrieve" in task_text:
                        method = "GET"
                        action = "Get"
                    elif "update" in task_text or "put" in task_text or "patch" in task_text:
                        method = "PUT"
                        action = "Update"
                    elif "delete" in task_text:
                        method = "DELETE"
                        action = "Delete"
                    else:
                        continue

                    route_name = keywords[0]
                    routes.append({
                        "method": method,
                        "path": f"/api/v1/{route_name}s",
                        "description": f"{action} {route_name}"
                    })

            if routes:
                endpoints.append({
                    "category": category,
                    "routes": routes
                })

        return endpoints

    def _generate_dockerfile(self, project_type: str, metadata: Dict) -> str:
        """
        Generate Dockerfile content.

        Args:
            project_type: Type of project
            metadata: Project metadata

        Returns:
            Dockerfile content
        """
        template_name = f"docker/python_{project_type}.dockerfile"

        try:
            # Template rendering disabled (templates directory removed)
            # Using default fallback template
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.warning(f"Template {template_name} not found, using default")
            # Fallback template
            return f"""FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE {metadata['app_port']}

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "{metadata['app_port']}"]
"""

    def _generate_docker_compose(self, metadata: Dict) -> str:
        """
        Generate docker-compose.yml content.

        Args:
            metadata: Project metadata

        Returns:
            docker-compose.yml content
        """
        template_name = "docker/docker-compose.yml.j2"

        try:
            # Template rendering disabled (templates directory removed)
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.error(f"Failed to render docker-compose template: {e}")
            raise

    def _generate_env_example(self, project_type: str, metadata: Dict) -> str:
        """
        Generate .env.example content.

        Args:
            project_type: Type of project
            metadata: Project metadata

        Returns:
            .env.example content
        """
        template_name = f"config/env_{project_type}.example.j2"

        try:
            # Template rendering disabled (templates directory removed)
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.error(f"Failed to render .env.example template: {e}")
            raise

    def _generate_gitignore(self, project_type: str) -> str:
        """
        Generate .gitignore content.

        Args:
            project_type: Type of project

        Returns:
            .gitignore content
        """
        template_name = "git/gitignore_python.txt"

        try:
            # Template rendering disabled (templates directory removed)
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.error(f"Failed to render .gitignore template: {e}")
            raise

    def _generate_dependencies(self, project_type: str, metadata: Dict) -> str:
        """
        Generate dependencies file (requirements.txt or package.json).

        Args:
            project_type: Type of project
            metadata: Project metadata

        Returns:
            Dependencies file content
        """
        if project_type == "fastapi":
            template_name = "config/requirements_fastapi.txt.j2"
        else:
            template_name = "config/package_express.json.j2"

        try:
            # Template rendering disabled (templates directory removed)
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.error(f"Failed to render dependencies template: {e}")
            raise

    def _generate_readme(self, masterplan: MasterPlan, metadata: Dict) -> str:
        """
        Generate README.md content.

        Args:
            masterplan: MasterPlan object
            metadata: Project metadata

        Returns:
            README.md content
        """
        template_name = f"git/README_{metadata['project_type']}.md.j2"

        try:
            # Template rendering disabled (templates directory removed)
            raise FileNotFoundError(f"Templates not available: {template_name}")
        except Exception as e:
            logger.error(f"Failed to render README template: {e}")
            raise
