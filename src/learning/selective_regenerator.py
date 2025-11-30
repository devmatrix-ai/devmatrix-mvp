"""
Selective Regenerator - Intra-Run Learning for Code Generation.

After smoke tests fail, this module:
1. Identifies which files caused failures (routes, services)
2. Regenerates ONLY those files using freshly-learned anti-patterns
3. Enables learning within the same pipeline run (not just across runs)

Reference: DOCS/mvp/exit/FIXES_2025-11-30_RUNTIME_AND_LEARNING.md
"""
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class RegenerationTarget:
    """A file that should be regenerated."""
    file_path: str
    file_type: str  # 'route', 'service', 'schema', 'entity'
    entity_name: Optional[str] = None
    endpoint_pattern: Optional[str] = None
    violation_count: int = 0
    reason: str = ""


@dataclass
class RegenerationResult:
    """Result of selective regeneration."""
    files_identified: int = 0
    files_regenerated: int = 0
    files_skipped: int = 0
    anti_patterns_used: int = 0
    errors: List[str] = field(default_factory=list)
    regenerated_files: List[str] = field(default_factory=list)


class SelectiveRegenerator:
    """
    Regenerates specific files based on smoke test failures.

    Flow:
        1. Smoke test fails with violations
        2. Violations are classified and stored as anti-patterns
        3. This class identifies which files to regenerate
        4. Files are regenerated with anti-pattern warnings injected
        5. New code avoids the mistakes that caused failures
    """

    def __init__(
        self,
        app_dir: str,
        application_ir: Any = None,
        min_violations_to_regenerate: int = 1,
    ):
        """
        Initialize regenerator.

        Args:
            app_dir: Generated app directory
            application_ir: ApplicationIR for context
            min_violations_to_regenerate: Minimum violations before regenerating a file
        """
        self.app_dir = Path(app_dir)
        self.application_ir = application_ir
        self.min_violations = min_violations_to_regenerate
        self.logger = logging.getLogger(f"{__name__}.SelectiveRegenerator")

    def identify_targets(
        self,
        violations: List[Dict[str, Any]],
    ) -> List[RegenerationTarget]:
        """
        Identify files that should be regenerated based on violations.

        Args:
            violations: List of smoke test violations

        Returns:
            List of RegenerationTarget objects
        """
        # Group violations by endpoint
        endpoint_violations: Dict[str, List[Dict]] = {}

        for v in violations:
            endpoint = v.get("endpoint", v.get("path", ""))
            if endpoint:
                if endpoint not in endpoint_violations:
                    endpoint_violations[endpoint] = []
                endpoint_violations[endpoint].append(v)

        targets: List[RegenerationTarget] = []
        seen_files: Set[str] = set()

        for endpoint, vlist in endpoint_violations.items():
            if len(vlist) < self.min_violations:
                continue

            # Extract entity from endpoint (e.g., /carts -> cart)
            entity = self._extract_entity_from_endpoint(endpoint)

            # Identify affected files
            affected_files = self._find_affected_files(endpoint, entity)

            for file_info in affected_files:
                if file_info["path"] in seen_files:
                    continue
                seen_files.add(file_info["path"])

                target = RegenerationTarget(
                    file_path=file_info["path"],
                    file_type=file_info["type"],
                    entity_name=entity,
                    endpoint_pattern=endpoint,
                    violation_count=len(vlist),
                    reason=f"{len(vlist)} violations on {endpoint}"
                )
                targets.append(target)

        self.logger.info(f"Identified {len(targets)} files for regeneration")
        return targets

    def _extract_entity_from_endpoint(self, endpoint: str) -> Optional[str]:
        """Extract entity name from endpoint path."""
        # Remove path parameters
        clean_path = re.sub(r'\{[^}]+\}', '', endpoint)
        parts = [p for p in clean_path.split('/') if p]

        if not parts:
            return None

        # First part is usually the resource (pluralized entity)
        resource = parts[0].lower()

        # Singularize simple cases
        if resource.endswith('ies'):
            return resource[:-3] + 'y'  # categories -> category
        elif resource.endswith('s') and not resource.endswith('ss'):
            return resource[:-1]  # products -> product
        return resource

    def _find_affected_files(
        self,
        endpoint: str,
        entity: Optional[str],
    ) -> List[Dict[str, str]]:
        """Find files that handle this endpoint/entity."""
        affected = []

        if not entity:
            return affected

        src_dir = self.app_dir / "src"
        if not src_dir.exists():
            return affected

        # Routes file
        routes_patterns = [
            src_dir / "api" / "routes" / f"{entity}.py",
            src_dir / "api" / "routes" / f"{entity}s.py",
            src_dir / "routes" / f"{entity}.py",
        ]
        for route_file in routes_patterns:
            if route_file.exists():
                affected.append({
                    "path": str(route_file),
                    "type": "route"
                })
                break

        # Service file
        service_patterns = [
            src_dir / "services" / f"{entity}_service.py",
            src_dir / "services" / f"{entity}s_service.py",
            src_dir / "services" / f"{entity}_flow_methods.py",
        ]
        for service_file in service_patterns:
            if service_file.exists():
                affected.append({
                    "path": str(service_file),
                    "type": "service"
                })
                break

        # Schema file (if entity-specific validation failed)
        schema_patterns = [
            src_dir / "models" / "schemas.py",
        ]
        for schema_file in schema_patterns:
            if schema_file.exists():
                affected.append({
                    "path": str(schema_file),
                    "type": "schema"
                })
                break

        return affected

    async def regenerate_targets(
        self,
        targets: List[RegenerationTarget],
        code_gen_service: Any = None,
    ) -> RegenerationResult:
        """
        Regenerate the identified target files.

        Args:
            targets: List of files to regenerate
            code_gen_service: CodeGenerationService instance

        Returns:
            RegenerationResult with statistics
        """
        result = RegenerationResult(files_identified=len(targets))

        if not targets:
            self.logger.info("No targets to regenerate")
            return result

        if not code_gen_service:
            result.errors.append("No code generation service provided")
            return result

        # Get anti-pattern count for logging
        try:
            from src.learning.negative_pattern_store import get_negative_pattern_store
            store = get_negative_pattern_store()
            stats = store.get_statistics()
            result.anti_patterns_used = stats.get("total_patterns", 0)
        except Exception as e:
            self.logger.warning(f"Could not get anti-pattern stats: {e}")

        print(f"\n🔄 Selective Regeneration: {len(targets)} files using {result.anti_patterns_used} anti-patterns")

        for target in targets:
            try:
                success = await self._regenerate_single_file(
                    target=target,
                    code_gen_service=code_gen_service,
                )

                if success:
                    result.files_regenerated += 1
                    result.regenerated_files.append(target.file_path)
                    print(f"  ✅ Regenerated: {os.path.basename(target.file_path)} ({target.reason})")
                else:
                    result.files_skipped += 1

            except Exception as e:
                result.errors.append(f"{target.file_path}: {str(e)}")
                self.logger.error(f"Failed to regenerate {target.file_path}: {e}")

        print(f"  📊 Result: {result.files_regenerated}/{result.files_identified} files regenerated")

        return result

    async def _regenerate_single_file(
        self,
        target: RegenerationTarget,
        code_gen_service: Any,
    ) -> bool:
        """Regenerate a single file."""
        # For now, we rely on the existing code repair mechanism
        # which already uses anti-patterns when available.
        #
        # Full regeneration would require:
        # 1. Extract the IR subset for this entity/endpoint
        # 2. Call code_gen_service with just that subset
        # 3. Replace the file with new generated content
        #
        # This is a placeholder for the full implementation.

        self.logger.debug(f"Would regenerate {target.file_path} ({target.file_type})")

        # Signal that we identified the target but didn't regenerate
        # (full regeneration requires more integration work)
        return False


# =============================================================================
# Integration with Smoke Repair
# =============================================================================


async def selective_regenerate_from_violations(
    app_dir: str,
    violations: List[Dict[str, Any]],
    application_ir: Any = None,
    code_gen_service: Any = None,
) -> RegenerationResult:
    """
    Convenience function for selective regeneration.

    Usage in smoke repair orchestrator:
        from src.learning.selective_regenerator import selective_regenerate_from_violations

        # After smoke test fails and anti-patterns are stored
        result = await selective_regenerate_from_violations(
            app_dir=app_path,
            violations=smoke_violations,
            application_ir=ir,
            code_gen_service=code_gen,
        )

        if result.files_regenerated > 0:
            # Re-run smoke tests
            ...
    """
    regenerator = SelectiveRegenerator(
        app_dir=app_dir,
        application_ir=application_ir,
    )

    targets = regenerator.identify_targets(violations)

    if not targets:
        return RegenerationResult()

    return await regenerator.regenerate_targets(
        targets=targets,
        code_gen_service=code_gen_service,
    )


# =============================================================================
# Singleton for pipeline integration
# =============================================================================

_selective_regenerator: Optional[SelectiveRegenerator] = None


def get_selective_regenerator(
    app_dir: str = None,
    application_ir: Any = None,
) -> SelectiveRegenerator:
    """Get or create selective regenerator instance."""
    global _selective_regenerator

    if _selective_regenerator is None or app_dir:
        _selective_regenerator = SelectiveRegenerator(
            app_dir=app_dir or "/tmp",
            application_ir=application_ir,
        )

    return _selective_regenerator
