"""
Template Generator - TEMPLATE Stratum Implementation

Generates static infrastructure code from pre-tested templates.
NO LLM INVOLVEMENT - deterministic file generation.

Stratum: TEMPLATE (highest trust level)

Phase 0.5.2: Added TEMPLATE_PROTECTED_PATHS and guard_template_paths().
"""

import logging
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import fnmatch

from src.cognitive.patterns.template_patterns import (
    TEMPLATE_PATTERNS,
    TemplatePattern,
    get_template,
    get_template_for_file,
    is_template_file,
)
from src.services.stratum_classification import (
    Stratum,
    classify_file,
    is_llm_allowed,
)


# =============================================================================
# TEMPLATE PROTECTED PATHS - LLM CANNOT WRITE TO THESE (Phase 0.5.2)
# =============================================================================

TEMPLATE_PROTECTED_PATHS: Set[str] = {
    # Infrastructure - NEVER touch
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "prometheus.yml",
    "grafana/",

    # Dependencies - NEVER touch
    "requirements.txt",
    "pyproject.toml",

    # Alembic config - NEVER touch (migrations are AST, not config)
    "alembic.ini",
    "alembic/env.py",

    # Core config - NEVER touch
    "src/core/config.py",
    "src/core/database.py",

    # Health endpoints - NEVER touch
    "src/routes/health.py",
    "src/api/routes/health.py",

    # Base models - NEVER touch
    "src/models/base.py",

    # Main app setup - NEVER touch
    "src/main.py",
    "main.py",

    # Base repository - NEVER touch
    "src/repositories/base.py",
}


class TemplateProtectionError(Exception):
    """Raised when LLM attempts to write to a protected template path."""
    pass


def guard_template_paths(file_path: str, generator: str) -> bool:
    """
    Guard against LLM writing to protected template paths.

    Phase 0.5.2: Explicit protection for infrastructure files.

    Args:
        file_path: Path to the file being written
        generator: The generator type ("template", "ast", "llm")

    Returns:
        True if write is allowed

    Raises:
        TemplateProtectionError: If LLM tries to write to protected path
    """
    if generator != "llm":
        return True  # Only guard LLM

    # Normalize path for comparison
    normalized = file_path.replace("\\", "/")

    for protected in TEMPLATE_PROTECTED_PATHS:
        # Check exact match
        if normalized.endswith(protected):
            raise TemplateProtectionError(
                f"🛡️ BLOCKED: LLM cannot write to protected path '{file_path}'. "
                f"This file belongs to TEMPLATE stratum and must use static templates."
            )

        # Check directory match (for patterns ending with /)
        if protected.endswith("/") and protected[:-1] in normalized:
            raise TemplateProtectionError(
                f"🛡️ BLOCKED: LLM cannot write to protected directory '{file_path}'. "
                f"Files in '{protected}' belong to TEMPLATE stratum."
            )

    return True


def is_template_protected(file_path: str) -> bool:
    """
    Check if a file path is protected (TEMPLATE stratum).

    Args:
        file_path: Path to check

    Returns:
        True if file is protected from LLM
    """
    normalized = file_path.replace("\\", "/")

    for protected in TEMPLATE_PROTECTED_PATHS:
        if normalized.endswith(protected):
            return True
        if protected.endswith("/") and protected[:-1] in normalized:
            return True

    return False

logger = logging.getLogger(__name__)


class TemplateGenerator:
    """
    Generates infrastructure code from static templates.

    TEMPLATE stratum rules:
    - NO LLM calls allowed
    - Code is pre-tested and validated
    - 100% reproducible output
    - Zero variation per project
    """

    def __init__(self):
        self.templates = TEMPLATE_PATTERNS
        self._generated_files: Dict[str, str] = {}

    def generate_all_templates(self, output_dir: str) -> Dict[str, str]:
        """
        Generate all template files for a new project.

        Args:
            output_dir: Base directory for generated files

        Returns:
            Dict mapping file paths to generated content
        """
        generated = {}

        for name, template in self.templates.items():
            file_path = str(Path(output_dir) / template.file_path)
            generated[file_path] = template.code
            logger.info(f"📄 TEMPLATE generated: {template.file_path}")

        self._generated_files = generated
        return generated

    def generate_template(
        self,
        template_name: str,
        output_dir: str
    ) -> Optional[Tuple[str, str]]:
        """
        Generate a single template file.

        Args:
            template_name: Name of template (e.g., 'dockerfile', 'config')
            output_dir: Base directory for generated file

        Returns:
            Tuple of (file_path, content) or None if template not found
        """
        template = get_template(template_name)
        if not template:
            logger.warning(f"Template not found: {template_name}")
            return None

        file_path = str(Path(output_dir) / template.file_path)
        logger.info(f"📄 TEMPLATE generated: {template.file_path}")

        return (file_path, template.code)

    def get_template_for_path(self, file_path: str) -> Optional[str]:
        """
        Get template content for a file path if it's a TEMPLATE stratum file.

        Args:
            file_path: Path to check

        Returns:
            Template content if file is TEMPLATE stratum, None otherwise
        """
        # Check stratum classification
        stratum = classify_file(file_path)
        if stratum != Stratum.TEMPLATE:
            return None

        # Get matching template
        template = get_template_for_file(file_path)
        if template:
            return template.code

        return None

    def should_use_template(self, file_path: str) -> bool:
        """
        Check if a file should be generated from template (not LLM).

        Args:
            file_path: File path to check

        Returns:
            True if file should use TEMPLATE stratum
        """
        return classify_file(file_path) == Stratum.TEMPLATE

    def get_infrastructure_files(self) -> List[str]:
        """
        Get list of all infrastructure file paths.

        Returns:
            List of file paths that belong to TEMPLATE stratum
        """
        return [t.file_path for t in self.templates.values()]

    def validate_template_coverage(
        self,
        required_files: List[str]
    ) -> Dict[str, bool]:
        """
        Validate that all required infrastructure files have templates.

        Args:
            required_files: List of required file paths

        Returns:
            Dict mapping file path to coverage status
        """
        coverage = {}

        for file_path in required_files:
            template = get_template_for_file(file_path)
            coverage[file_path] = template is not None

        covered = sum(1 for v in coverage.values() if v)
        total = len(required_files)

        logger.info(
            f"📊 Template coverage: {covered}/{total} files "
            f"({100*covered/total:.1f}%)"
        )

        return coverage


# =============================================================================
# TEMPLATE-FIRST GENERATION ORCHESTRATOR
# =============================================================================

class StratifiedGenerator:
    """
    Orchestrates code generation using stratified architecture.

    Order of precedence:
    1. TEMPLATE - Use static templates (no LLM)
    2. AST - Use deterministic IR→Code transforms (no LLM)
    3. LLM - Only for complex business logic (constrained)
    """

    def __init__(self):
        self.template_generator = TemplateGenerator()
        self._stratum_stats = {
            Stratum.TEMPLATE: 0,
            Stratum.AST: 0,
            Stratum.LLM: 0,
        }

    def classify_generation_request(
        self,
        file_path: str
    ) -> Tuple[Stratum, Optional[str]]:
        """
        Classify how a file should be generated.

        Args:
            file_path: Target file path

        Returns:
            Tuple of (Stratum, reason)
        """
        stratum = classify_file(file_path)

        reasons = {
            Stratum.TEMPLATE: "Static infrastructure pattern",
            Stratum.AST: "Deterministic from ApplicationIR",
            Stratum.LLM: "Complex business logic",
        }

        return (stratum, reasons.get(stratum))

    def generate_file(
        self,
        file_path: str,
        output_dir: str,
        application_ir: Optional[any] = None,
        llm_context: Optional[Dict] = None,
    ) -> Tuple[str, Stratum]:
        """
        Generate a file using the appropriate stratum.

        Args:
            file_path: Target file path
            output_dir: Output directory
            application_ir: ApplicationIR for AST generation
            llm_context: Context for LLM generation (if needed)

        Returns:
            Tuple of (generated_content, stratum_used)
        """
        stratum = classify_file(file_path)
        self._stratum_stats[stratum] += 1

        if stratum == Stratum.TEMPLATE:
            # TEMPLATE: Use static pattern
            content = self.template_generator.get_template_for_path(file_path)
            if content:
                logger.info(f"📄 TEMPLATE: {file_path}")
                return (content, Stratum.TEMPLATE)
            else:
                logger.warning(
                    f"⚠️ No template for {file_path}, falling back to AST"
                )
                stratum = Stratum.AST

        if stratum == Stratum.AST:
            # AST: Deterministic from IR (placeholder for integration)
            logger.info(f"🔧 AST: {file_path} (requires ApplicationIR)")
            # This will be handled by existing AST generators
            # Return None to signal AST generator should handle it
            return (None, Stratum.AST)

        if stratum == Stratum.LLM:
            # LLM: Check if allowed first
            if not is_llm_allowed(file_path):
                raise ValueError(
                    f"LLM generation not allowed for {file_path}. "
                    f"File matches forbidden pattern."
                )
            logger.info(f"🤖 LLM: {file_path} (constrained generation)")
            # Return None to signal LLM generator should handle it
            return (None, Stratum.LLM)

        raise ValueError(f"Unknown stratum for {file_path}")

    def get_generation_stats(self) -> Dict[str, int]:
        """Get statistics on stratum usage."""
        return {
            "template": self._stratum_stats[Stratum.TEMPLATE],
            "ast": self._stratum_stats[Stratum.AST],
            "llm": self._stratum_stats[Stratum.LLM],
            "total": sum(self._stratum_stats.values()),
        }

    def get_llm_reduction_percentage(self) -> float:
        """Calculate percentage of LLM calls reduced."""
        total = sum(self._stratum_stats.values())
        if total == 0:
            return 0.0

        non_llm = (
            self._stratum_stats[Stratum.TEMPLATE] +
            self._stratum_stats[Stratum.AST]
        )
        return (non_llm / total) * 100


# Singleton instance
_template_generator: Optional[TemplateGenerator] = None
_stratified_generator: Optional[StratifiedGenerator] = None


def get_template_generator() -> TemplateGenerator:
    """Get singleton TemplateGenerator instance."""
    global _template_generator
    if _template_generator is None:
        _template_generator = TemplateGenerator()
    return _template_generator


def get_stratified_generator() -> StratifiedGenerator:
    """Get singleton StratifiedGenerator instance."""
    global _stratified_generator
    if _stratified_generator is None:
        _stratified_generator = StratifiedGenerator()
    return _stratified_generator
