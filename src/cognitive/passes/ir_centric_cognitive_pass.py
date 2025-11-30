"""
IR-Centric Cognitive Pass for Code Enhancement.

Implements the core cognitive enhancement pipeline:
1. Extract functions implementing IR flows
2. Query anti-patterns from NegativePatternStore
3. Build IR Guard prompt with contracts
4. Call LLM for enhancement
5. Validate against IR contracts
6. Rollback on violation

Part of Bug #143-160 IR-Centric Cognitive Code Generation.
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import ast
import logging
import re

# Local imports
from src.cognitive.ir.behavior_model import Flow, BehaviorModelIR
from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.cache.cognitive_cache import CognitiveCache, CachedEnhancement
from src.learning.negative_pattern_store import (
    NegativePatternStore,
    GenerationAntiPattern,
    CognitiveRegressionPattern,
)

logger = logging.getLogger(__name__)


@dataclass
class FunctionEnhancement:
    """
    Result of enhancing a single function.
    """
    function_name: str
    original_code: str
    enhanced_code: str
    flow_id: str
    anti_patterns_applied: List[str] = field(default_factory=list)

    # Validation state
    validated: bool = False
    validation_passed: bool = False
    validation_errors: List[str] = field(default_factory=list)

    # Rollback state
    rolled_back: bool = False
    rollback_reason: Optional[str] = None

    # Metrics
    enhancement_time_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class EnhancementResult:
    """
    Result of cognitive enhancement pass on a file.
    """
    file_path: str
    original_content: str
    enhanced_content: str

    # Function-level results
    function_enhancements: List[FunctionEnhancement] = field(default_factory=list)

    # Overall state
    success: bool = False
    fully_enhanced: bool = False
    partial_enhancement: bool = False

    # Validation summary
    ir_validations_passed: int = 0
    ir_validations_failed: int = 0
    rollbacks_performed: int = 0

    # Metrics
    total_time_ms: float = 0.0
    total_tokens_used: int = 0
    cache_hits: int = 0

    # Errors
    errors: List[str] = field(default_factory=list)


class IRCentricCognitivePass:
    """
    IR-Centric Cognitive Enhancement Pass.

    This pass enhances generated code by:
    1. Identifying functions that implement IR flows
    2. Querying historical anti-patterns that affected similar flows
    3. Generating IR Guard prompts with contracts as constraints
    4. Calling LLM to enhance code
    5. Validating enhanced code against IR contracts
    6. Rolling back to original if IR validation fails

    The key difference from traditional passes:
    - Semantic matching by IR flow, not file path
    - Function-level granularity, not file-level
    - IR contracts as validation constraints
    - Learning from failures via CognitiveRegressionPattern

    Example:
        pass_ = IRCentricCognitivePass(ir, pattern_store, cache)
        result = await pass_.enhance_file(
            file_path="src/services/cart_service.py",
            content="..."
        )

        if result.success:
            write_file(file_path, result.enhanced_content)
    """

    # Version for cache key generation
    VERSION = "1.0.0"

    def __init__(
        self,
        ir: ApplicationIR,
        pattern_store: NegativePatternStore,
        cache: Optional[CognitiveCache] = None,
        llm_client: Optional[Any] = None,
        ir_validator: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the cognitive pass.

        Args:
            ir: Application IR with flows and contracts
            pattern_store: Store for anti-patterns and regressions
            cache: Optional cognitive cache for enhanced code
            llm_client: LLM client for enhancement calls
            ir_validator: IR compliance validator
            config: Additional configuration
        """
        self._ir = ir
        self._pattern_store = pattern_store
        self._cache = cache or CognitiveCache()
        self._llm_client = llm_client
        self._ir_validator = ir_validator
        self._config = config or {}

        # Enhancement settings
        self._max_patterns_per_flow = self._config.get("max_patterns_per_flow", 5)
        self._min_pattern_occurrences = self._config.get("min_pattern_occurrences", 2)
        self._rollback_on_validation_failure = self._config.get("rollback_on_failure", True)
        self._enable_cache = self._config.get("enable_cache", True)

        # Metrics
        self._total_enhancements = 0
        self._successful_enhancements = 0
        self._validation_failures = 0
        self._rollbacks = 0
        self._cache_hits = 0

    async def enhance_file(
        self,
        file_path: str,
        content: str,
    ) -> EnhancementResult:
        """
        Enhance a generated file using cognitive patterns.

        Args:
            file_path: Path to the file being enhanced
            content: Current content of the file

        Returns:
            EnhancementResult with enhanced content and metrics
        """
        import time
        start_time = time.time()

        result = EnhancementResult(
            file_path=file_path,
            original_content=content,
            enhanced_content=content,  # Start with original
        )

        try:
            # Step 1: Get flows for this file
            flows = self._get_flows_for_file(file_path)
            if not flows:
                logger.debug(f"No IR flows found for {file_path}")
                result.success = True
                return result

            # Step 2: Extract functions implementing flows
            flow_functions = self._extract_flow_functions(content, flows)
            if not flow_functions:
                logger.debug(f"No flow functions extracted from {file_path}")
                result.success = True
                return result

            # Step 3: Process each flow function
            enhanced_content = content
            for flow, func_info in flow_functions:
                enhancement = await self._enhance_function(
                    flow=flow,
                    func_name=func_info["name"],
                    func_code=func_info["code"],
                    file_path=file_path,
                )
                result.function_enhancements.append(enhancement)

                # Track validation results
                if enhancement.validated:
                    if enhancement.validation_passed:
                        result.ir_validations_passed += 1
                        if not enhancement.rolled_back:
                            # Apply enhancement to content
                            enhanced_content = self._apply_enhancement(
                                enhanced_content,
                                func_info,
                                enhancement.enhanced_code,
                            )
                    else:
                        result.ir_validations_failed += 1
                        if enhancement.rolled_back:
                            result.rollbacks_performed += 1

                # Track metrics
                result.total_tokens_used += enhancement.tokens_used
                if enhancement.enhanced_code != enhancement.original_code and not enhancement.rolled_back:
                    result.cache_hits += 1 if self._cache_hits > 0 else 0

            result.enhanced_content = enhanced_content
            result.success = True
            result.fully_enhanced = result.ir_validations_failed == 0
            result.partial_enhancement = (
                result.ir_validations_passed > 0 and
                result.ir_validations_failed > 0
            )

        except Exception as e:
            logger.error(f"Error enhancing {file_path}: {e}")
            result.errors.append(str(e))
            result.success = False

        result.total_time_ms = (time.time() - start_time) * 1000
        return result

    async def _enhance_function(
        self,
        flow: Flow,
        func_name: str,
        func_code: str,
        file_path: str,
    ) -> FunctionEnhancement:
        """
        Enhance a single function implementing an IR flow.
        """
        import time
        start_time = time.time()

        enhancement = FunctionEnhancement(
            function_name=func_name,
            original_code=func_code,
            enhanced_code=func_code,  # Start with original
            flow_id=flow.get_flow_id(),
        )

        try:
            # Step 1: Get anti-patterns for this flow
            anti_patterns = self._get_anti_patterns_for_flow(flow)
            if not anti_patterns:
                logger.debug(f"No anti-patterns for flow {flow.get_flow_id()}")
                enhancement.validated = True
                enhancement.validation_passed = True
                return enhancement

            anti_pattern_ids = [p.pattern_id for p in anti_patterns]
            enhancement.anti_patterns_applied = anti_pattern_ids

            # Step 2: Check cache
            if self._enable_cache:
                cache_key = self._cache.compute_cache_key_from_flow(
                    flow=flow,
                    anti_pattern_ids=anti_pattern_ids,
                )
                cached = self._cache.get(cache_key)
                if cached and cached.validation_passed:
                    enhancement.enhanced_code = cached.enhanced_code
                    enhancement.validated = True
                    enhancement.validation_passed = True
                    self._cache_hits += 1
                    enhancement.enhancement_time_ms = (time.time() - start_time) * 1000
                    return enhancement

            # Step 3: Check for known regressions
            if self._pattern_store.has_cognitive_regression(flow.get_flow_id(), anti_pattern_ids):
                logger.info(f"Skipping enhancement for {func_name} due to known regression")
                enhancement.validated = True
                enhancement.validation_passed = True
                return enhancement

            # Step 4: Build IR Guard prompt
            ir_guard = self._build_ir_guard(flow, anti_patterns)

            # Step 5: Call LLM for enhancement
            enhanced_code, tokens_used = await self._call_llm_for_enhancement(
                func_code=func_code,
                ir_guard=ir_guard,
                flow=flow,
            )
            enhancement.enhanced_code = enhanced_code
            enhancement.tokens_used = tokens_used
            self._total_enhancements += 1

            # Step 6: Validate against IR contracts
            validation_result = await self._validate_against_ir(
                enhanced_code=enhanced_code,
                flow=flow,
            )
            enhancement.validated = True
            enhancement.validation_passed = validation_result["passed"]
            enhancement.validation_errors = validation_result.get("errors", [])

            # Step 7: Handle validation failure
            if not enhancement.validation_passed:
                self._validation_failures += 1
                if self._rollback_on_validation_failure:
                    enhancement.rolled_back = True
                    enhancement.rollback_reason = "IR validation failed"
                    enhancement.enhanced_code = func_code  # Rollback to original
                    self._rollbacks += 1

                    # Store regression for learning
                    regression = CognitiveRegressionPattern(
                        ir_flow=flow.name,
                        flow_id=flow.get_flow_id(),
                        anti_patterns_applied=anti_pattern_ids,
                        result="ir_contract_violation",
                        violations=enhancement.validation_errors,
                        enhanced_function=enhanced_code,
                        original_function=func_code,
                        file_path=file_path,
                    )
                    self._pattern_store.store_cognitive_regression(regression)
                else:
                    self._successful_enhancements += 1
            else:
                self._successful_enhancements += 1

                # Cache successful enhancement
                if self._enable_cache:
                    cache_key = self._cache.compute_cache_key_from_flow(
                        flow=flow,
                        anti_pattern_ids=anti_pattern_ids,
                    )
                    self._cache.store(
                        cache_key=cache_key,
                        flow_id=flow.get_flow_id(),
                        enhanced_code=enhanced_code,
                        original_code=func_code,
                        anti_patterns_applied=anti_pattern_ids,
                        constraint_types=flow.constraint_types,
                        preconditions=flow.preconditions,
                        postconditions=flow.postconditions,
                        ir_version=flow.version,
                    )
                    self._cache.mark_validated(cache_key, True)

        except Exception as e:
            logger.error(f"Error enhancing function {func_name}: {e}")
            enhancement.validation_errors.append(str(e))

        enhancement.enhancement_time_ms = (time.time() - start_time) * 1000
        return enhancement

    def _get_flows_for_file(self, file_path: str) -> List[Flow]:
        """
        Get IR flows implemented in this file.
        """
        if not self._ir or not self._ir.behavior_model:
            return []
        return self._ir.behavior_model.get_flows_for_file(file_path)

    def _extract_flow_functions(
        self,
        content: str,
        flows: List[Flow],
    ) -> List[Tuple[Flow, Dict[str, Any]]]:
        """
        Extract functions that implement IR flows from source code.

        Returns list of (flow, function_info) tuples where function_info contains:
        - name: Function name
        - code: Function source code
        - start_line: Line number where function starts
        - end_line: Line number where function ends
        """
        results = []

        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            logger.warning(f"Failed to parse content: {e}")
            return results

        lines = content.split('\n')

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_name = node.name

                # Find matching flow by implementation_name or name pattern
                matching_flow = None
                for flow in flows:
                    impl_name = flow.implementation_name or flow.get_flow_id()
                    if self._matches_flow_name(func_name, impl_name):
                        matching_flow = flow
                        break

                if matching_flow:
                    # Extract function code
                    start_line = node.lineno - 1  # 0-indexed
                    end_line = node.end_lineno or start_line + 1
                    func_code = '\n'.join(lines[start_line:end_line])

                    results.append((matching_flow, {
                        "name": func_name,
                        "code": func_code,
                        "start_line": start_line,
                        "end_line": end_line,
                    }))

        return results

    def _matches_flow_name(self, func_name: str, flow_name: str) -> bool:
        """
        Check if function name matches flow name.

        Handles variations:
        - Exact match: add_item_to_cart == add_item_to_cart
        - Case insensitive: AddItemToCart ~= add_item_to_cart
        - Partial match: _add_item == add_item
        """
        # Normalize both names
        func_norm = func_name.lower().replace('_', '').replace('-', '')
        flow_norm = flow_name.lower().replace('_', '').replace('-', '')

        # Exact match
        if func_norm == flow_norm:
            return True

        # Contains match (for prefixed/suffixed names)
        if flow_norm in func_norm or func_norm in flow_norm:
            return True

        return False

    def _get_anti_patterns_for_flow(self, flow: Flow) -> List[GenerationAntiPattern]:
        """
        Get anti-patterns that apply to this flow.
        """
        patterns = []

        # Get by flow name
        flow_patterns = self._pattern_store.get_patterns_for_flow(
            flow.name,
            min_occurrences=self._min_pattern_occurrences,
        )
        patterns.extend(flow_patterns)

        # Get by constraint types
        for constraint_type in flow.constraint_types:
            constraint_patterns = self._pattern_store.get_patterns_for_constraint_type(
                constraint_type,
                min_occurrences=self._min_pattern_occurrences,
            )
            for p in constraint_patterns:
                if p not in patterns:
                    patterns.append(p)

        # Limit to max patterns
        return patterns[:self._max_patterns_per_flow]

    def _build_ir_guard(
        self,
        flow: Flow,
        anti_patterns: List[GenerationAntiPattern],
    ) -> str:
        """
        Build IR Guard prompt with contracts and anti-patterns.

        The IR Guard includes:
        1. IR contract (preconditions, postconditions)
        2. Anti-patterns to avoid
        3. Constraint types to respect
        """
        sections = []

        # Header
        sections.append(f"# IR Guard for {flow.name}")
        sections.append("")

        # IR Contract
        sections.append("## IR Contract")
        sections.append(f"Flow ID: {flow.get_flow_id()}")
        sections.append(f"Primary Entity: {flow.primary_entity or 'N/A'}")

        if flow.entities_involved:
            sections.append(f"Entities: {', '.join(flow.entities_involved)}")

        if flow.preconditions:
            sections.append("")
            sections.append("### Preconditions (MUST be true before execution)")
            for pre in flow.preconditions:
                sections.append(f"- {pre}")

        if flow.postconditions:
            sections.append("")
            sections.append("### Postconditions (MUST be true after execution)")
            for post in flow.postconditions:
                sections.append(f"- {post}")

        if flow.constraint_types:
            sections.append("")
            sections.append("### Constraint Types")
            for ct in flow.constraint_types:
                sections.append(f"- {ct}")

        # Anti-patterns
        if anti_patterns:
            sections.append("")
            sections.append("## Anti-Patterns to Avoid")
            sections.append("The following patterns have caused issues in the past:")
            sections.append("")
            for pattern in anti_patterns:
                sections.append(f"### {pattern.pattern_id}: {pattern.description}")
                sections.append(f"- Severity: {pattern.severity}")
                if pattern.correct_approach:
                    sections.append(f"- Correct approach: {pattern.correct_approach}")
                if pattern.endpoint_pattern:
                    sections.append(f"- Endpoint pattern: {pattern.endpoint_pattern}")
                sections.append("")

        # Instructions
        sections.append("## Enhancement Instructions")
        sections.append("1. Preserve all IR contract constraints")
        sections.append("2. Avoid all listed anti-patterns")
        sections.append("3. Maintain function signature and return types")
        sections.append("4. Do not add features not specified in the contract")
        sections.append("5. If unsure, preserve original implementation")

        return '\n'.join(sections)

    async def _call_llm_for_enhancement(
        self,
        func_code: str,
        ir_guard: str,
        flow: Flow,
    ) -> Tuple[str, int]:
        """
        Call LLM to enhance the function.

        Returns (enhanced_code, tokens_used).
        """
        if not self._llm_client:
            logger.warning("No LLM client configured, skipping enhancement")
            return func_code, 0

        # Build prompt
        prompt = f"""You are enhancing a function that implements an IR flow.

{ir_guard}

## Original Function
```python
{func_code}
```

## Task
Enhance this function to:
1. Avoid the anti-patterns listed above
2. Respect all preconditions and postconditions
3. Handle constraint types appropriately

Return ONLY the enhanced Python function code, without explanation.
If no enhancement is needed, return the original code unchanged.
"""

        try:
            # Call LLM
            response = await self._llm_client.generate(prompt)
            enhanced_code = self._extract_code_from_response(response.text)
            tokens_used = getattr(response, 'usage', {}).get('total_tokens', 0)
            return enhanced_code, tokens_used
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")
            return func_code, 0

    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        """
        # Try to find code block
        code_pattern = r'```(?:python)?\n(.*?)```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        if matches:
            return matches[0].strip()

        # If no code block, assume entire response is code
        return response.strip()

    async def _validate_against_ir(
        self,
        enhanced_code: str,
        flow: Flow,
    ) -> Dict[str, Any]:
        """
        Validate enhanced code against IR contracts.
        """
        if not self._ir_validator:
            # No validator, assume valid
            return {"passed": True, "errors": []}

        try:
            result = await self._ir_validator.validate_function(
                code=enhanced_code,
                flow=flow,
                preconditions=flow.preconditions,
                postconditions=flow.postconditions,
            )
            return {
                "passed": result.is_valid,
                "errors": result.errors if hasattr(result, 'errors') else [],
            }
        except Exception as e:
            logger.error(f"IR validation failed: {e}")
            return {"passed": False, "errors": [str(e)]}

    def _apply_enhancement(
        self,
        content: str,
        func_info: Dict[str, Any],
        enhanced_code: str,
    ) -> str:
        """
        Apply enhanced code to the file content.
        """
        lines = content.split('\n')
        start_line = func_info["start_line"]
        end_line = func_info["end_line"]

        # Replace function lines with enhanced code
        enhanced_lines = enhanced_code.split('\n')
        new_lines = lines[:start_line] + enhanced_lines + lines[end_line:]

        return '\n'.join(new_lines)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get pass statistics.
        """
        return {
            "total_enhancements": self._total_enhancements,
            "successful_enhancements": self._successful_enhancements,
            "validation_failures": self._validation_failures,
            "rollbacks": self._rollbacks,
            "cache_hits": self._cache_hits,
            "prevention_rate": (
                self._successful_enhancements / self._total_enhancements
                if self._total_enhancements > 0 else 0.0
            ),
            "cache_hit_rate": self._cache.get_statistics().get("hit_rate", 0.0),
            "version": self.VERSION,
        }
