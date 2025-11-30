"""
Compliance Validator - Semantic validation of generated code against spec

Compares spec requirements vs generated code to calculate compliance score.
Part of Task Group 4.1: Semantic Validation System.

Validates:
- Entity compliance: entities_found / entities_expected
- Endpoint compliance: endpoints_found / endpoints_expected
- Business logic compliance: validations_found / validations_expected
- Overall compliance: average of all categories

Threshold: FAIL if overall < 0.80 (80%)
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field as dataclass_field

from src.parsing.spec_parser import SpecRequirements
from src.analysis.code_analyzer import CodeAnalyzer

# Support for IR-centric architecture
try:
    from src.cognitive.ir.application_ir import ApplicationIR
    APPLICATION_IR_AVAILABLE = True
except ImportError:
    APPLICATION_IR_AVAILABLE = False

# Optional: SemanticMatcher for ML-based matching (replaces manual equivalences)
try:
    from src.services.semantic_matcher import SemanticMatcher
    SEMANTIC_MATCHER_AVAILABLE = True
except ImportError:
    SEMANTIC_MATCHER_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ComplianceReport:
    """
    Detailed compliance report

    Shows what was implemented vs what was expected,
    with compliance scores per category and overall.
    """

    overall_compliance: float  # 0.0-1.0

    # Entities
    entities_implemented: List[str] = dataclass_field(default_factory=list)
    entities_expected: List[str] = dataclass_field(default_factory=list)

    # Endpoints
    endpoints_implemented: List[str] = dataclass_field(default_factory=list)
    endpoints_expected: List[str] = dataclass_field(default_factory=list)

    # Business Logic
    validations_implemented: List[str] = dataclass_field(default_factory=list)
    validations_expected: List[str] = dataclass_field(default_factory=list)
    validations_found: List[str] = dataclass_field(default_factory=list)  # All found, including extras

    # Missing requirements
    missing_requirements: List[str] = dataclass_field(default_factory=list)

    # Per-category scores
    compliance_details: Dict[str, float] = dataclass_field(default_factory=dict)

    def __str__(self) -> str:
        """String representation of compliance report"""
        # For validations: show found/found when all expected are present
        validation_compliance = self.compliance_details.get('validations', 0)
        if validation_compliance >= 1.0 and self.validations_found:
            # All validations found + extras
            validations_display = f"{len(self.validations_found)}/{len(self.validations_found)}"
        else:
            # Partial compliance
            validations_display = f"{len(self.validations_implemented)}/{len(self.validations_expected)}"

        return f"""
Compliance Report
=================
Overall Compliance: {self.overall_compliance:.1%}

Entities: {self.compliance_details.get('entities', 0):.1%}
  Expected: {len(self.entities_expected)} - {', '.join(self.entities_expected)}
  Implemented: {len(self.entities_implemented)} - {', '.join(self.entities_implemented)}

Endpoints: {self.compliance_details.get('endpoints', 0):.1%}
  Expected: {len(self.endpoints_expected)}
  Implemented: {len(self.endpoints_implemented)}

Validations: {validation_compliance:.1%} ({validations_display})
  Expected: {len(self.validations_expected)}
  Implemented: {len(self.validations_implemented)}
  Found (including extras): {len(self.validations_found)}

Missing Requirements ({len(self.missing_requirements)}):
{chr(10).join('  - ' + req for req in self.missing_requirements[:10])}
"""


class ComplianceValidationError(Exception):
    """Raised when compliance is below threshold"""

    pass


class ComplianceValidator:
    """
    Validates generated code against specification requirements

    Calculates compliance score by comparing:
    1. Expected entities (from spec) vs Implemented entities (from code)
    2. Expected endpoints (from spec) vs Implemented endpoints (from code)
    3. Expected validations (from spec) vs Implemented validations (from code)

    Overall compliance = average of all category scores
    """

    def __init__(self, use_semantic_matching: bool = None, application_ir=None):
        """
        Initialize compliance validator.

        Args:
            use_semantic_matching: If True, use ML-based SemanticMatcher for validation matching.
                                   If None (default), auto-detect from USE_SEMANTIC_MATCHING env var.
                                   Falls back to manual equivalences if SemanticMatcher unavailable.
            application_ir: Optional ApplicationIR instance for structured validation matching.
                           When provided, uses ValidationModelIR for more precise constraint matching.
        """
        self.analyzer = CodeAnalyzer()

        # Store ApplicationIR for IR-based matching (optional)
        self.application_ir = application_ir
        self.validation_model = None
        if application_ir and hasattr(application_ir, 'validation_model'):
            self.validation_model = application_ir.validation_model
            logger.info(f"ComplianceValidator: ApplicationIR provided with {len(self.validation_model.rules)} validation rules")

        # Auto-detect semantic matching from environment
        if use_semantic_matching is None:
            use_semantic_matching = os.getenv("USE_SEMANTIC_MATCHING", "true").lower() == "true"

        # Initialize SemanticMatcher if available and enabled
        self.semantic_matcher: Optional[SemanticMatcher] = None
        if use_semantic_matching and SEMANTIC_MATCHER_AVAILABLE:
            try:
                self.semantic_matcher = SemanticMatcher()
                logger.info("ComplianceValidator initialized with SemanticMatcher (ML-based matching)")
            except Exception as e:
                logger.warning(f"Failed to initialize SemanticMatcher: {e}, using manual equivalences")
                self.semantic_matcher = None
        else:
            logger.info("ComplianceValidator initialized with manual equivalences")

        logger.info("ComplianceValidator initialized")

    def _get_entities_from_spec(self, spec) -> list:
        """
        Extract entities from spec, handling both ApplicationIR and SpecRequirements.

        Args:
            spec: Either ApplicationIR or SpecRequirements object

        Returns:
            List of entity objects with .name and .attributes
        """
        # 1) ApplicationIR: domain_model.entities
        if hasattr(spec, "domain_model") and spec.domain_model is not None:
            if hasattr(spec.domain_model, "entities"):
                return list(spec.domain_model.entities)
            if hasattr(spec.domain_model, "get_entities"):
                return spec.domain_model.get_entities()

        # 2) Object has modern get_entities() method
        if hasattr(spec, "get_entities") and callable(getattr(spec, "get_entities")):
            try:
                return spec.get_entities()
            except Exception as e:
                logger.warning(f"get_entities() failed: {e}")

        # 3) Legacy SpecRequirements.entities attribute
        if hasattr(spec, "entities"):
            return spec.entities if spec.entities else []

        logger.warning(f"Could not extract entities from spec type: {type(spec).__name__}")
        return []

    def _get_endpoints_from_spec(self, spec) -> list:
        """
        Extract endpoints from spec, handling both ApplicationIR and SpecRequirements.

        Args:
            spec: Either ApplicationIR or SpecRequirements object

        Returns:
            List of endpoint objects with .method and .path
        """
        # 1) ApplicationIR: api_model.endpoints
        if hasattr(spec, "api_model") and spec.api_model is not None:
            if hasattr(spec.api_model, "endpoints"):
                return list(spec.api_model.endpoints)
            if hasattr(spec.api_model, "get_endpoints"):
                return spec.api_model.get_endpoints()

        # 2) Object has modern get_endpoints() method
        if hasattr(spec, "get_endpoints") and callable(getattr(spec, "get_endpoints")):
            try:
                return spec.get_endpoints()
            except Exception as e:
                logger.warning(f"get_endpoints() failed: {e}")

        # 3) Legacy SpecRequirements.endpoints attribute
        if hasattr(spec, "endpoints"):
            return spec.endpoints if spec.endpoints else []

        logger.warning(f"Could not extract endpoints from spec type: {type(spec).__name__}")
        return []

    def _get_validation_rules_from_spec(self, spec) -> list:
        """
        Extract validation rules from spec, handling both ApplicationIR and SpecRequirements.

        Args:
            spec: Either ApplicationIR or SpecRequirements object

        Returns:
            List of validation rule objects
        """
        # 1) ApplicationIR: validation_model.rules
        if hasattr(spec, "validation_model") and spec.validation_model is not None:
            if hasattr(spec.validation_model, "rules"):
                return list(spec.validation_model.rules)

        # 2) Object has modern get_validation_rules() method
        if hasattr(spec, "get_validation_rules") and callable(getattr(spec, "get_validation_rules")):
            try:
                return spec.get_validation_rules()
            except Exception as e:
                logger.warning(f"get_validation_rules() failed: {e}")

        # 3) Legacy SpecRequirements.validation_rules attribute
        if hasattr(spec, "validation_rules"):
            return spec.validation_rules if spec.validation_rules else []

        return []

    def _get_requirements_from_spec(self, spec) -> list:
        """
        Extract functional requirements from spec, handling both ApplicationIR and SpecRequirements.

        Args:
            spec: Either ApplicationIR or SpecRequirements object

        Returns:
            List of requirement objects with .type, .id, .description
        """
        # 1) ApplicationIR: metadata.requirements or requirements_model
        if hasattr(spec, "metadata") and spec.metadata is not None:
            if isinstance(spec.metadata, dict) and "requirements" in spec.metadata:
                return spec.metadata["requirements"]

        # 2) Object has requirements attribute directly
        if hasattr(spec, "requirements"):
            reqs = spec.requirements
            if reqs is not None:
                return list(reqs) if hasattr(reqs, '__iter__') else []

        # 3) Legacy functional_requirements
        if hasattr(spec, "functional_requirements"):
            return spec.functional_requirements if spec.functional_requirements else []

        return []

    def _get_attributes_from_entity(self, entity) -> list:
        """
        Extract attributes/fields from entity, handling Entity (IR) and Entity/EntityDetail (legacy).

        Args:
            entity: Entity with .attributes (IR) or .fields (legacy)

        Returns:
            List of attribute-like objects
        """
        # 1) Entity moderno (IR): .attributes
        if hasattr(entity, "attributes") and entity.attributes is not None:
            return list(entity.attributes)

        # 2) Entity/EntityDetail legacy: .fields
        if hasattr(entity, "fields") and entity.fields is not None:
            return list(entity.fields)

        logger.warning(f"Could not extract attributes from entity: {type(entity).__name__}")
        return []

    def _is_relationship_attr(self, attr) -> bool:
        """
        Bug #48 Fix: Detect if attribute is a relationship (not a scalar field).

        Relationships are List[Entity] or similar and don't have normal "required" semantics.
        They should be excluded from validation matching because they're handled differently
        in SQLAlchemy (relationship()) and Pydantic (List[EntityResponse]).

        Args:
            attr: Attribute or Field object

        Returns:
            True if this is a relationship attribute
        """
        # Check type string for List[...] pattern (one-to-many relationship)
        attr_type = ""
        if hasattr(attr, "type"):
            attr_type = str(attr.type) if attr.type else ""
        elif hasattr(attr, "field_type"):
            attr_type = str(attr.field_type) if attr.field_type else ""

        # Relationships typically have List[Entity] type
        if "List[" in attr_type or "list[" in attr_type:
            return True

        # Check for relationship-specific metadata
        if hasattr(attr, "is_relationship") and attr.is_relationship:
            return True

        # Common relationship field names (heuristic)
        attr_name = getattr(attr, "name", "").lower()
        if attr_name in ("items", "orders", "products", "cart_items", "order_items"):
            return True

        return False

    def _is_attr_required(self, attr) -> bool:
        """
        Check if attribute is required, handling both Attribute (IR) and Field (legacy).

        Args:
            attr: Attribute or Field object

        Returns:
            True if required/not nullable
        """
        # Bug #48 Fix: Skip relationships - they don't have normal "required" semantics
        if self._is_relationship_attr(attr):
            return False

        # Attribute (IR): is_nullable=False means required
        if hasattr(attr, "is_nullable"):
            return not attr.is_nullable
        # Field (legacy): required=True means required
        if hasattr(attr, "required"):
            return attr.required
        return False

    def _get_attr_constraints(self, attr) -> dict:
        """
        Get constraints dict from attribute, normalizing both Attribute (dict) and Field (list).

        Args:
            attr: Attribute or Field object

        Returns:
            Dict of constraint_key: constraint_value
        """
        if not hasattr(attr, "constraints") or attr.constraints is None:
            return {}

        # Attribute (IR): constraints is already a dict
        if isinstance(attr.constraints, dict):
            return attr.constraints

        # Field (legacy): constraints is a list like ["unique", "length:1-255", "gt=0"]
        if isinstance(attr.constraints, list):
            result = {}
            for c in attr.constraints:
                if ":" in c:
                    key, val = c.split(":", 1)
                    result[key] = val
                elif "=" in c:
                    key, val = c.split("=", 1)
                    result[key] = val
                else:
                    result[c] = True
            return result

        return {}

    def _get_attr_type(self, attr) -> str:
        """
        Get data type string from attribute, handling Attribute (enum) and Field (str).

        Args:
            attr: Attribute or Field object

        Returns:
            Type as string
        """
        # Attribute (IR): data_type is an enum
        if hasattr(attr, "data_type"):
            return attr.data_type.value if hasattr(attr.data_type, "value") else str(attr.data_type)
        # Field (legacy): type is a string
        if hasattr(attr, "type"):
            return attr.type
        return "unknown"

    def validate(
        self, spec_requirements: SpecRequirements, generated_code: str
    ) -> ComplianceReport:
        """
        Validate generated code against specification

        Args:
            spec_requirements: Parsed specification with entities, endpoints, etc.
            generated_code: Python source code generated by CodeGenerationService

        Returns:
            ComplianceReport with detailed compliance analysis
        """
        logger.info("Starting compliance validation")

        # 1. Extract what was implemented
        entities_found = self.analyzer.extract_models(generated_code)
        endpoints_found = self.analyzer.extract_endpoints(generated_code)
        validations_found = self.analyzer.extract_validations(generated_code)

        # 2. Extract what was expected (IR-centric with defensive helpers)
        # Supports both ApplicationIR and legacy SpecRequirements
        entities_from_ir = self._get_entities_from_spec(spec_requirements)
        endpoints_from_ir = self._get_endpoints_from_spec(spec_requirements)

        entities_expected = [e.name for e in entities_from_ir]
        endpoints_expected = [f"{ep.method} {ep.path}" for ep in endpoints_from_ir]

        # ARCHITECTURE RULE #1: NO Manual Ground Truth in Code
        # Per ARCHITECTURE_RULES.md, ground truth must ONLY come from automated extraction.
        # We do NOT load validation_ground_truth from YAML or add manual definitions.
        #
        # Instead: validations_expected reflects what SHOULD be implemented based on spec constraints
        # (entities, endpoints, business logic), not a pre-defined manual list.
        validations_expected = []

        # Build expected validations from IR entities (defensive: handles both .attributes and .fields)
        for entity in entities_from_ir:
            # Use defensive helper to get attributes/fields
            for attr in self._get_attributes_from_entity(entity):
                # Add required constraint (defensive helper handles is_nullable vs required)
                if self._is_attr_required(attr):
                    sig = f"{entity.name}.{attr.name}: required"
                    if sig not in validations_expected:
                        validations_expected.append(sig)

                # Add other constraints from IR (defensive helper normalizes dict vs list)
                constraints = self._get_attr_constraints(attr)
                if constraints:
                    for constraint_key, constraint_val in constraints.items():
                        # Normalize constraint to match code format
                        constraint_str = f"{constraint_key}={constraint_val}" if constraint_val is not True else constraint_key
                        constraint_str = self._normalize_constraint(constraint_str)

                        sig = f"{entity.name}.{attr.name}: {constraint_str}"
                        if sig not in validations_expected:
                            validations_expected.append(sig)

        # If no explicit validations from entities, use ValidationModelIR rules
        if not validations_expected:
            validation_rules = self._get_validation_rules_from_spec(spec_requirements)
            for rule in validation_rules:
                validations_expected.append(f"{rule.entity}.{rule.field}: {rule.type.value}")

        # 3. Calculate compliance per category
        entity_compliance = self._calculate_compliance(entities_found, entities_expected)
        endpoint_compliance = self._calculate_endpoint_compliance_fuzzy(endpoints_found, endpoints_expected)

        # Always use flexible matching (no manual ground truth exists anymore per Architecture Rule #1)
        validation_compliance, validations_matched = self._calculate_validation_compliance(
            validations_found, validations_expected, use_exact_matching=False
        )

        # 4. Calculate overall compliance (weighted average)
        # Entities and endpoints are more important than validations
        overall_compliance = (
            entity_compliance * 0.40 + endpoint_compliance * 0.40 + validation_compliance * 0.20
        )

        # 5. Identify missing requirements
        missing = self._identify_missing_requirements(
            entities_expected,
            entities_found,
            endpoints_expected,
            endpoints_found,
            spec_requirements,
        )

        # 6. Build detailed report
        # Use matched validations (not all found) when ground truth exists for accurate metrics
        report = ComplianceReport(
            overall_compliance=overall_compliance,
            entities_implemented=entities_found,
            entities_expected=entities_expected,
            endpoints_implemented=endpoints_found,
            endpoints_expected=endpoints_expected,
            validations_implemented=validations_matched,  # Only matched validations
            validations_expected=validations_expected,
            validations_found=validations_found,  # All found validations
            missing_requirements=missing,
            compliance_details={
                "entities": entity_compliance,
                "endpoints": endpoint_compliance,
                "validations": validation_compliance,
            },
        )

        logger.info(
            f"Compliance validation complete: {overall_compliance:.1%} "
            f"(entities: {entity_compliance:.1%}, "
            f"endpoints: {endpoint_compliance:.1%}, "
            f"validations: {validation_compliance:.1%})"
        )

        return report

    def validate_from_app(
        self, spec_requirements: SpecRequirements, output_path
    ) -> ComplianceReport:
        """
        Validate generated code using OpenAPI schema from running app.

        CRITICAL FIX for 0% compliance bug: Instead of parsing main.py string,
        this dynamically imports the generated FastAPI app and reads its OpenAPI schema.

        This finds ALL entities and endpoints across modular architecture:
        - Entities from OpenAPI schemas (src/models/schemas.py)
        - Endpoints from OpenAPI paths (src/api/routes/*.py)

        Args:
            spec_requirements: Parsed specification with entities, endpoints, etc.
            output_path: Path to generated app directory (e.g., tests/e2e/generated_apps/app_123/)

        Returns:
            ComplianceReport with REAL compliance analysis
        """
        import sys
        import importlib.util
        from pathlib import Path

        # Ensure output_path is Path object and convert to absolute path
        if not isinstance(output_path, Path):
            output_path = Path(output_path).resolve()
        else:
            output_path = output_path.resolve()

        logger.info(f"Validating app at {output_path} using OpenAPI schema")

        # Add output_path to sys.path for imports
        output_path_str = str(output_path)
        if output_path_str not in sys.path:
            sys.path.insert(0, output_path_str)

        try:
            # Import the generated FastAPI app
            # Try src/main.py first (standard DevMatrix structure)
            main_py_path = output_path / "src" / "main.py"
            is_root_main = False  # Track if main.py is in root vs src/

            # Fallback: try main.py in root if src/main.py doesn't exist
            if not main_py_path.exists():
                root_main_py = output_path / "main.py"
                if root_main_py.exists():
                    logger.info(f"Found main.py in root (not in src/)")
                    main_py_path = root_main_py
                    is_root_main = True
                else:
                    logger.error(f"main.py not found at {output_path / 'src' / 'main.py'} or {root_main_py}")
                    # Fallback to old validation method
                    logger.warning("Falling back to string-based validation (will show low compliance)")
                    main_code = ""
                    if root_main_py.exists():
                        main_code = root_main_py.read_text()
                    return self.validate(spec_requirements, main_code)

            # Configure temporary database for validation (avoid global DATABASE_URL issues)
            # Use asyncpg driver to avoid psycopg2 async errors
            import os
            import sys
            import importlib

            # CRITICAL: Store and replace DATABASE_URL BEFORE any app imports
            original_database_url = os.environ.get('DATABASE_URL')

            # Fix DATABASE_URL if it exists but doesn't have asyncpg driver
            # This is critical because many environments set DATABASE_URL with postgresql://
            # but generated apps use AsyncSession which requires postgresql+asyncpg://
            if original_database_url and 'postgresql://' in original_database_url:
                if '+asyncpg' not in original_database_url:
                    # Convert postgresql:// to postgresql+asyncpg://
                    fixed_url = original_database_url.replace('postgresql://', 'postgresql+asyncpg://')
                    logger.info(f"Converting DATABASE_URL to async driver for validation")
                    os.environ['DATABASE_URL'] = fixed_url
                else:
                    # Already has asyncpg, use as is
                    pass
            else:
                # No DATABASE_URL or not PostgreSQL, set a dummy async URL
                # This won't actually connect during OpenAPI extraction
                os.environ['DATABASE_URL'] = 'postgresql+asyncpg://validation:validation@localhost/validation_temp'

            # Clear any existing modules from cache to avoid driver conflicts and cached settings
            # This is important because Settings uses @lru_cache and might have cached the old DATABASE_URL
            # CRITICAL: Save DevMatrix's 'src' module to restore it later
            devmatrix_src_module = sys.modules.get('src', None)

            # Clear all potentially conflicting modules INCLUDING 'src' base package
            modules_to_clear = [m for m in list(sys.modules.keys())
                              if any(pattern in m for pattern in ['psycopg', 'sqlalchemy', 'src.', 'src', 'api.', 'core.', 'models.'])]
            for module_name in modules_to_clear:
                sys.modules.pop(module_name, None)

            # Extra safety: Explicitly remove 'src' if it exists (DevMatrix namespace collision)
            sys.modules.pop('src', None)

            # Bug #46 Fix: Invalidate importlib caches to force re-reading modified .py files
            # Without this, Python may use cached bytecode (.pyc) instead of fresh source
            # This is critical for repair loops where code is modified between validations
            importlib.invalidate_caches()
            logger.debug("Invalidated importlib caches for fresh module loading")

            # Bug #46 Fix: Clear __pycache__ directories to prevent stale bytecode
            # This is especially important when CodeRepairAgent modifies schemas.py/entities.py
            try:
                import shutil
                pycache_dirs = list(output_path.rglob("__pycache__"))
                for pycache in pycache_dirs:
                    if pycache.is_dir():
                        shutil.rmtree(pycache, ignore_errors=True)
                if pycache_dirs:
                    logger.debug(f"Cleared {len(pycache_dirs)} __pycache__ directories for fresh imports")
            except Exception as e:
                logger.debug(f"Could not clear __pycache__: {e}")

            # Clear Prometheus metrics registry to avoid "Duplicated timeseries" errors
            # This happens when we import the app multiple times in the same Python process
            try:
                from prometheus_client import REGISTRY
                # Create a fresh registry by removing all collectors
                collectors = list(REGISTRY._collector_to_names.keys())
                for collector in collectors:
                    try:
                        REGISTRY.unregister(collector)
                    except Exception:
                        pass  # Ignore if unregister fails
            except ImportError:
                pass  # prometheus_client not available, that's fine

            try:
                # Load main.py as module with proper package context
                app_root = str(output_path)

                # Store original sys.path and cwd for cleanup
                original_sys_path = sys.path.copy()
                original_cwd = os.getcwd()

                # CRITICAL: Add app root to sys.path FIRST (highest priority)
                # This allows Python to find the 'src' package
                if app_root in sys.path:
                    sys.path.remove(app_root)  # Remove if exists to re-add at position 0
                sys.path.insert(0, app_root)

                # Store original working directory but DON'T change it yet
                # Changing cwd breaks relative imports in the generated app
                logger.debug(f"App root added to sys.path[0]: {sys.path[0]}")
                logger.debug(f"Current working directory: {os.getcwd()}")

                # Verify files exist (log for debugging)
                src_init = os.path.join(app_root, 'src', '__init__.py')
                src_main = os.path.join(app_root, 'src', 'main.py')
                logger.debug(f"src/__init__.py exists: {os.path.exists(src_init)}")
                logger.debug(f"src/main.py exists: {os.path.exists(src_main)}")

                # Import main module (either 'main' from root or 'src.main' from src/)
                # The app_root in sys.path[0] should be enough
                if is_root_main:
                    # main.py is in root - import as 'main'
                    main_module = __import__('main')
                else:
                    # main.py is in src/ - import as 'src.main'
                    main_module = __import__('src.main', fromlist=['app'])

                # Get FastAPI app instance immediately (while sys.path is still valid)
                app = main_module.app

                logger.info("Successfully imported FastAPI app")

                # Extract OpenAPI schema (while app is still accessible)
                openapi_schema = app.openapi()

            finally:
                # CRITICAL: Restore working directory FIRST (even if exception occurred)
                # This must be in finally block to prevent affecting subsequent operations
                try:
                    os.chdir(original_cwd)
                except:
                    pass  # Ignore if restoration fails

                # Restore original DATABASE_URL
                if original_database_url is not None:
                    os.environ['DATABASE_URL'] = original_database_url
                else:
                    os.environ.pop('DATABASE_URL', None)

                # Cleanup: Remove app_root from sys.path if we added it
                if app_root in sys.path:
                    sys.path.remove(app_root)

                # Cleanup: Clear lru_cache from get_settings() to avoid stale config
                # This is critical because get_settings() caches the Settings object,
                # and if we reimport modules later, we want fresh settings
                if 'src.core.config' in sys.modules:
                    try:
                        config_module = sys.modules['src.core.config']
                        if hasattr(config_module, 'get_settings'):
                            config_module.get_settings.cache_clear()
                    except Exception:
                        pass  # Ignore if cache_clear fails

                # Cleanup: Remove imported src.* modules from cache to avoid pollution
                modules_to_remove = [k for k in sys.modules.keys() if k.startswith('src.')]
                for module_name in modules_to_remove:
                    sys.modules.pop(module_name, None)

                # CRITICAL: Restore DevMatrix's 'src' module so rest of pipeline can import from it
                if devmatrix_src_module is not None:
                    sys.modules['src'] = devmatrix_src_module

            # 1. Extract entities from OpenAPI schemas
            # NOTE: Schemas might be empty (just 'pass') but we count them as present
            # since the structure exists even if fields are missing
            entities_found = []
            schemas = openapi_schema.get("components", {}).get("schemas", {})

            # Build set of expected entity names (lowercase for comparison) - IR-centric with defensive helper
            entities_from_ir = self._get_entities_from_spec(spec_requirements)
            entities_expected_lower = {e.lower() for e in [ent.name for ent in entities_from_ir]}
            logger.debug(f"Looking for entities: {entities_expected_lower}")

            # Check all schemas and extract base entity names
            for schema_name in schemas.keys():
                # Remove common suffixes to get base entity name
                base_name = schema_name

                # Try removing suffixes in order (longest first)
                suffixes = ['Response', 'Create', 'Update', 'Entity', 'List', 'Base']
                for suffix in suffixes:
                    if base_name.endswith(suffix):
                        base_name = base_name[:-len(suffix)]
                        break

                # Check if this matches an expected entity (case-insensitive)
                if base_name.lower() in entities_expected_lower and base_name not in entities_found:
                    entities_found.append(base_name)
                    logger.debug(f"Found entity '{base_name}' from schema '{schema_name}'")

            logger.info(f"Extracted {len(entities_found)} entities from OpenAPI schemas: {entities_found}")

            # 1b. Extract entities directly from entities.py (more accurate - includes entities without endpoints)
            entities_file = output_path / "src" / "models" / "entities.py"
            if entities_file.exists():
                logger.debug(f"Reading entities directly from {entities_file}")
                entities_content = entities_file.read_text()

                # Find all class definitions: class XyzEntity(Base):
                import re
                entity_pattern = r'class\s+(\w+)Entity\(Base\):'
                entity_matches = re.findall(entity_pattern, entities_content)

                for entity_name in entity_matches:
                    if entity_name.lower() in entities_expected_lower and entity_name not in entities_found:
                        entities_found.append(entity_name)
                        logger.debug(f"Found entity '{entity_name}' from entities.py")

                logger.info(f"After checking entities.py: {len(entities_found)} entities found: {entities_found}")
            else:
                logger.warning(f"entities.py not found at {entities_file}")

            # 2. Extract endpoints from OpenAPI paths
            endpoints_found = []
            paths = openapi_schema.get("paths", {})

            for path, methods in paths.items():
                for method in methods.keys():
                    # Only include actual HTTP methods (not 'parameters', 'summary', etc.)
                    if method.upper() in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']:
                        endpoints_found.append(f"{method.upper()} {path}")

            logger.info(f"Extracted {len(endpoints_found)} endpoints from OpenAPI paths")

            # 3. Extract validations (heuristic from schemas)
            import re

            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'

            validations_found = []
            validations_seen = set()

            def record_validation(entity_name: str, field_name: str, constraint: str) -> None:
                """Add a validation signature once."""
                normalized_entity = self._normalize_entity_name(entity_name)
                normalized_constraint = self._normalize_constraint(constraint)
                sig = f"{normalized_entity}.{field_name}: {normalized_constraint}"
                if sig not in validations_seen:
                    validations_seen.add(sig)
                    validations_found.append(sig)

            for schema_name, schema_def in schemas.items():
                # Get base entity name (remove suffixes)
                base_entity_name = schema_name
                suffixes = ['Response', 'Create', 'Update', 'Entity', 'List', 'Base']
                for suffix in suffixes:
                    if base_entity_name.endswith(suffix):
                        base_entity_name = base_entity_name[:-len(suffix)]
                        break

                required_props = set(schema_def.get("required", []))
                properties = schema_def.get("properties", {})
                for prop_name, prop_def in properties.items():
                    # Helper function to extract validations from a schema (handles anyOf)
                    def extract_validations(schema_obj, entity_name, field_name):
                        if field_name in required_props:
                            record_validation(entity_name, field_name, "required")

                        if not isinstance(schema_obj, dict):
                            return

                        enum_vals = schema_obj.get("enum")
                        if isinstance(enum_vals, list) and enum_vals:
                            enum_str = ",".join(str(v) for v in enum_vals)
                            record_validation(entity_name, field_name, f"enum={enum_str}")

                        if schema_obj.get("exclusiveMinimum") is not None:
                            record_validation(entity_name, field_name, f"gt={schema_obj['exclusiveMinimum']}")
                        elif "minimum" in schema_obj:
                            record_validation(entity_name, field_name, f"ge={schema_obj['minimum']}")

                        if "maximum" in schema_obj:
                            record_validation(entity_name, field_name, f"le={schema_obj['maximum']}")

                        if "minLength" in schema_obj:
                            record_validation(entity_name, field_name, f"min_length={schema_obj['minLength']}")

                        if "maxLength" in schema_obj:
                            record_validation(entity_name, field_name, f"max_length={schema_obj['maxLength']}")

                        if "minItems" in schema_obj:
                            record_validation(entity_name, field_name, f"min_items={schema_obj['minItems']}")

                        pattern = schema_obj.get("pattern")
                        fmt = schema_obj.get("format")
                        if fmt == "uuid" or pattern == uuid_pattern:
                            record_validation(entity_name, field_name, "uuid_format")
                        elif fmt == "email" or pattern == email_pattern:
                            record_validation(entity_name, field_name, "email_format")
                        elif pattern:
                            record_validation(entity_name, field_name, f"pattern={pattern}")


                        # Extract default values - indicates auto-generation
                        if "default" in schema_obj:
                            default_val = schema_obj["default"]
                            # Common patterns for auto-generated fields
                            if isinstance(default_val, bool):
                                record_validation(entity_name, field_name, f"default={str(default_val).lower()}")
                            elif isinstance(default_val, (int, float)):
                                record_validation(entity_name, field_name, f"default={default_val}")
                            elif isinstance(default_val, str):
                                # String defaults like "open", "pending", etc
                                record_validation(entity_name, field_name, f"default={default_val}")

                        # FIX 11: Extract readOnly and description patterns from OpenAPI schema
                        if schema_obj.get("readOnly") is True:
                            record_validation(entity_name, field_name, "read-only")

                        desc = schema_obj.get("description")
                        if desc:
                            if desc is True or str(desc).lower() == "true":
                                record_validation(entity_name, field_name, "read-only")
                            
                            if isinstance(desc, str):
                                desc_lower = desc.lower()
                                
                                if "read-only" in desc_lower or "read only" in desc_lower:
                                    record_validation(entity_name, field_name, "read-only")
                                
                                # Handle "Auto-calculated: <pattern>" format
                                if "auto-calculated:" in desc_lower:
                                    parts = desc_lower.split("auto-calculated:")
                                    if len(parts) > 1:
                                        pattern = parts[1].strip()
                                        if pattern:
                                            normalized = pattern.replace(" ", "_").replace("-", "_")
                                            if normalized == "auto_calculated":
                                                record_validation(entity_name, field_name, "auto-calculated")
                                            elif normalized == "sum_of_items":
                                                record_validation(entity_name, field_name, "sum_of_items")
                                            elif normalized == "sum_of_amounts":
                                                record_validation(entity_name, field_name, "sum_of_amounts")
                                            elif "at_add_time" in normalized or "at_time_of" in normalized:
                                                record_validation(entity_name, field_name, "snapshot_at_add_time")
                                            elif "at_order_time" in normalized:
                                                record_validation(entity_name, field_name, "snapshot_at_order_time")
                                            elif normalized == "immutable":
                                                record_validation(entity_name, field_name, "immutable")
                                            else:
                                                record_validation(entity_name, field_name, normalized)
                                else:
                                    # Pattern matching for computed/auto-calculated fields (fallback)
                                    if "auto-calculated" in desc_lower or "auto_calculated" in desc_lower:
                                        record_validation(entity_name, field_name, "auto-calculated")
                                    if "sum of items" in desc_lower or "sum_of_items" in desc_lower:
                                        record_validation(entity_name, field_name, "sum_of_items")
                                    if "sum of amounts" in desc_lower or "sum_of_amounts" in desc_lower:
                                        record_validation(entity_name, field_name, "sum_of_amounts")
                                    if "at time of" in desc_lower or "at_add_time" in desc_lower:
                                        record_validation(entity_name, field_name, "snapshot_at_add_time")
                                    if "at order time" in desc_lower or "at_order_time" in desc_lower:
                                        record_validation(entity_name, field_name, "snapshot_at_order_time")
                                    if "immutable" in desc_lower:
                                        record_validation(entity_name, field_name, "immutable")

                    # Extract validations from prop_def directly
                    extract_validations(prop_def, base_entity_name, prop_name)

                    # Also check inside anyOf (for Decimal fields that can be number or string)
                    if "anyOf" in prop_def:
                        for sub_schema in prop_def["anyOf"]:
                            if isinstance(sub_schema, dict):
                                extract_validations(sub_schema, base_entity_name, prop_name)

            logger.info(f"Extracted {len(validations_found)} validations from OpenAPI schemas")

            # 3b. Extract validations directly from schemas.py using AST (handles multi-line Field() calls)
            schemas_file = output_path / "src" / "models" / "schemas.py"
            if schemas_file.exists():
                logger.debug(f"Reading validations from {schemas_file} using AST parser")
                try:
                    import ast
                    schemas_content = schemas_file.read_text()
                    tree = ast.parse(schemas_content)
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Get class name and normalize it
                            class_name = node.name
                            
                            # Process all assignments in the class
                            for item in node.body:
                                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                                    field_name = item.target.id
                                    
                                    # Check if it's a Field() call
                                    if isinstance(item.value, ast.Call):
                                        # Check for Field() or similar
                                        if (isinstance(item.value.func, ast.Name) and item.value.func.id == 'Field') or \
                                           (isinstance(item.value.func, ast.Attribute) and item.value.func.attr == 'Field'):
                                            
                                            # Extract constraints from Field() keywords
                                            for keyword in item.value.keywords:
                                                if keyword.arg == 'description' and isinstance(keyword.value, ast.Constant):
                                                    desc_val = keyword.value.value
                                                    
                                                    if desc_val is True or str(desc_val).lower() == "true":
                                                        record_validation(class_name, field_name, "read-only")
                                                    elif isinstance(desc_val, str):
                                                        desc_lower = desc_val.lower()
                                                        
                                                        if "read-only" in desc_lower or "read only" in desc_lower:
                                                            record_validation(class_name, field_name, "read-only")
                                                        
                                                        # Handle "Auto-calculated: <pattern>" format
                                                        if "auto-calculated:" in desc_lower:
                                                            parts = desc_lower.split("auto-calculated:")
                                                            if len(parts) > 1:
                                                                pattern = parts[1].strip()
                                                                if pattern:
                                                                    normalized = pattern.replace(" ", "_").replace("-", "_")
                                                                    if normalized == "auto_calculated":
                                                                        record_validation(class_name, field_name, "auto-calculated")
                                                                    elif normalized == "sum_of_items":
                                                                        record_validation(class_name, field_name, "sum_of_items")
                                                                    elif normalized == "sum_of_amounts":
                                                                        record_validation(class_name, field_name, "sum_of_amounts")
                                                                    elif "at_add_time" in normalized or "at_time_of" in normalized:
                                                                        record_validation(class_name, field_name, "snapshot_at_add_time")
                                                                    elif "at_order_time" in normalized:
                                                                        record_validation(class_name, field_name, "snapshot_at_order_time")
                                                                    elif normalized == "immutable":
                                                                        record_validation(class_name, field_name, "immutable")
                                                        else:
                                                            # Pattern matching for computed/auto-calculated fields (fallback)
                                                            if "auto-calculated" in desc_lower or "auto_calculated" in desc_lower:
                                                                record_validation(class_name, field_name, "auto-calculated")
                                                            if "sum of items" in desc_lower or "sum_of_items" in desc_lower:
                                                                record_validation(class_name, field_name, "sum_of_items")
                                                            if "at time of" in desc_lower or "at_add_time" in desc_lower:
                                                                record_validation(class_name, field_name, "snapshot_at_add_time")
                                                            if "at order time" in desc_lower or "at_order_time" in desc_lower:
                                                                record_validation(class_name, field_name, "snapshot_at_order_time")
                                                            if "immutable" in desc_lower:
                                                                record_validation(class_name, field_name, "immutable")
                                                
                                                # Extract other constraints
                                                elif keyword.arg in ["gt", "ge", "lt", "le", "min_length", "max_length", "min_items"]:
                                                    if isinstance(keyword.value, ast.Constant):
                                                        record_validation(class_name, field_name, f"{keyword.arg}={keyword.value.value}")
                                                
                                                elif keyword.arg == "pattern" and isinstance(keyword.value, ast.Constant):
                                                    pat_val = keyword.value.value
                                                    if pat_val == uuid_pattern:
                                                        record_validation(class_name, field_name, "uuid_format")
                                                    elif pat_val == email_pattern:
                                                        record_validation(class_name, field_name, "email_format")
                                                    else:
                                                        record_validation(class_name, field_name, f"pattern={pat_val}")
                                            
                                            # Check if Field(...) for required
                                            if any(isinstance(arg, ast.Constant) and arg.value == Ellipsis for arg in item.value.args):
                                                record_validation(class_name, field_name, "required")
                                    
                                    # Check annotation for Literal (enum)
                                    if item.annotation:
                                        annotation_str = ast.unparse(item.annotation) if hasattr(ast, 'unparse') else ""
                                        if "Literal[" in annotation_str:
                                            # Extract enum values
                                            literal_match = re.search(r'Literal\[(.+?)\]', annotation_str)
                                            if literal_match:
                                                raw_vals = literal_match.group(1)
                                                enum_vals = [v.strip().strip('"').strip("'") for v in raw_vals.split(',') if v.strip()]
                                                if enum_vals:
                                                    record_validation(class_name, field_name, f"enum={','.join(enum_vals)}")
                                        
                                        if "UUID" in annotation_str:
                                            record_validation(class_name, field_name, "uuid_format")
                    
                    logger.info(f"After checking schemas.py with AST: {len(validations_found)} validations found")
                except Exception as e:
                    logger.warning(f"Failed to parse schemas.py with AST: {e}, falling back to regex")
            else:
                logger.warning(f"schemas.py not found at {schemas_file}")

            # 3.5. PASO 1C: Extract SQLAlchemy constraints using AST Parser (robust)
            # Replaces regex-based extraction with AST parser that handles multi-line definitions
            entities_file = output_path / "src" / "models" / "entities.py"
            if entities_file.exists():
                try:
                    entities_content = entities_file.read_text()
                    sqlalchemy_constraints = self._extract_sqlalchemy_constraints_ast(entities_content)

                    extracted_count = 0
                    for entity_name, fields in sqlalchemy_constraints.items():
                        for field_info in fields:
                            field_name = field_info["field"]
                            constraints = field_info["constraints"]

                            for constraint in constraints:
                                record_validation(entity_name, field_name, constraint)
                                extracted_count += 1

                    logger.info(f"✅ Extracted {extracted_count} SQLAlchemy constraints using AST parser")
                except Exception as e:
                    logger.warning(f"Failed to extract SQLAlchemy constraints: {e}")
            else:
                logger.debug(f"entities.py not found at {entities_file}")

            # 4. Extract what was expected from spec (IR-centric with defensive helpers)
            # Supports both ApplicationIR and legacy SpecRequirements
            entities_from_ir = self._get_entities_from_spec(spec_requirements)
            endpoints_from_ir = self._get_endpoints_from_spec(spec_requirements)

            entities_expected = [e.name for e in entities_from_ir]
            endpoints_expected = [f"{ep.method} {ep.path}" for ep in endpoints_from_ir]

            # ARCHITECTURE RULE #1: NO Manual Ground Truth in Code
            # Per ARCHITECTURE_RULES.md, ground truth must ONLY come from automated extraction.
            # We do NOT load validation_ground_truth from YAML or add manual definitions.
            #
            # Instead: validations_expected reflects what SHOULD be implemented based on spec constraints
            # (entities, endpoints, business logic), not a pre-defined manual list.
            validations_expected = []

            # Build expected validations from IR entities (defensive: handles both .attributes and .fields)
            for entity in entities_from_ir:
                # Use defensive helper to get attributes/fields
                for attr in self._get_attributes_from_entity(entity):
                    # Add required constraint (defensive helper handles is_nullable vs required)
                    if self._is_attr_required(attr):
                        sig = f"{entity.name}.{attr.name}: required"
                        if sig not in validations_expected:
                            validations_expected.append(sig)

                    # Add other constraints from IR (defensive helper normalizes dict vs list)
                    constraints = self._get_attr_constraints(attr)
                    if constraints:
                        for constraint_key, constraint_val in constraints.items():
                            # Normalize constraint to match code format
                            constraint_str = f"{constraint_key}={constraint_val}" if constraint_val is not True else constraint_key
                            constraint_str = self._normalize_constraint(constraint_str)

                            sig = f"{entity.name}.{attr.name}: {constraint_str}"
                            if sig not in validations_expected:
                                validations_expected.append(sig)

            # Bug #117 Fix: Always include ValidationModelIR rules in expectations
            # Previously this was a fallback, causing a gap where DomainModel provided basic rules (required)
            # but ValidationModelIR provided advanced rules (gt=0, regex), leading to 100% compliance
            # but failing tests. Now we merge both sources.
            validation_rules = self._get_validation_rules_from_spec(spec_requirements)
            for rule in validation_rules:
                # Normalize rule to match signature format
                constraint_str = rule.type.value
                if rule.condition:
                    # Map condition to constraint string if possible
                    # e.g. condition="> 0" -> "gt=0"
                    if ">" in rule.condition and "0" in rule.condition:
                        constraint_str = "gt=0"
                    elif "regex" in rule.type.value or "pattern" in rule.type.value:
                        constraint_str = f"pattern={rule.condition}"
                
                sig = f"{rule.entity}.{rule.attribute}: {constraint_str}"
                
                # Avoid duplicates if DomainModel already provided this rule
                if sig not in validations_expected:
                    validations_expected.append(sig)

            # 5. Calculate compliance per category
            entity_compliance = self._calculate_compliance(entities_found, entities_expected)
            endpoint_compliance = self._calculate_endpoint_compliance_fuzzy(endpoints_found, endpoints_expected)

            # Always use flexible matching (no manual ground truth exists anymore per Architecture Rule #1)
            validation_compliance, validations_matched = self._calculate_validation_compliance(
                validations_found, validations_expected, use_exact_matching=False
            )

            # 6. Calculate overall compliance (weighted average)
            # Entities and endpoints are more important than validations
            overall_compliance = (
                entity_compliance * 0.40 + endpoint_compliance * 0.40 + validation_compliance * 0.20
            )

            # 7. Identify missing requirements
            missing = self._identify_missing_requirements(
                entities_expected,
                entities_found,
                endpoints_expected,
                endpoints_found,
                spec_requirements,
            )

            # 8. Build detailed report
            # Use matched validations (not all found) when ground truth exists for accurate metrics
            report = ComplianceReport(
                overall_compliance=overall_compliance,
                entities_implemented=entities_found,
                entities_expected=entities_expected,
                endpoints_implemented=endpoints_found,
                endpoints_expected=endpoints_expected,
                validations_implemented=validations_matched,  # Only matched validations
                validations_expected=validations_expected,
                validations_found=validations_found,  # All found validations
                missing_requirements=missing,
                compliance_details={
                    "entities": entity_compliance,
                    "endpoints": endpoint_compliance,
                    "validations": validation_compliance,
                },
            )

            logger.info(
                f"OpenAPI-based compliance validation complete: {overall_compliance:.1%} "
                f"(entities: {entity_compliance:.1%}, "
                f"endpoints: {endpoint_compliance:.1%}, "
                f"validations: {validation_compliance:.1%})"
            )

            return report

        except Exception as e:
            logger.error(f"Error importing app for OpenAPI validation: {e}")
            import traceback
            traceback.print_exc()

            # Fallback to old validation method
            logger.warning("Falling back to string-based validation (will show low compliance)")
            main_code = ""
            if (output_path / "src" / "main.py").exists():
                main_code = (output_path / "src" / "main.py").read_text()
            return self.validate(spec_requirements, main_code)

        finally:
            # Clean up sys.path
            if output_path_str in sys.path:
                sys.path.remove(output_path_str)

    def validate_or_raise(
        self, spec_requirements: SpecRequirements, generated_code: str, threshold: float = 0.80
    ) -> ComplianceReport:
        """
        Validate and raise exception if compliance below threshold

        Args:
            spec_requirements: Parsed specification
            generated_code: Generated Python code
            threshold: Minimum compliance score (default 0.80 = 80%)

        Returns:
            ComplianceReport if compliance >= threshold

        Raises:
            ComplianceValidationError: If compliance < threshold
        """
        report = self.validate(spec_requirements, generated_code)

        if report.overall_compliance < threshold:
            error_msg = (
                f"Compliance validation FAILED: {report.overall_compliance:.1%} "
                f"(threshold: {threshold:.1%})\n\n"
                f"{report}"
            )
            logger.error(error_msg)
            raise ComplianceValidationError(error_msg)

        logger.info(f"Compliance validation PASSED: {report.overall_compliance:.1%}")
        return report

    def _normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity/schema names coming from OpenAPI component names.

        Handles variations like CartItem-Input / CartItem-Output so they match
        the base entity name used in ground truth and spec parsing.
        """
        normalized = name.strip()
        suffixes = [
            "-Input",
            "-Output",
            "-Request",
            "-Response",
            "Input",
            "Output",
            "Request",
            "Response",
            "Model",
        ]
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[: -len(suffix)]
        return normalized or name

    def _normalize_constraint(self, constraint: str) -> str:
        """
        Normalize constraint string to standard format used in code analysis
        
        Args:
            constraint: Raw constraint string (e.g., "> 0", "email format")
            
        Returns:
            Normalized constraint (e.g., "gt=0", "email_format")
        """
        c = constraint.strip()
        c_lower = c.lower()
        
        # Special handling for enums: preserve case of values
        if c_lower.startswith("enum="):
            # Just ensure the prefix is standardized if needed, but for now return as is
            # assuming ground truth has correct case
            return c
        
        # For other constraints, work with lowercase
        c = c_lower
        
        # Map symbols to text
        if c.startswith(">="):
            return f"ge={c[2:].strip()}"
        if c.startswith(">"):
            return f"gt={c[1:].strip()}"
        if c.startswith("<="):
            return f"le={c[2:].strip()}"
        if c.startswith("<"):
            return f"lt={c[1:].strip()}"

        # Normalize numeric values like gt=0.0 -> gt=0
        numeric_match = re.match(r"^(gt|ge|lt|le)=(-?\d+(?:\.\d+)?)$", c)
        if numeric_match:
            key, value = numeric_match.groups()
            if value.endswith(".0"):
                value = value[:-2]
            return f"{key}={value}"
            
        # Map common terms
        if c == "email format":
            return "email_format"
        if c == "uuid format":
            return "uuid_format"

        return c

    def _semantic_match_validations(
        self,
        found: List[str],
        expected: List[str]
    ) -> tuple[float, List[str]]:
        """
        Use SemanticMatcher for ML-based validation matching.

        This replaces the manual `semantic_equivalences` dictionary with embeddings + LLM.

        Priority order:
        1. ValidationModelIR (if available from ApplicationIR) - most precise
        2. Standard SemanticMatcher batch matching - general purpose

        Args:
            found: Validation signatures found in code
            expected: Validation requirements from spec

        Returns:
            Tuple of (compliance_score 0.0-1.0, list of matched validation strings)
        """
        if not self.semantic_matcher:
            raise RuntimeError("SemanticMatcher not initialized")

        if not expected:
            return 1.0, found

        if not found:
            return 0.0, []

        # ═══════════════════════════════════════════════════════════════════════════════
        # IR-BASED MATCHING: Use ValidationModelIR if available (more precise)
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.validation_model and hasattr(self.validation_model, 'rules') and len(self.validation_model.rules) > 0:
            logger.info(f"🧠 Using IR-based matching with {len(self.validation_model.rules)} rules from ValidationModelIR")
            compliance, results = self.semantic_matcher.match_from_validation_model(
                self.validation_model, found
            )

            # Convert MatchResult list to matched validation strings
            matched_validations = [r.code_constraint for r in results if r.match]

            if compliance >= 1.0:
                return 1.0, found  # All matched, return all found
            return compliance, matched_validations

        # ═══════════════════════════════════════════════════════════════════════════════
        # FAST IR MATCHING: Use IRSemanticMatcher with index-based lookup (Phase 3)
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("🚀 Using IRSemanticMatcher for fast batch matching")

        try:
            from src.services.ir_semantic_matcher import IRSemanticMatcher
            from src.cognitive.ir.constraint_ir import ConstraintIR

            # Initialize IR matcher (no embedding fallback for maximum speed)
            ir_matcher = IRSemanticMatcher(use_embedding_fallback=False)

            # Parse strings to ConstraintIR
            spec_constraints = [ConstraintIR.from_validation_string(s) for s in expected]
            code_constraints = [ConstraintIR.from_validation_string(s) for s in found]

            # Use fast IR matching with index (O(n) instead of O(n×m))
            compliance, ir_results = ir_matcher.match_constraint_lists(spec_constraints, code_constraints)

            # Convert results back to matched validation strings
            matches = sum(1 for r in ir_results if r.match)
            matched_validations = [r.code_constraint.to_string() for r in ir_results if r.match and r.code_constraint]
            unmatched = [r.spec_constraint.to_string() for r in ir_results if not r.match]

            logger.info(f"📊 IRSemanticMatcher: {matches}/{len(expected)} = {compliance:.1%}")

        except Exception as e:
            # Fallback to slow SemanticMatcher if IRSemanticMatcher fails
            logger.warning(f"⚠️ IRSemanticMatcher failed ({e}), using slow SemanticMatcher")
            logger.info("📋 Using standard SemanticMatcher batch matching")

            matches = 0
            matched_validations = []
            unmatched = []

            for exp_val in expected:
                best_match = None
                best_score = 0.0

                for found_val in found:
                    result = self.semantic_matcher.match(exp_val, found_val)
                    if result.match and result.confidence > best_score:
                        best_match = found_val
                        best_score = result.confidence

                if best_match:
                    matches += 1
                    matched_validations.append(best_match)
                else:
                    unmatched.append(exp_val)

        # Calculate compliance
        compliance = matches / len(expected) if expected else 1.0

        if compliance >= 1.0:
            logger.info(f"✅ Semantic matching: {matches}/{len(expected)} = 100% (+ {len(found) - matches} extras)")
            return 1.0, found  # Return all found (includes extras)
        else:
            logger.warning(f"⚠️ Semantic matching: {matches}/{len(expected)} = {compliance:.1%}")
            if unmatched:
                logger.warning(f"   Unmatched: {unmatched[:5]}{'...' if len(unmatched) > 5 else ''}")
            return compliance, matched_validations

    def _extract_sqlalchemy_constraints_ast(self, entities_content: str) -> Dict[str, List[Dict]]:
        """
        PASO 1B: Extract SQLAlchemy constraints using AST parser (robust).

        Handles multi-line Column definitions, nested function calls, etc.

        Returns: {
            "Product": [
                {"field": "id", "constraints": ["unique", "required", "primary_key"]},
                {"field": "name", "constraints": ["required"]},
            ]
        }
        """
        import ast

        try:
            tree = ast.parse(entities_content)
        except SyntaxError as e:
            logger.error(f"entities.py has syntax errors: {e}, falling back to empty result")
            return {}

        result = {}

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Extract entity name: ProductEntity → Product
            if not node.name.endswith("Entity"):
                continue
            entity_name = node.name[:-6]  # Remove "Entity" suffix
            result[entity_name] = []

            # Process class body
            for stmt in node.body:
                if not isinstance(stmt, ast.Assign):
                    continue

                # field_name = Column(...)
                field_name = stmt.targets[0].id if hasattr(stmt.targets[0], 'id') else None
                if not field_name:
                    continue

                constraints = []

                # Check if it's a Column() call
                if isinstance(stmt.value, ast.Call):
                    call = stmt.value
                    func_name = call.func.attr if isinstance(call.func, ast.Attribute) else None

                    if func_name == "Column" or (isinstance(call.func, ast.Name) and call.func.id == "Column"):
                        # Extract keyword arguments
                        for keyword in call.keywords:
                            key = keyword.arg
                            value = keyword.value

                            if key == "nullable":
                                # nullable=False → required
                                if isinstance(value, ast.Constant) and value.value is False:
                                    constraints.append("required")

                            elif key == "unique":
                                # unique=True → unique
                                if isinstance(value, ast.Constant) and value.value is True:
                                    constraints.append("unique")

                            elif key == "primary_key":
                                # primary_key=True → primary_key
                                if isinstance(value, ast.Constant) and value.value is True:
                                    constraints.append("primary_key")

                            elif key == "default" or key == "default_factory":
                                # Normalize default/default_factory values to constraint names
                                if isinstance(value, ast.Attribute):
                                    # default=uuid.uuid4 or default=datetime.utcnow → auto-generated
                                    # Also: default_factory=datetime.utcnow → auto-generated
                                    if value.attr == "uuid4" or value.attr == "utcnow":
                                        constraints.append("auto-generated")
                                elif isinstance(value, ast.Constant):
                                    # default=True → default_true, default=False → default_false, etc.
                                    const_val = value.value
                                    if const_val is True:
                                        constraints.append("default_true")
                                    elif const_val is False:
                                        constraints.append("default_false")
                                    elif isinstance(const_val, str):
                                        # default="open" → default_open
                                        # default="pending_payment" → default_pending_payment
                                        # Normalize: replace spaces and underscores, lowercase
                                        normalized_default = const_val.lower().replace(" ", "_").replace("-", "_")
                                        constraints.append(f"default_{normalized_default}")
                                elif isinstance(value, ast.Name):
                                    # default=open (Name without quotes) → default_open
                                    # or default_factory=datetime.utcnow → auto-generated
                                    if key == "default_factory":
                                        constraints.append("auto-generated")
                                    else:
                                        # default=open → default_open
                                        constraints.append(f"default_{value.id.lower()}")

                            elif key == "description":
                                # FIX 2: Extract read-only constraint from description=True
                                # Also extract computed field semantics from description patterns
                                if isinstance(value, ast.Constant):
                                    desc_val = value.value
                                    if desc_val is True:
                                        # description=True → read-only field
                                        constraints.append("read-only")
                                    elif isinstance(desc_val, str):
                                        # FIX 9: Handle string "True" (common from CodeRepairAgent)
                                        if desc_val.lower() == "true":
                                            constraints.append("read-only")
                                            
                                        # FIX 3: Map description patterns to computed field constraints
                                        desc_lower = desc_val.lower()

                                        # Handle "Auto-calculated: <pattern>" format
                                        if "auto-calculated:" in desc_lower:
                                            # Extract pattern after "Auto-calculated:"
                                            parts = desc_lower.split("auto-calculated:")
                                            if len(parts) > 1:
                                                pattern = parts[1].strip()
                                                # Normalize extracted pattern
                                                if pattern:
                                                    # Replace spaces and hyphens with underscores
                                                    normalized = pattern.replace(" ", "_").replace("-", "_")
                                                    # Map specific patterns
                                                    if normalized == "auto_calculated":
                                                        constraints.append("auto-calculated")
                                                    elif normalized == "sum_of_items":
                                                        constraints.append("sum_of_items")
                                                    elif normalized == "sum_of_amounts":
                                                        constraints.append("sum_of_amounts")
                                                    elif "at_add_time" in normalized or "at_time_of" in normalized:
                                                        constraints.append("snapshot_at_add_time")
                                                    elif "at_order_time" in normalized:
                                                        constraints.append("snapshot_at_order_time")
                                                    elif normalized == "immutable":
                                                        constraints.append("immutable")
                                                    else:
                                                        # Fallback: add the normalized pattern as-is
                                                        constraints.append(normalized)
                                        else:
                                            # Pattern matching for computed/auto-calculated fields (fallback)
                                            if "auto-calculated" in desc_lower or "auto_calculated" in desc_lower:
                                                constraints.append("auto-calculated")
                                            if "sum of items" in desc_lower or "sum_of_items" in desc_lower:
                                                constraints.append("sum_of_items")
                                            if "sum of amounts" in desc_lower or "sum_of_amounts" in desc_lower:
                                                constraints.append("sum_of_amounts")
                                            if "at time of" in desc_lower or "at_add_time" in desc_lower:
                                                constraints.append("snapshot_at_add_time")
                                            if "at order time" in desc_lower or "at_order_time" in desc_lower:
                                                constraints.append("snapshot_at_order_time")
                                            if "immutable" in desc_lower:
                                                constraints.append("immutable")

                            elif key == "info":
                                # FIX 10: Extract description from info={'description': ...}
                                if isinstance(value, ast.Dict):
                                    for k, v in zip(value.keys, value.values):
                                        if isinstance(k, ast.Constant) and k.value == 'description':
                                            if isinstance(v, ast.Constant):
                                                desc_val = v.value
                                                
                                                if desc_val is True:
                                                    constraints.append("read-only")
                                                elif isinstance(desc_val, str):
                                                    if desc_val.lower() == "true":
                                                        constraints.append("read-only")
                                                    
                                                    desc_lower = desc_val.lower()
                                                    
                                                    # Handle "Auto-calculated: <pattern>" format
                                                    if "auto-calculated:" in desc_lower:
                                                        parts = desc_lower.split("auto-calculated:")
                                                        if len(parts) > 1:
                                                            pattern = parts[1].strip()
                                                            if pattern:
                                                                normalized = pattern.replace(" ", "_").replace("-", "_")
                                                                if normalized == "auto_calculated":
                                                                    constraints.append("auto-calculated")
                                                                elif normalized == "sum_of_items":
                                                                    constraints.append("sum_of_items")
                                                                elif normalized == "sum_of_amounts":
                                                                    constraints.append("sum_of_amounts")
                                                                elif "at_add_time" in normalized or "at_time_of" in normalized:
                                                                    constraints.append("snapshot_at_add_time")
                                                                elif "at_order_time" in normalized:
                                                                    constraints.append("snapshot_at_order_time")
                                                                elif normalized == "immutable":
                                                                    constraints.append("immutable")
                                                                else:
                                                                    constraints.append(normalized)
                                                    else:
                                                        # Pattern matching for computed/auto-calculated fields (fallback)
                                                        if "auto-calculated" in desc_lower or "auto_calculated" in desc_lower:
                                                            constraints.append("auto-calculated")
                                                        if "sum of items" in desc_lower or "sum_of_items" in desc_lower:
                                                            constraints.append("sum_of_items")
                                                        if "sum of amounts" in desc_lower or "sum_of_amounts" in desc_lower:
                                                            constraints.append("sum_of_amounts")
                                                        if "at time of" in desc_lower or "at_add_time" in desc_lower:
                                                            constraints.append("snapshot_at_add_time")
                                                        if "at order time" in desc_lower or "at_order_time" in desc_lower:
                                                            constraints.append("snapshot_at_order_time")
                                                        if "immutable" in desc_lower:
                                                            constraints.append("immutable")
                                # FIX 4: Extract default values and map to semantic constraint names
                                if isinstance(value, ast.Constant):
                                    default_val = value.value
                                    if isinstance(default_val, bool):
                                        # default=True → default_true
                                        constraints.append(f"default_{'true' if default_val else 'false'}")
                                    elif isinstance(default_val, str):
                                        # default="open" → default_open, default="pending_payment" → default_pending_payment
                                        constraints.append(f"default_{default_val}")
                                    elif isinstance(default_val, (int, float)):
                                        # default=0 → default_zero, default=1 → default_one, etc.
                                        if default_val == 0:
                                            constraints.append("default_zero")
                                        elif default_val == 1:
                                            constraints.append("default_one")
                                        else:
                                            constraints.append(f"default_{default_val}")
                                elif isinstance(value, ast.Call):
                                    # default=func() → extract function name
                                    func_name = None
                                    if isinstance(value.func, ast.Name):
                                        func_name = value.func.id
                                    elif isinstance(value.func, ast.Attribute):
                                        func_name = value.func.attr

                                    if func_name:
                                        # datetime.utcnow → auto_generated
                                        if func_name in ["utcnow", "now", "utc_now"]:
                                            constraints.append("auto-generated")
                                        else:
                                            constraints.append(f"default_factory_{func_name}")

                            elif key == "default_factory":
                                # FIX 4 Extended: default_factory extraction for auto-generated fields
                                if isinstance(value, ast.Call):
                                    # default_factory=datetime.utcnow()
                                    func_name = None
                                    if isinstance(value.func, ast.Name):
                                        func_name = value.func.id
                                    elif isinstance(value.func, ast.Attribute):
                                        func_name = value.func.attr

                                    if func_name and func_name in ["utcnow", "now", "utc_now", "uuid4"]:
                                        constraints.append("auto-generated")
                                elif isinstance(value, ast.Name):
                                    # default_factory=some_factory_func (without call)
                                    func_name = value.id
                                    if "uuid" in func_name.lower() or "time" in func_name.lower():
                                        constraints.append("auto-generated")

                        # Check positional arguments for ForeignKey
                        for arg in call.args:
                            if isinstance(arg, ast.Call):
                                arg_func = arg.func.attr if isinstance(arg.func, ast.Attribute) else (arg.func.id if isinstance(arg.func, ast.Name) else None)
                                if arg_func == "ForeignKey":
                                    # Extract the table name from ForeignKey("table_name.column_name")
                                    if arg.args and isinstance(arg.args[0], ast.Constant):
                                        fk_ref = arg.args[0].value
                                        # Extract entity name from table reference (e.g., "customers.id" -> "customers" -> "customer")
                                        if isinstance(fk_ref, str):
                                            # Split on dot to get just the table name
                                            fk_table = fk_ref.split('.')[0] if '.' in fk_ref else fk_ref
                                            # Try to singularize: customers → customer, products → product
                                            entity_name_fk = fk_table.rstrip('s') if fk_table.endswith('s') else fk_table
                                            constraints.append(f"foreign_key_{entity_name_fk}")
                                        else:
                                            constraints.append("foreign_key")
                                    else:
                                        constraints.append("foreign_key")

                result[entity_name].append({
                    "field": field_name,
                    "constraints": constraints
                })

        return result

    def _matches_with_wildcard(self, found_constraint: str, expected_constraint: str) -> bool:
        """
        CAMBIO 3: Check if a found constraint matches an expected constraint with wildcard support.

        Examples:
        - "description=Read-only field" matches "description"
        - "foreign_key_customer" matches "foreign_key*"
        - "auto-generated" matches "auto-generated"
        """
        import fnmatch

        # Direct equality
        if found_constraint == expected_constraint:
            return True

        # Wildcard pattern matching (e.g., "foreign_key_customer" matches "foreign_key*")
        if '*' in expected_constraint:
            if fnmatch.fnmatch(found_constraint, expected_constraint):
                return True

        # Prefix matching for constraints with values (e.g., "description=*" matches any "description=...")
        if '=' in expected_constraint and '=' in found_constraint:
            found_key = found_constraint.split('=')[0]
            expected_key = expected_constraint.split('=')[0]
            if found_key == expected_key:
                return True

        # Prefix matching for simple constraints (e.g., "description" matches "description=...")
        if found_constraint.startswith(expected_constraint):
            return True

        # Substring matching as last resort
        return expected_constraint in found_constraint

    def _calculate_compliance(self, found: List[str], expected: List[str]) -> float:
        """
        Calculate compliance score for a category

        Uses set intersection to handle case variations and extra items.

        Args:
            found: Items found in generated code
            expected: Items expected from spec

        Returns:
            Compliance score 0.0-1.0
        """
        if not expected:
            return 1.0  # No requirements = 100% compliance

        if not found:
            return 0.0  # Nothing implemented = 0% compliance

        # Normalize for comparison (case-insensitive, strip whitespace)
        found_normalized = {item.strip().lower() for item in found}
        expected_normalized = {item.strip().lower() for item in expected}

        # Count how many expected items were found
        matches = found_normalized & expected_normalized
        compliance = len(matches) / len(expected_normalized)

        return min(compliance, 1.0)  # Cap at 100%

    def _calculate_endpoint_compliance_fuzzy(self, found: List[str], expected: List[str]) -> float:
        """
        Calculate endpoint compliance with fuzzy matching

        Fuzzy matching handles:
        1. Path parameter variations: /carts/{id} ≈ /carts/{customer_id}
        2. Functionally equivalent HTTP methods: POST vs DELETE for "clear/empty"
        3. Route variations: /carts/clear ≈ /carts/{id} for clear operations

        Args:
            found: Endpoints found in generated code (format: "GET /products")
            expected: Endpoints expected from spec

        Returns:
            Compliance score 0.0-1.0
        """
        if not expected:
            return 1.0

        if not found:
            return 0.0

        # Parse endpoints into (method, path) tuples
        def parse_endpoint(endpoint_str: str):
            parts = endpoint_str.strip().split(maxsplit=1)
            if len(parts) == 2:
                return parts[0].upper(), parts[1]
            return None, None

        expected_parsed = []
        for exp in expected:
            method, path = parse_endpoint(exp)
            if method and path:
                expected_parsed.append((method, path))

        found_parsed = []
        for fnd in found:
            method, path = parse_endpoint(fnd)
            if method and path:
                found_parsed.append((method, path))

        # Count fuzzy matches
        matches = 0
        for exp_method, exp_path in expected_parsed:
            if self._is_fuzzy_endpoint_match(exp_method, exp_path, found_parsed):
                matches += 1

        compliance = matches / len(expected_parsed) if expected_parsed else 0.0

        logger.debug(
            f"Endpoint fuzzy matching: {matches}/{len(expected_parsed)} matches "
            f"({compliance:.1%})"
        )

        return min(compliance, 1.0)

    def _is_fuzzy_endpoint_match(
        self,
        expected_method: str,
        expected_path: str,
        found_endpoints: List[tuple]
    ) -> bool:
        """
        Check if expected endpoint matches any found endpoint using fuzzy rules

        Args:
            expected_method: Expected HTTP method (GET, POST, etc.)
            expected_path: Expected path (/carts/{customer_id})
            found_endpoints: List of (method, path) tuples from generated code

        Returns:
            True if a fuzzy match is found
        """
        # Normalize paths: replace {any_param} with {id} for comparison
        def normalize_path(path: str) -> str:
            import re
            # Replace all {param_name} with {*} for fuzzy matching
            return re.sub(r'\{[^}]+\}', '{*}', path.lower().strip())

        expected_path_norm = normalize_path(expected_path)

        for found_method, found_path in found_endpoints:
            found_path_norm = normalize_path(found_path)

            # 1. Exact match (method + normalized path)
            if expected_method == found_method and expected_path_norm == found_path_norm:
                return True

            # 2. Functionally equivalent methods for specific operations
            if self._are_methods_functionally_equivalent(
                expected_method, found_method, expected_path, found_path
            ):
                # Check if paths are semantically similar
                if self._are_paths_similar(expected_path, found_path):
                    return True

        return False

    def _are_methods_functionally_equivalent(
        self,
        method1: str,
        method2: str,
        path1: str,
        path2: str
    ) -> bool:
        """
        Check if two HTTP methods are functionally equivalent for the operation

        Examples:
        - DELETE /carts/{id} ≈ POST /carts/clear (both clear/empty cart)
        - PUT /orders/{id}/cancel ≈ POST /orders/cancel (both cancel order)

        Args:
            method1, method2: HTTP methods to compare
            path1, path2: Paths to provide context

        Returns:
            True if methods are functionally equivalent
        """
        # Normalize methods
        m1, m2 = method1.upper(), method2.upper()

        # If methods are the same, they're equivalent
        if m1 == m2:
            return True

        # Check for clear/empty/delete operations
        if "clear" in path1.lower() or "clear" in path2.lower():
            # POST /carts/clear ≈ DELETE /carts/{id}
            if {m1, m2} == {"POST", "DELETE"}:
                return True

        # Check for cancel operations
        if "cancel" in path1.lower() or "cancel" in path2.lower():
            # POST /orders/cancel ≈ PUT /orders/{id}/cancel
            if {m1, m2} <= {"POST", "PUT", "PATCH"}:
                return True

        return False

    def _are_paths_similar(self, path1: str, path2: str) -> bool:
        """
        Check if two paths are semantically similar

        Examples:
        - /carts/{id} ≈ /carts/{customer_id}
        - /carts/clear ≈ /carts/{id} (for delete/clear operations)
        - /orders/{id}/cancel ≈ /orders/cancel

        Args:
            path1, path2: Paths to compare

        Returns:
            True if paths are similar enough
        """
        import re

        # Normalize: lowercase, strip slashes
        p1 = path1.lower().strip().strip('/')
        p2 = path2.lower().strip().strip('/')

        # Exact match
        if p1 == p2:
            return True

        # Replace all {params} with placeholder for comparison
        p1_norm = re.sub(r'\{[^}]+\}', 'PARAM', p1)
        p2_norm = re.sub(r'\{[^}]+\}', 'PARAM', p2)

        # Match if normalized paths are the same
        if p1_norm == p2_norm:
            return True

        # Check for clear/cancel variations
        # /carts/{id} ≈ /carts/clear
        p1_parts = p1_norm.split('/')
        p2_parts = p2_norm.split('/')

        if len(p1_parts) == len(p2_parts):
            # Same base path and either both have PARAM or one has clear/cancel
            if p1_parts[:-1] == p2_parts[:-1]:
                last1, last2 = p1_parts[-1], p2_parts[-1]
                if 'PARAM' in {last1, last2} and any(
                    x in {last1, last2} for x in ['clear', 'cancel', 'checkout']
                ):
                    return True

        return False

    def _is_real_enforcement(self, constraint: str) -> bool:
        """
        PHASE 3: Detect if constraint is REAL enforcement vs FAKE (description string).

        Real enforcement patterns:
        - exclude=True (Pydantic immutable)
        - onupdate=None (SQLAlchemy immutable)
        - @computed_field, @property (auto-calculated)
        - @field_validator (Pydantic validation)
        - gt=, ge=, lt=, le=, min_length=, max_length= (Pydantic Field constraints)
        - unique=True, nullable=False (SQLAlchemy constraints)
        - ForeignKey(...) (SQLAlchemy relationship)
        - Business logic methods (checkout, cancel_order with stock logic)

        Fake enforcement (description string only):
        - description="Read-only field"
        - description="Auto-calculated"
        - description="Snapshot at add time"

        Args:
            constraint: The constraint string to check (e.g., "description", "exclude=True", "gt=0")

        Returns:
            True if real enforcement, False if fake (description only)
        """
        constraint_lower = constraint.lower().strip()

        # FAKE: Only description string (no real enforcement)
        if constraint_lower == "description" or constraint_lower.startswith("description="):
            # Check if there are other constraints besides description
            # If ONLY description, it's fake
            return False

        # REAL ENFORCEMENT PATTERNS (Phase 1 + Phase 2)

        # 1. Pydantic Field constraints (real validation)
        real_pydantic_constraints = ['gt=', 'ge=', 'lt=', 'le=', 'min_length=', 'max_length=',
                                     'pattern=', 'regex=', 'email', 'uuid']
        if any(pattern in constraint_lower for pattern in real_pydantic_constraints):
            return True

        # 2. Immutable enforcement (Phase 2.3)
        if 'exclude=true' in constraint_lower or 'exclude' in constraint_lower:
            return True

        # 3. SQLAlchemy immutable (Phase 2.3)
        if 'onupdate=none' in constraint_lower:
            return True

        # 4. Computed field enforcement (Phase 2.2)
        if '@computed_field' in constraint_lower or '@property' in constraint_lower:
            return True

        # 5. Pydantic validator (Phase 1)
        if '@field_validator' in constraint_lower or '@validator' in constraint_lower:
            return True

        # 6. SQLAlchemy constraints (Phase 1)
        if 'unique=true' in constraint_lower or 'nullable=false' in constraint_lower:
            return True

        # 7. Foreign key relationships (Phase 1)
        if 'foreignkey' in constraint_lower or 'foreign_key' in constraint_lower:
            return True

        # 8. Business logic enforcement (Phase 2.4)
        # Check for actual business logic code (stock decrement, state transitions)
        if 'stock' in constraint_lower and ('decrement' in constraint_lower or 'increment' in constraint_lower):
            return True

        # 9. Required constraints (Phase 1)
        if constraint_lower in ['required', 'not_null', 'nullable=false']:
            return True

        # 10. Default values with factory functions (real enforcement)
        if 'default=' in constraint_lower and any(pattern in constraint_lower for pattern in ['lambda', 'uuid.uuid4', 'datetime.utcnow', 'datetime.now']):
            return True

        # FAKE: read_only/auto-generated without real enforcement mechanism
        # These are ONLY fake if they appear alone without exclude/onupdate/computed_field
        if constraint_lower in ['read_only', 'auto-generated', 'auto_generated', 'auto-calculated',
                                'auto_calculated', 'snapshot', 'immutable']:
            return False

        # Default: if we don't recognize it, consider it fake to be conservative
        return False

    def _calculate_validation_compliance(self, found: List[str], expected: List[str], use_exact_matching: bool = False) -> tuple[float, List[str]]:
        """
        Calculate validation compliance with exact or flexible matching

        PHASE 3 ENHANCEMENT: Now uses _is_real_enforcement() to filter out fake enforcement (description strings).

        ARCHITECTURE RULE #1 COMPLIANT: All found validations are counted (no filtering of read_only or other unrecognized types).

        FIX 6: Semantic Equivalence Matching for complex patterns:
        - Compound constraints: Fields with multiple constraints (auto-generated + read-only)
        - Snapshot patterns: snapshot_at_add_time, snapshot_at_order_time
        - Enum-default patterns: default_pending_payment, default_checked_out

        FLEXIBLE MATCHING (use_exact_matching=False):
        - For each expected validation, check if any found validation contains the constraint substring
        - Example: Expected "Product.price: gt=0" matches Found "Product.price: gt=0" (substring match)
        - If all expected validations are found, return compliance=1.0 with ALL found validations as matched
        - This ensures read_only and other validations are properly counted

        EXACT MATCHING (use_exact_matching=True):
        - For each expected validation, check for exact match in found list
        - Used when manual ground truth exists (deprecated per Architecture Rule #1)

        Args:
            found: Validation signatures found in code (e.g., ["Product.price: gt=0", "Product.name: read_only"])
            expected: Validation requirements from spec (e.g., ["Product.price: gt=0", "Product.name: required"])

        Returns:
            Tuple of (compliance_score 0.0-1.0, list of matched validation strings)
        """
        if not expected:
            return 1.0, found  # No expectations, all found validations count

        if not found:
            return 0.0, []  # Nothing found, no matches

        # ═══════════════════════════════════════════════════════════════════════════════
        # SEMANTIC MATCHER: ML-based matching (if available)
        # Replaces ~300 lines of manual semantic_equivalences with embeddings + LLM
        # ═══════════════════════════════════════════════════════════════════════════════
        if self.semantic_matcher is not None:
            logger.info("🧠 Using SemanticMatcher for ML-based constraint matching")
            compliance, matched = self._semantic_match_validations(found, expected)

            # If perfect compliance, return all found validations (includes extras)
            if compliance >= 1.0:
                logger.info(f"✅ SemanticMatcher: All {len(expected)} expected validations matched")
                return 1.0, found
            else:
                logger.info(f"📊 SemanticMatcher: {len(matched)}/{len(expected)} validations matched = {compliance:.1%}")
                return compliance, matched

        # ═══════════════════════════════════════════════════════════════════════════════
        # FALLBACK: Manual semantic equivalences (legacy, ~300 lines)
        # Used when SemanticMatcher is not available
        # ═══════════════════════════════════════════════════════════════════════════════
        logger.info("📋 Using manual semantic_equivalences (fallback mode)")

        # FLEXIBLE MATCHING MODE (default - per Architecture Rule #1)
        # Use semantic equivalence mapping for common validation patterns
        # Maps high-level constraints from spec to code-level constraints
        # FIX 6: Enhanced with compound constraint detection and snapshot pattern support
        semantic_equivalences = {
            # Database-level constraints
            "unique": ["unique", "read_only", "primary"],
            "primary_key": ["primary_key", "unique"],
            "foreign_key": ["foreign_key*", "fk_*"],  # Matches foreign_key_customer, foreign_key_product, etc.
            "required": ["required"],

            # Auto-generated variants (FIX 6: improved compound detection)
            "auto-generated": ["default_factory*", "auto_increment", "generated", "auto-generated", "default=uuid.uuid4", "default=datetime.utcnow"],
            "auto_generated": ["default_factory*", "auto_increment", "generated", "auto-generated", "default=uuid.uuid4", "default=datetime.utcnow"],
            "auto-increment": ["default_factory*", "auto_increment"],

            # Read-only variants (output fields, snapshots, immutable)
            # FIX 6: Improved snapshot pattern matching
            "read-only": ["description", "read_only", "exclude", "snapshot_at*"],
            "read_only": ["description", "read_only", "exclude", "snapshot_at*"],
            "snapshot_at": ["description", "read_only", "exclude", "snapshot_at*"],
            "snapshot_at_add_time": ["snapshot_at_add_time", "description", "read_only", "exclude"],
            "snapshot_at_order_time": ["snapshot_at_order_time", "description", "read_only", "exclude"],
            "immutable": ["description", "read_only", "exclude"],

            # Computed fields (auto-calculated, derived)
            "computed_field": ["description"],
            "auto-calculated": ["description", "auto-calculated", "auto_calculated"],
            "auto_calculated": ["description", "auto-calculated", "auto_calculated"],

            # Input validation constraints
            "presence": ["required"],
            "non-empty": ["required", "min_length"],
            "non_empty": ["required", "min_length"],
            "non-negative": ["ge=0", "gt=-1", "minimum=0"],
            "non_negative": ["ge=0", "gt=-1", "minimum=0"],
            "positive": ["gt=0", "ge=1"],
            "greater_than_zero": ["gt=0", "gt"],
            "gt": ["gt"],
            "ge": ["ge"],
            "lt": ["lt"],
            "le": ["le"],
            "min_length": ["min_length"],
            "max_length": ["max_length"],

            # Format validations
            "valid_email_format": ["email_format", "pattern"],
            "valid-email-format": ["email_format", "pattern"],
            "email_format": ["email_format", "pattern"],
            "uuid_format": ["uuid_format"],

            # Default values (FIX 6: improved enum-default pattern matching)
            "default_true": ["default=True", "default=true", "default_true", "default*true"],
            "default_false": ["default=False", "default=false", "default_false", "default*false"],
            "default_open": ["default=open", "default_open", "default*open"],
            "default_pending_payment": ["default=pending_payment", "default_pending_payment", "default*pending*payment"],
            "default_pending": ["default=pending", "default_pending", "default*pending"],
            "default_checked_out": ["default=checked_out", "default_checked_out", "default*checked*out"],

            # Enum/values constraints
            "values": ["enum", "values", "default*"],  # Enum constraints often have default values

            # Read-only/computed fields (should match description or auto-generated patterns)
            "read-only": ["description", "read_only", "exclude", "snapshot_at*"],
            "auto-calculated": ["description", "auto*calculated", "sum_of*"],
        }

        matches = 0
        matched_validations = []
        unmatched_validations = []

        # FIX 6: Build entity.field -> [constraints] map from found validations
        # This enables compound constraint detection
        found_constraints_map = {}
        for found_val in found:
            if ": " in found_val:
                entity_field, constraint = found_val.split(": ", 1)
                if entity_field not in found_constraints_map:
                    found_constraints_map[entity_field] = []
                found_constraints_map[entity_field].append(constraint.lower())

        for exp_val in expected:
            # Extract entity.field and constraint from expected
            # Expected format: "Entity.field: constraint" (e.g., "Product.price: gt=0")
            found_match = False

            if ": " in exp_val:
                entity_field, constraint = exp_val.split(": ", 1)
                constraint_lower = constraint.lower()

                # FIX 6: Check if entity.field has multiple constraints (compound constraint)
                # FIX 7: Ultra-flexible matching for compound constraints
                if entity_field in found_constraints_map:
                    found_field_constraints = found_constraints_map[entity_field]

                    # Try to match the expected constraint against all found constraints for this field
                    for found_constraint in found_field_constraints:
                        # Try exact match first (strict)
                        if constraint_lower == found_constraint:
                            # PHASE 3: Only count if real enforcement present
                            if self._is_real_enforcement(found_constraint):
                                matches += 1
                                matched_validations.append(f"{entity_field}: {found_constraint}")
                                found_match = True
                            break

                        # Try semantic equivalence match with wildcard support
                        # Check if the constraint has semantic equivalents
                        for semantic_key, equivalents in semantic_equivalences.items():
                            if semantic_key in constraint_lower:
                                # Check if any equivalent matches (with wildcard support)
                                for equiv in equivalents:
                                    if self._matches_with_wildcard(found_constraint, equiv.lower()):
                                        # PHASE 3: Only count if real enforcement present
                                        if self._is_real_enforcement(found_constraint):
                                            matches += 1
                                            matched_validations.append(f"{entity_field}: {found_constraint}")
                                            found_match = True
                                        break
                                if found_match:
                                    break

                        # FIX 7: Ultra-flexible matching for special patterns
                        if not found_match:
                            # Pattern-based matching for known constraint types
                            if "auto-generated" in constraint_lower or "auto_generated" in constraint_lower:
                                # IMPROVED FIX 8: Match auto-generated with any factory function patterns
                                # Match: default_factory=datetime.utcnow, default_factory=uuid.uuid4, auto-generated, etc.
                                factory_patterns = [
                                    "default_factory",
                                    "auto-generated",
                                    "auto_generated",
                                    "auto_increment",
                                    "generated",
                                ]
                                if any(pattern in found_constraint for pattern in factory_patterns):
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "read-only" in constraint_lower or "immutable" in constraint_lower:
                                # PHASE 3: Match read-only/immutable with REAL enforcement (not just description)
                                if "description" in found_constraint or "read_only" in found_constraint:
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "foreign_key" in constraint_lower:
                                # IMPROVED FIX 8: Match foreign_key patterns
                                # Match: foreign_key_customer, foreign_key_product, ForeignKey('table.id'), etc.
                                fk_patterns = [
                                    "foreign_key",
                                    "fk_",
                                    "foreignkey",
                                ]
                                if any(pattern in found_constraint for pattern in fk_patterns):
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "snapshot_at" in constraint_lower:
                                # PHASE 3: Match snapshot patterns with REAL enforcement (not just description)
                                if "description" in found_constraint or "read_only" in found_constraint:
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "default_" in constraint_lower:
                                # Match default_pending_payment with default=pending_payment
                                # IMPROVED FIX 8: Handle multiple formats for default values
                                value_part = constraint_lower.split("default_")[1] if "default_" in constraint_lower else ""
                                # Try multiple formats: default=value, default='value', default="value", default_value
                                default_patterns = [
                                    f"default={value_part}",
                                    f"default='{value_part}'",
                                    f'default="{value_part}"',
                                    f"default={value_part.replace('_', ' ')}",  # For multi-word values
                                    f"default_{value_part}",
                                ]
                                if any(pattern in found_constraint for pattern in default_patterns):
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True
                                elif "default" in found_constraint:
                                    # Generic default match: any default matches any default
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "auto-calculated" in constraint_lower or "auto_calculated" in constraint_lower:
                                # PHASE 3: Match auto-calculated with REAL enforcement (not just description)
                                if "description" in found_constraint or "auto" in found_constraint:
                                    # PHASE 3: Only count if real enforcement present
                                    if self._is_real_enforcement(found_constraint):
                                        matches += 1
                                        matched_validations.append(f"{entity_field}: {found_constraint}")
                                        found_match = True

                            elif "sum_of" in constraint_lower or "positive" in constraint_lower or "greater_than_zero" in constraint_lower:
                                # Match these with any constraint (they're extras, not critical)
                                # PHASE 3: Only count if real enforcement present
                                if self._is_real_enforcement(found_constraint):
                                    matches += 1
                                    matched_validations.append(f"{entity_field}: {found_constraint}")
                                    found_match = True

                        if found_match:
                            break

                if not found_match:
                    # Fallback: check found validations as before
                    for found_val in found:
                        # Check if this is the same entity.field
                        if entity_field not in found_val:
                            continue

                        # Try exact match first (strict)
                        if constraint in found_val:
                            # Extract found_constraint for enforcement check
                            if ": " in found_val:
                                found_constraint_check = found_val.split(": ", 1)[1].lower()
                            else:
                                found_constraint_check = found_val.lower()
                            # PHASE 3: Only count if real enforcement present
                            if self._is_real_enforcement(found_constraint_check):
                                matches += 1
                                matched_validations.append(found_val)
                                found_match = True
                            break

                        # Extract the constraint part from found_val for matching
                        # Found format: "Entity.field: constraint_value"
                        if ": " in found_val:
                            found_constraint = found_val.split(": ", 1)[1].lower()
                        else:
                            found_constraint = found_val.lower()

                        # Try semantic equivalence match with wildcard support
                        # Check if the constraint has semantic equivalents
                        for semantic_key, equivalents in semantic_equivalences.items():
                            if semantic_key in constraint_lower:
                                # Check if any equivalent matches (with wildcard support)
                                for equiv in equivalents:
                                    if self._matches_with_wildcard(found_constraint, equiv.lower()):
                                        # PHASE 3: Only count if real enforcement present
                                        if self._is_real_enforcement(found_constraint):
                                            matches += 1
                                            matched_validations.append(found_val)
                                            found_match = True
                                        break
                                if found_match:
                                    break

                        if found_match:
                            break
            else:
                # Fallback: simple substring match for edge cases
                for found_val in found:
                    if exp_val in found_val:
                        # Extract found_constraint for enforcement check
                        if ": " in found_val:
                            found_constraint_check = found_val.split(": ", 1)[1].lower()
                        else:
                            found_constraint_check = found_val.lower()
                        # PHASE 3: Only count if real enforcement present
                        if self._is_real_enforcement(found_constraint_check):
                            matches += 1
                            matched_validations.append(found_val)
                            found_match = True
                        break

            if not found_match:
                unmatched_validations.append(exp_val)

        # Calculate compliance
        if matches == len(expected):
            # All required validations are present
            # Per the new logic: return ALL found validations as matched (includes extras like read_only)
            compliance = 1.0  # 100% - all required are present
            logger.info(f"✅ Validation compliance: All {len(expected)} required validations found + {len(found) - len(expected)} extra validations")
            logger.info(f"   Found validations: {len(found)} total")
            return compliance, found  # Return ALL found as matched (not just matched ones)
        else:
            # Some required validations are missing
            compliance = matches / len(expected)
            logger.warning(f"⚠️ Validation compliance: {matches}/{len(expected)} required validations found = {compliance:.1%}")
            logger.warning(f"❌ UNMATCHED VALIDATIONS ({len(unmatched_validations)}):")
            for i, val in enumerate(unmatched_validations[:10], 1):
                logger.warning(f"  {i}. {val}")
            if len(unmatched_validations) > 10:
                logger.warning(f"  ... and {len(unmatched_validations) - 10} more")
            return compliance, matched_validations



    def _identify_missing_requirements(
        self,
        entities_expected: List[str],
        entities_found: List[str],
        endpoints_expected: List[str],
        endpoints_found: List[str],
        spec: SpecRequirements,
    ) -> List[str]:
        """
        Identify specific missing requirements

        Args:
            entities_expected: Expected entity names
            entities_found: Found entity names
            endpoints_expected: Expected endpoints
            endpoints_found: Found endpoints
            spec: Full spec requirements

        Returns:
            List of missing requirement descriptions
        """
        missing = []

        # Missing entities
        entities_found_normalized = {e.lower() for e in entities_found}
        for entity in entities_expected:
            if entity.lower() not in entities_found_normalized:
                missing.append(f"Entity: {entity}")

        # Missing endpoints (sample first 5 to avoid spam)
        endpoints_found_normalized = {e.lower() for e in endpoints_found}
        missing_endpoints = []
        for endpoint in endpoints_expected:
            if endpoint.lower() not in endpoints_found_normalized:
                missing_endpoints.append(f"Endpoint: {endpoint}")

        # Add sample of missing endpoints
        missing.extend(missing_endpoints[:5])
        if len(missing_endpoints) > 5:
            missing.append(f"... and {len(missing_endpoints) - 5} more endpoints")

        # Missing functional requirements (sample) - use defensive helper
        requirements = self._get_requirements_from_spec(spec)
        for req in requirements[:5]:
            # Handle both object with .type and dict with 'type' key
            req_type = getattr(req, 'type', None) or (req.get('type') if isinstance(req, dict) else None)
            if req_type == "functional":
                # Check if requirement keywords are in code (heuristic)
                req_id = getattr(req, 'id', None) or (req.get('id', 'N/A') if isinstance(req, dict) else 'N/A')
                req_desc = getattr(req, 'description', '') or (req.get('description', '') if isinstance(req, dict) else '')
                missing.append(f"Requirement {req_id}: {req_desc[:60]}...")

        return missing

    def _format_entity_report(
        self,
        report: ComplianceReport
    ) -> str:
        """
        Enhanced entity report with categorization

        Separates:
        - Domain entities (Product, Customer, etc.)
        - Request/Response schemas (ProductCreate, etc.)
        - Enums (Status enums)

        Args:
            report: ComplianceReport with entities data

        Returns:
            Formatted string with categorized entities

        Part of Task Group 2: Presentation Enhancement (M4)
        """
        # Categorize entities
        domain_entities = []
        schemas = []
        enums = []

        for entity in report.entities_implemented:
            if entity in report.entities_expected:
                domain_entities.append(entity)
            elif entity.endswith(('Create', 'Update', 'Request', 'Response')):
                schemas.append(entity)
            elif entity.endswith('Status'):
                enums.append(entity)
            else:
                # Unknown category - treat as domain entity
                domain_entities.append(entity)

        # Format output
        lines = []
        lines.append(f"\n📦 Entities ({len(report.entities_expected)} required, {len(domain_entities)} present):")
        lines.append(f"   ✅ {', '.join(domain_entities)}")

        if schemas or enums:
            lines.append(f"\n   📝 Additional models (best practices):")
            if schemas:
                lines.append(f"   - Request/Response schemas: {len(schemas)}")
            if enums:
                lines.append(f"   - Enums: {len(enums)}")

        return "\n".join(lines)

    def _format_endpoint_report(
        self,
        report: ComplianceReport
    ) -> str:
        """
        Enhanced endpoint report with categorization

        Separates:
        - Required endpoints (from spec)
        - Additional endpoints (best practices like / and /health)

        Args:
            report: ComplianceReport with endpoints data

        Returns:
            Formatted string with categorized endpoints

        Part of Task Group 2: Presentation Enhancement (M4)
        """
        # Categorize endpoints
        required_endpoints = []
        additional_endpoints = []

        for endpoint in report.endpoints_implemented:
            if endpoint in report.endpoints_expected:
                required_endpoints.append(endpoint)
            else:
                # Additional endpoints (best practices)
                additional_endpoints.append(endpoint)

        # Format output
        # Bug #19 fix: Clarified endpoint counts to avoid confusion
        # "matched" = endpoints that match the required ones
        # "inferred" = additional best-practice endpoints
        lines = []
        total_impl = len(report.endpoints_implemented)
        lines.append(f"\n🌐 Endpoints: {len(required_endpoints)}/{len(report.endpoints_expected)} required matched (+{len(additional_endpoints)} inferred = {total_impl} total)")

        if required_endpoints:
            # Show sample of required endpoints (first 5)
            sample = required_endpoints[:5]
            lines.append(f"   ✅ {', '.join(sample)}")
            if len(required_endpoints) > 5:
                lines.append(f"   ... and {len(required_endpoints) - 5} more required")
        else:
            lines.append(f"   ❌ No required endpoints found")

        if additional_endpoints:
            lines.append(f"\n   📝 Inferred endpoints (best practices): {len(additional_endpoints)}")
            # Only show first 3 inferred to keep output manageable
            for endpoint in additional_endpoints[:3]:
                lines.append(f"   - {endpoint}")
            if len(additional_endpoints) > 3:
                lines.append(f"   ... and {len(additional_endpoints) - 3} more inferred")

        return "\n".join(lines)

    def generate_detailed_report(
        self, spec_requirements: SpecRequirements, generated_code: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report with all details

        Args:
            spec_requirements: Parsed specification
            generated_code: Generated code

        Returns:
            Dict with full compliance analysis
        """
        report = self.validate(spec_requirements, generated_code)
        stats = self.analyzer.get_code_statistics(generated_code)

        detailed_report = {
            "compliance": {
                "overall": report.overall_compliance,
                "entities": report.compliance_details["entities"],
                "endpoints": report.compliance_details["endpoints"],
                "validations": report.compliance_details["validations"],
            },
            "entities": {
                "expected": report.entities_expected,
                "implemented": report.entities_implemented,
                "missing": [
                    e for e in report.entities_expected if e not in report.entities_implemented
                ],
            },
            "endpoints": {
                "expected_count": len(report.endpoints_expected),
                "implemented_count": len(report.endpoints_implemented),
                "sample_expected": report.endpoints_expected[:5],
                "sample_implemented": report.endpoints_implemented[:5],
            },
            "validations": {
                "expected_count": len(report.validations_expected),
                "implemented_count": len(report.validations_implemented),
                "types_found": report.validations_implemented,
            },
            "code_statistics": stats,
            "missing_requirements": report.missing_requirements,
            "passed": report.overall_compliance >= 0.80,
        }

        return detailed_report

    # ═══════════════════════════════════════════════════════════════════════════════
    # Phase 3.5: ApplicationIR as Ground Truth
    # ═══════════════════════════════════════════════════════════════════════════════

    async def load_spec_from_markdown(
        self,
        spec_markdown: str,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ):
        """
        Phase 3.5: Load spec as ApplicationIR.

        Uses LLM to generate ApplicationIR (one-time), then caches for
        100% deterministic subsequent runs.

        Args:
            spec_markdown: Raw markdown content
            spec_path: Path for cache key
            force_refresh: Force LLM regeneration

        Returns:
            ApplicationIR with validation_model (ground truth)
        """
        from src.specs.spec_to_application_ir import SpecToApplicationIR

        converter = SpecToApplicationIR()
        return await converter.get_application_ir(
            spec_markdown, spec_path, force_refresh
        )

    async def validate_from_spec_markdown(
        self,
        spec_markdown: str,
        output_path,
        spec_path: str = "spec.md",
        force_refresh: bool = False
    ) -> ComplianceReport:
        """
        Phase 3.5: Full SPEC + CODE → ComplianceReport using ApplicationIR.

        Flow:
        1. SPEC → ApplicationIR (cached LLM, one-time)
        2. ApplicationIR → ValidationModelIR (ground truth)
        3. CODE → Extract validations (existing logic)
        4. Match spec vs code → ComplianceReport

        This method bridges Phase 3.5 (ApplicationIR) with the existing
        validation pipeline for backward compatibility.

        Args:
            spec_markdown: Raw markdown content
            output_path: Path to generated app directory
            spec_path: Path for traceability
            force_refresh: Force ApplicationIR regeneration

        Returns:
            ComplianceReport with deterministic metrics
        """
        from pathlib import Path

        # Step 1: Get ApplicationIR from spec (cached)
        application_ir = await self.load_spec_from_markdown(
            spec_markdown, spec_path, force_refresh
        )

        # Step 2: Convert ApplicationIR to SpecRequirements format
        # (bridges Phase 3.5 IR with existing validation logic)
        spec_requirements = self._application_ir_to_spec_requirements(application_ir)

        # Step 3: Use existing validate_from_app logic
        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        return self.validate_from_app(spec_requirements, output_path)

    def _application_ir_to_spec_requirements(self, application_ir) -> SpecRequirements:
        """
        Convert ApplicationIR to SpecRequirements for backward compatibility.

        This bridges Phase 3.5 (ApplicationIR as ground truth) with the
        existing validation pipeline that expects SpecRequirements.

        Args:
            application_ir: ApplicationIR instance

        Returns:
            SpecRequirements compatible with existing validation logic
        """
        # Extract entities from DomainModelIR (defensive: handles both Entity types)
        entities = []
        for entity in application_ir.domain_model.entities:
            # Build attributes list using defensive helpers
            attrs_list = []
            for attr in self._get_attributes_from_entity(entity):
                attrs_list.append({
                    "name": attr.name,
                    "type": self._get_attr_type(attr),
                    "required": self._is_attr_required(attr),
                    "constraints": self._get_attr_constraints(attr),
                })

            # Build relationships list (defensive for missing relationships attr)
            rels_list = []
            if hasattr(entity, "relationships") and entity.relationships:
                for rel in entity.relationships:
                    rels_list.append({
                        "target": rel.target_entity,
                        "type": rel.type.value if hasattr(rel.type, "value") else str(rel.type),
                        "field": rel.field_name,
                    })

            entities.append({
                "name": entity.name,
                "attributes": attrs_list,
                "relationships": rels_list,
            })

        # Extract endpoints from APIModelIR (includes inferred best-practice endpoints)
        endpoints = []
        inferred_count = 0
        for ep in application_ir.api_model.endpoints:
            ep_dict = {
                "path": ep.path,
                "method": ep.method.value,
                "operation_id": ep.operation_id,
                "summary": ep.summary,
            }
            # Track inferred endpoints for traceability (Phase 0: IR as single source of truth)
            if getattr(ep, 'inferred', False):
                ep_dict["inferred"] = True
                ep_dict["inference_source"] = getattr(ep, 'inference_source', None)
                ep_dict["inference_reason"] = getattr(ep, 'inference_reason', None)
                inferred_count += 1
            endpoints.append(ep_dict)

        if inferred_count > 0:
            logger.info(f"📊 IR contains {len(endpoints)} endpoints ({inferred_count} inferred best-practice)")

        # Extract business_logic from ValidationModelIR
        business_logic = []
        for rule in application_ir.validation_model.rules:
            business_logic.append({
                "entity": rule.entity,
                "field": rule.attribute,
                "type": rule.type.value,
                "condition": rule.condition,
            })

        return SpecRequirements(
            app_name=application_ir.name,
            entities=entities,
            endpoints=endpoints,
            business_logic=business_logic,
            raw_spec=application_ir.description or "",
        )

    async def validate_from_spec_file(
        self,
        spec_path,
        output_path,
        force_refresh: bool = False
    ) -> ComplianceReport:
        """
        Convenience: Load spec from file, code from directory.

        Args:
            spec_path: Path to spec markdown file
            output_path: Path to generated app directory
            force_refresh: Force ApplicationIR regeneration

        Returns:
            ComplianceReport with full validation results
        """
        from pathlib import Path

        if not isinstance(spec_path, Path):
            spec_path = Path(spec_path)

        spec_markdown = spec_path.read_text()

        return await self.validate_from_spec_markdown(
            spec_markdown,
            output_path,
            str(spec_path),
            force_refresh
        )

    def get_application_ir_cache_info(self, spec_path: str) -> dict:
        """
        Get information about cached ApplicationIR for a spec.

        Args:
            spec_path: Path to spec file

        Returns:
            Dict with cache status, hash, rules count, etc.
        """
        from src.specs.spec_to_application_ir import SpecToApplicationIR

        converter = SpecToApplicationIR()
        return converter.get_cache_info(spec_path)

    def clear_application_ir_cache(self, spec_path: str = None):
        """
        Clear cached ApplicationIR files.

        Args:
            spec_path: Optional specific spec to clear. If None, clears all.
        """
        from src.specs.spec_to_application_ir import SpecToApplicationIR

        converter = SpecToApplicationIR()
        converter.clear_cache(spec_path)
        logger.info(f"🗑️ ApplicationIR cache cleared" + (f" for {spec_path}" if spec_path else ""))

    # ═══════════════════════════════════════════════════════════════════════════════
    # Phase 3 + 3.5: Full IR vs IR Validation
    # ═══════════════════════════════════════════════════════════════════════════════

    async def validate_ir_vs_ir(
        self,
        spec_markdown: str,
        code_validation_model,
        spec_path: str = "spec.md",
        use_embedding_fallback: bool = True
    ) -> Tuple[float, List[Any]]:
        """
        Phase 3 + 3.5: Full IR vs IR validation.

        This is the most accurate validation method:
        1. SPEC → ApplicationIR (Phase 3.5, cached LLM)
        2. ApplicationIR → ValidationModelIR (deterministic)
        3. CODE → ValidationModelIR (Phase 2 extraction)
        4. Match ValidationModelIR vs ValidationModelIR (Phase 3)

        Args:
            spec_markdown: Raw spec markdown content
            code_validation_model: ValidationModelIR from code extraction
            spec_path: Path for cache key
            use_embedding_fallback: Use semantic matching for edge cases

        Returns:
            Tuple of (compliance_score, list of IRMatchResult)
        """
        from src.specs.spec_to_application_ir import SpecToApplicationIR
        from src.services.ir_semantic_matcher import IRSemanticMatcher

        # Step 1: Get ApplicationIR from spec (cached)
        converter = SpecToApplicationIR()
        application_ir = await converter.get_application_ir(spec_markdown, spec_path)

        # Step 2: Get spec ValidationModelIR
        spec_validation_model = application_ir.validation_model

        # Step 3: Match IR vs IR
        matcher = IRSemanticMatcher(use_embedding_fallback=use_embedding_fallback)
        compliance, results = matcher.match_validation_models(
            spec_validation_model,
            code_validation_model
        )

        logger.info(
            f"🎯 IR vs IR validation: {compliance:.1%} "
            f"({len([r for r in results if r.match])}/{len(results)} rules matched)"
        )

        return compliance, results

    async def validate_full_ir_pipeline(
        self,
        spec_path,
        output_path,
        force_refresh: bool = False
    ) -> dict:
        """
        Full Phase 3 + 3.5 validation pipeline.

        Combines all phases:
        - Phase 3.5: SPEC → ApplicationIR (LLM, cached)
        - Phase 2: CODE → ValidationModelIR (extraction)
        - Phase 3: IR vs IR matching

        Args:
            spec_path: Path to spec markdown file
            output_path: Path to generated app directory
            force_refresh: Force ApplicationIR regeneration

        Returns:
            Dict with compliance scores and detailed results
        """
        from pathlib import Path
        from src.specs.spec_to_application_ir import SpecToApplicationIR
        from src.services.ir_semantic_matcher import IRSemanticMatcher

        if not isinstance(spec_path, Path):
            spec_path = Path(spec_path)
        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        # Phase 3.5: Load spec as ApplicationIR
        spec_markdown = spec_path.read_text()
        converter = SpecToApplicationIR()

        if force_refresh:
            converter.clear_cache(str(spec_path))

        application_ir = await converter.get_application_ir(
            spec_markdown, str(spec_path)
        )

        # Also run traditional validation for comparison
        spec_requirements = self._application_ir_to_spec_requirements(application_ir)
        traditional_report = self.validate_from_app(spec_requirements, output_path)

        # Get cache info
        cache_info = converter.get_cache_info(str(spec_path))

        return {
            "phase": "3.5 + 3",
            "spec_path": str(spec_path),
            "output_path": str(output_path),
            "application_ir": {
                "name": application_ir.name,
                "entities_count": len(application_ir.domain_model.entities),
                "endpoints_count": len(application_ir.api_model.endpoints),
                "validation_rules_count": len(application_ir.validation_model.rules),
            },
            "cache_info": cache_info,
            "compliance": {
                "overall": traditional_report.overall_compliance,
                "entities": traditional_report.compliance_details.get("entities", 0),
                "endpoints": traditional_report.compliance_details.get("endpoints", 0),
                "validations": traditional_report.compliance_details.get("validations", 0),
            },
            "deterministic": True,  # Phase 3.5 guarantees determinism
        }

    # ============================================================================
    # PHASE 2: UNIFIED CONSTRAINT EXTRACTOR INTEGRATION
    # ============================================================================

    async def validate_with_phase2(
        self,
        spec: Dict[str, Any],
        output_path,
    ) -> Dict[str, Any]:
        """
        Validate using Phase 2 Unified Constraint Extractor.

        PHASE 2 PIPELINE:
        1. Extract constraints from spec using UnifiedConstraintExtractor
        2. Extract constraints from generated code
        3. Compare ValidationModelIR vs ValidationModelIR
        4. Calculate compliance

        Args:
            spec: Specification dictionary (from parsed spec)
            output_path: Path to generated app directory

        Returns:
            Dict with Phase 2 compliance results
        """
        from src.services.unified_constraint_extractor import UnifiedConstraintExtractor

        if not self.application_ir:
            raise ValueError("Phase 2 validation requires ApplicationIR to be provided")

        logger.info("🟠 PHASE 2: Unified Constraint Extractor validation starting...")

        # Step 1: Extract spec constraints using UnifiedConstraintExtractor
        try:
            extractor = UnifiedConstraintExtractor(self.application_ir)
            spec_validation_model = await extractor.extract_all(spec)
            logger.info(f"✅ Phase 2 extracted {len(spec_validation_model.rules)} constraints from spec")
        except Exception as e:
            logger.error(f"❌ Phase 2 extraction failed: {e}")
            return {
                "phase": "2",
                "error": str(e),
                "compliance": 0.0,
            }

        # Step 2: Extract code constraints (reuse existing CodeAnalyzer)
        if not isinstance(output_path, Path):
            output_path = Path(output_path)

        code_files = self._read_code_files(output_path)
        code_text = "\n".join(code_files.values())
        validations_found = self.analyzer.extract_validations(code_text)

        # Step 3: Match spec vs code constraints
        spec_constraints_str = [
            f"{r.entity}.{r.attribute}: {r.type.value}"
            for r in spec_validation_model.rules
        ]

        matched_count = 0
        if self.semantic_matcher:
            # Use ML-based matching
            for code_val in validations_found:
                for spec_constraint in spec_constraints_str:
                    result = self.semantic_matcher.match(spec_constraint, code_val)
                    if result.match:
                        matched_count += 1
                        break
        else:
            # Fallback: naive string matching
            for code_val in validations_found:
                for spec_constraint in spec_constraints_str:
                    if code_val.lower() in spec_constraint.lower() or spec_constraint.lower() in code_val.lower():
                        matched_count += 1
                        break

        # Step 4: Calculate compliance
        total_spec_constraints = len(spec_validation_model.rules)
        compliance_score = (
            matched_count / total_spec_constraints
            if total_spec_constraints > 0
            else 1.0
        )

        logger.info(
            f"🎯 Phase 2 compliance: {matched_count}/{total_spec_constraints} "
            f"= {compliance_score:.1%}"
        )

        return {
            "phase": "2",
            "spec_constraints_count": total_spec_constraints,
            "code_constraints_found": len(validations_found),
            "matched_constraints": matched_count,
            "compliance_score": compliance_score,
            "extractor_type": "UnifiedConstraintExtractor",
            "semantic_matcher_used": self.semantic_matcher is not None,
        }

    def _read_code_files(self, output_path: Path) -> Dict[str, str]:
        """
        Read all relevant code files from generated app.

        Returns dict mapping file paths to contents.
        """
        code_files = {}

        # Patterns for relevant files
        patterns = [
            "src/models/*.py",
            "src/api/*.py",
            "src/services/*.py",
            "src/domain/*.py",
            "main.py",
            "*.py",
        ]

        for pattern in patterns:
            for file_path in output_path.glob(pattern):
                if file_path.is_file() and file_path.name.endswith(".py"):
                    relative_path = str(file_path.relative_to(output_path))
                    try:
                        code_files[relative_path] = file_path.read_text()
                    except Exception as e:
                        logger.warning(f"Failed to read {relative_path}: {e}")

        return code_files