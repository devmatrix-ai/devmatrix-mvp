"""
Smoke Test Planner Agent

Phase 2 of Bug #107: LLM-Driven Smoke Test Generation

Analyzes IR and spec to generate comprehensive smoke test scenarios.
Uses deterministic IR-driven generation - LLM reads IR, doesn't invent.
"""
import json
import structlog
from typing import Optional

from src.cognitive.ir.application_ir import ApplicationIR
from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
from src.validation.smoke_test_models import (
    SmokeTestPlan,
    TestScenario,
    SeedDataEntity
)

logger = structlog.get_logger(__name__)


PLANNER_SYSTEM_PROMPT = """You are an expert API test engineer. Your job is to analyze an API's
Intermediate Representation (IR) and generate comprehensive smoke test scenarios.

CRITICAL RULES:
1. READ from the IR, not INVENT rules. Every scenario must be justified by IR data.
2. Output ONLY valid JSON - NO code expressions like .repeat(), NO JavaScript, NO template literals.
3. For long strings, use actual characters like "AAAAAAAAAA" not "A".repeat(10).
4. ALL values must be JSON literals (strings, numbers, booleans, null, arrays, objects).

## Scenario Types to Generate

### For EVERY endpoint:
1. **happy_path**: Valid request with proper data → expect 200/201/204

### For endpoints with {id} parameters:
2. **not_found**: Invalid UUID → expect 404

### For POST/PUT/PATCH endpoints:
3. **validation_error**: Each validation_rule should generate a test (missing required, invalid format, etc.)
   - Bug #121 Fix: For max_length tests, generate ACTUAL long strings that EXCEED the limit
   - Example: If max_length=255, use a string with 256+ characters like "AAAA..." (repeated)
   - NEVER use placeholder text like "TOO_LONG_STRING" - that's only 15 characters!

### From predefined_test_cases (USE THESE!):
4. **predefined_[name]**: If the IR contains test_cases, convert them directly into scenarios

### From business_flows:
5. **flow_[name]**: Test the workflow steps (e.g., create → update → pay → cancel)

### From invariants:
6. **invariant_[name]**: Test business constraints (e.g., balance >= 0, status transitions)

## Expected Status Codes by Operation:
- GET list: 200
- GET by id: 200 (found) / 404 (not found)
- POST create: 201
- PUT/PATCH update: 200 (success) / 404 (not found) / 400/422 (validation)
- DELETE: 204 (success) / 404 (not found)
- POST action (pay, cancel, etc.): 200/204 (success) / 400 (invalid state) / 404 (not found)

Output ONLY valid JSON with literal values, no code or expressions."""


PLANNER_USER_PROMPT = """## IR Data (Source of Truth)

### Entities
{entities_json}

### Endpoints
{endpoints_json}

### Business Rules
{business_rules_json}

## UUID Rules
- Seed data UUIDs: 00000000-0000-4000-8000-00000000000X (X = entity index starting from 1)
- Not-found UUIDs: 99999999-9999-4000-8000-999999999999

## Output Format
Generate a JSON object with this exact structure:
{{
  "seed_data": [
    {{
      "entity_name": "EntityName",
      "uuid": "00000000-0000-4000-8000-000000000001",
      "fields": {{"field1": "value1", "field2": value2}},
      "depends_on": []
    }}
  ],
  "scenarios": [
    {{
      "endpoint": "GET /path",
      "name": "happy_path",
      "description": "Description",
      "path_params": {{}},
      "query_params": null,
      "payload": null,
      "expected_status": 200,
      "expected_response_contains": null,
      "reason": "Why this scenario exists based on IR"
    }}
  ]
}}

IMPORTANT - Bug #122 Fix - SEED DATA COMPLETENESS:
1. EVERY endpoint needs at least a happy_path scenario
2. Endpoints with {{id}} params need a not_found scenario
3. POST/PUT/PATCH with request_schema need at least one validation_error scenario
4. Use the actual entity field names from the IR
5. For FK relationships, ensure parent entities are seeded before children
6. **CRITICAL**: EVERY UUID used in path_params MUST have a corresponding seed_data entry!
7. For state-dependent tests (e.g., "cancel paid order"), seed an entity IN THAT STATE
   - If testing deactivate on inactive product → seed a Product with is_active=false
   - If testing cancel paid order → seed an Order with order_status='PAID'
   - If testing checkout on closed cart → seed a Cart with status='CHECKED_OUT'
8. Use DIFFERENT UUIDs for different states (e.g., ...0001=active product, ...0011=inactive product)"""


class SmokeTestPlannerAgent:
    """
    Specialized agent for generating smoke test plans from IR.

    Deterministic: Uses temperature=0, reads only from IR.
    """

    def __init__(self, llm_client: Optional[EnhancedAnthropicClient] = None):
        self.llm = llm_client or EnhancedAnthropicClient()

    async def _generate_with_streaming(self, prompt: str) -> str:
        """
        Generate LLM response using streaming to avoid timeout limits.

        Bug #107: Uses streaming API to handle long-running requests
        that would otherwise timeout with non-streaming requests.
        """
        import asyncio

        # Get model from selector
        model = self.llm.model_selector.select_model(
            task_type="validation",
            complexity="high"
        )

        # Bug #119: Changed to debug to reduce noise in smoke test output
        logger.debug(f"   Using streaming with model: {model}")

        # Run streaming in thread pool to avoid blocking async event loop
        def stream_sync():
            full_text = ""
            with self.llm.anthropic.messages.stream(
                model=model,
                max_tokens=32000,  # Maximum for comprehensive test plans
                temperature=0.0,  # Deterministic
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
            return full_text

        response = await asyncio.to_thread(stream_sync)
        logger.info(f"   Streaming complete: {len(response)} chars")
        return response

    async def generate_plan(
        self,
        ir: ApplicationIR,
        spec_content: Optional[str] = None  # Optional, IR is primary source
    ) -> SmokeTestPlan:
        """
        Generate smoke test plan from IR.

        Args:
            ir: Application Intermediate Representation
            spec_content: Optional spec content for additional context

        Returns:
            SmokeTestPlan with seed_data and scenarios
        """
        # Bug #119: Changed to debug to reduce noise in smoke test output
        logger.debug("🎯 Planner Agent: Generating smoke test plan from IR")

        # Format IR data for prompt
        entities_json = self._format_entities(ir)
        endpoints_json = self._format_endpoints(ir)
        business_rules_json = self._format_business_rules(ir)

        # Build prompt
        user_prompt = PLANNER_USER_PROMPT.format(
            entities_json=entities_json,
            endpoints_json=endpoints_json,
            business_rules_json=business_rules_json
        )

        full_prompt = f"{PLANNER_SYSTEM_PROMPT}\n\n{user_prompt}"

        # Bug #119: Changed to debug to reduce noise in smoke test output
        logger.debug(f"   Analyzing {len(ir.get_endpoints())} endpoints, {len(ir.get_entities())} entities")

        # Generate with LLM using streaming (temperature=0 for determinism)
        # Bug #107: Using streaming with max tokens to avoid timeout and truncation
        response = await self._generate_with_streaming(full_prompt)

        # Parse response
        plan = self._parse_response(response)

        # Validate plan covers all endpoints
        self._validate_plan_coverage(plan, ir)

        logger.info(f"   ✅ Generated {len(plan.scenarios)} scenarios, {len(plan.seed_data)} seed entities")

        return plan

    def _format_entities(self, ir: ApplicationIR) -> str:
        """Format entities from IR for prompt."""
        entities = []
        for idx, entity in enumerate(ir.get_entities(), start=1):
            entity_dict = {
                "name": entity.name,
                "index": idx,  # For deterministic UUID assignment
                "attributes": [
                    {
                        "name": attr.name,
                        "type": attr.data_type.value if hasattr(attr.data_type, 'value') else str(attr.data_type),
                        "required": not attr.is_nullable,
                        "is_primary_key": attr.is_primary_key,
                        "constraints": attr.constraints
                    }
                    for attr in entity.attributes
                ],
                "relationships": [
                    {
                        "target": rel.target_entity,
                        "type": rel.type.value if hasattr(rel.type, 'value') else str(rel.type),
                        "field": rel.field_name
                    }
                    for rel in entity.relationships
                ]
            }
            entities.append(entity_dict)

        return json.dumps(entities, indent=2)

    def _format_endpoints(self, ir: ApplicationIR) -> str:
        """Format endpoints from IR for prompt."""
        endpoints = []
        for endpoint in ir.get_endpoints():
            endpoint_dict = {
                "path": endpoint.path,
                "method": endpoint.method.value if hasattr(endpoint.method, 'value') else str(endpoint.method),
                "operation_id": endpoint.operation_id,
                "has_path_params": "{" in endpoint.path,
                "has_request_schema": endpoint.request_schema is not None,
                "parameters": [
                    {
                        "name": p.name,
                        "location": p.location.value if hasattr(p.location, 'value') else str(p.location),
                        "type": p.data_type,
                        "required": p.required
                    }
                    for p in endpoint.parameters
                ]
            }

            # Add request schema fields if present
            if endpoint.request_schema:
                endpoint_dict["request_schema_fields"] = [
                    {
                        "name": f.name,
                        "type": f.type,
                        "required": f.required
                    }
                    for f in endpoint.request_schema.fields
                ]

            endpoints.append(endpoint_dict)

        return json.dumps(endpoints, indent=2)

    def _format_business_rules(self, ir: ApplicationIR) -> str:
        """Format comprehensive business rules from IR for test generation."""
        rules_data = {
            "validation_rules": [],
            "predefined_test_cases": [],
            "business_flows": [],
            "invariants": []
        }

        # 1. Extract FULL ValidationRules (entity, attribute, type, condition, error_message)
        if ir.validation_model and ir.validation_model.rules:
            for rule in ir.validation_model.rules:
                rules_data["validation_rules"].append({
                    "entity": rule.entity,
                    "attribute": rule.attribute,
                    "validation_type": rule.type.value if hasattr(rule.type, 'value') else str(rule.type),
                    "condition": rule.condition,
                    "error_message": rule.error_message,
                    "severity": rule.severity
                })

        # 2. Extract PREDEFINED TEST CASES from ValidationModel (GOLD for tests!)
        if ir.validation_model and ir.validation_model.test_cases:
            for tc in ir.validation_model.test_cases:
                rules_data["predefined_test_cases"].append({
                    "name": tc.name,
                    "scenario": tc.scenario,
                    "input_data": tc.input_data,
                    "expected_outcome": tc.expected_outcome
                })

        # 3. Extract FULL Flows with steps, triggers, conditions
        if ir.behavior_model and ir.behavior_model.flows:
            for flow in ir.behavior_model.flows:
                flow_dict = {
                    "name": flow.name,
                    "type": flow.type.value if hasattr(flow.type, 'value') else str(flow.type),
                    "trigger": flow.trigger,
                    "description": flow.description,
                    "steps": []
                }
                for step in flow.steps:
                    step_dict = {
                        "order": step.order,
                        "description": step.description,
                        "action": step.action,
                        "target_entity": step.target_entity,
                        "condition": step.condition
                    }
                    flow_dict["steps"].append(step_dict)
                rules_data["business_flows"].append(flow_dict)

        # 4. Extract FULL Invariants with expressions
        if ir.behavior_model and ir.behavior_model.invariants:
            for inv in ir.behavior_model.invariants:
                rules_data["invariants"].append({
                    "entity": inv.entity,
                    "description": inv.description,
                    "expression": inv.expression,
                    "enforcement_level": inv.enforcement_level
                })

        # Legacy fallback for old IR structure
        if not any(rules_data.values()):
            for rule in ir.get_validation_rules():
                rules_data["validation_rules"].append({
                    "description": str(rule)
                })
            for flow in ir.get_flows():
                if hasattr(flow, 'description'):
                    rules_data["business_flows"].append({
                        "description": flow.description
                    })

        return json.dumps(rules_data, indent=2)

    def _parse_response(self, response: str) -> SmokeTestPlan:
        """Parse LLM response into SmokeTestPlan with JSON repair."""
        import re

        # Clean up response (remove markdown code blocks if present)
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        # Bug #107: Clean JavaScript code patterns that LLM might generate
        cleaned = self._clean_js_patterns(cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}, attempting repair...")

            # Try JSON repair strategies
            repaired = self._repair_json(cleaned, e)
            if repaired:
                try:
                    data = json.loads(repaired)
                    logger.info("✅ JSON repair successful")
                except json.JSONDecodeError as e2:
                    logger.error(f"JSON repair failed: {e2}")
                    logger.error(f"Response was: {cleaned[:500]}...")
                    raise ValueError(f"Invalid JSON from LLM after repair: {e2}")
            else:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Response was: {cleaned[:500]}...")
                raise ValueError(f"Invalid JSON from LLM: {e}")

        return SmokeTestPlan.from_dict(data)

    def _clean_js_patterns(self, json_str: str) -> str:
        """
        Clean JavaScript code patterns from LLM response.

        The LLM sometimes generates JavaScript expressions in JSON like:
        - "A".repeat(100) -> "AAAAAAAAAA..."
        - `template ${var}` -> "template value"
        """
        import re

        original = json_str
        changes_made = []

        # Pattern 1: "X".repeat(N) -> Replace with placeholder or literal
        # Match patterns like: "A".repeat(2001) or "x".repeat(100)
        repeat_pattern = r'"([^"]{1,5})"\.repeat\((\d+)\)'

        def replace_repeat(match):
            char = match.group(1)
            count = int(match.group(2))
            # Use placeholder for very long strings, literal for short ones
            if count > 50:
                return f'"TOO_LONG_{count}_CHARS"'
            else:
                return f'"{char * min(count, 50)}"'

        json_str = re.sub(repeat_pattern, replace_repeat, json_str)

        # Pattern 2: String concatenation like "a" + "b"
        concat_pattern = r'"([^"]*?)"\s*\+\s*"([^"]*?)"'
        while re.search(concat_pattern, json_str):
            json_str = re.sub(concat_pattern, r'"\1\2"', json_str)

        # Pattern 3: Template literals `...${...}...` -> "..."
        template_pattern = r'`([^`]*?)\$\{[^}]+\}([^`]*?)`'
        json_str = re.sub(template_pattern, r'"\1PLACEHOLDER\2"', json_str)

        # Pattern 4: Simple template literals without interpolation
        json_str = re.sub(r'`([^`]*?)`', r'"\1"', json_str)

        if json_str != original:
            logger.info("🔧 Cleaned JavaScript patterns from LLM response")

        return json_str

    def _repair_json(self, json_str: str, error: json.JSONDecodeError) -> Optional[str]:
        """Attempt to repair malformed JSON from LLM."""
        import re

        # Strategy 1: Truncated JSON - find last complete object/array
        # Check if JSON is truncated (common with long responses)
        if "Expecting" in str(error):
            # Try to find the last valid closing bracket sequence
            # Look for patterns like }] that close seed_data and scenarios

            # Find the position of error
            error_pos = error.pos if hasattr(error, 'pos') else len(json_str)

            # Try truncating at the error position and closing properly
            truncated = json_str[:error_pos]

            # Count open brackets to determine what needs closing
            open_braces = truncated.count('{') - truncated.count('}')
            open_brackets = truncated.count('[') - truncated.count(']')

            # Try to close at a valid point (end of last complete object)
            # Find the last complete object marker
            last_complete = max(
                truncated.rfind('},'),
                truncated.rfind('}]'),
                truncated.rfind('"}\n'),
            )

            if last_complete > 0:
                # Truncate to last complete object
                truncated = truncated[:last_complete + 1]

                # Recount brackets
                open_braces = truncated.count('{') - truncated.count('}')
                open_brackets = truncated.count('[') - truncated.count(']')

                # Close remaining brackets
                closing = ']' * open_brackets + '}' * open_braces
                repaired = truncated + closing

                logger.info(f"Attempting JSON repair: truncated at {last_complete}, adding '{closing}'")
                return repaired

        # Strategy 2: Fix common JSON errors
        # Remove trailing commas before ] or }
        fixed = re.sub(r',(\s*[}\]])', r'\1', json_str)
        if fixed != json_str:
            logger.info("Attempting JSON repair: removed trailing commas")
            return fixed

        # Strategy 3: If response was cut off, try to find valid partial JSON
        # Look for the scenarios array start and try to close it
        scenarios_start = json_str.find('"scenarios":')
        if scenarios_start > 0:
            # Find start of scenarios array
            array_start = json_str.find('[', scenarios_start)
            if array_start > 0:
                # Try to find the last complete scenario object
                last_obj_end = json_str.rfind('"reason":')
                if last_obj_end > array_start:
                    # Find the closing brace after this reason
                    next_brace = json_str.find('}', last_obj_end)
                    if next_brace > 0:
                        truncated = json_str[:next_brace + 1]
                        # Close remaining structures
                        open_braces = truncated.count('{') - truncated.count('}')
                        open_brackets = truncated.count('[') - truncated.count(']')
                        closing = ']' * open_brackets + '}' * open_braces
                        return truncated + closing

        return None

    def _validate_plan_coverage(self, plan: SmokeTestPlan, ir: ApplicationIR) -> None:
        """Validate that plan covers all endpoints with at least happy_path."""
        endpoints = ir.get_endpoints()

        missing_happy_path = []
        for endpoint in endpoints:
            key = f"{endpoint.method.value if hasattr(endpoint.method, 'value') else endpoint.method} {endpoint.path}"
            scenarios = plan.get_scenarios_for_endpoint(
                method=endpoint.method.value if hasattr(endpoint.method, 'value') else str(endpoint.method),
                path=endpoint.path
            )

            has_happy = any(s.name == "happy_path" for s in scenarios)
            if not has_happy:
                missing_happy_path.append(key)

        if missing_happy_path:
            logger.warning(f"⚠️ Missing happy_path scenarios for: {missing_happy_path}")

        # Bug #122 Fix: Validate seed data completeness
        self._validate_seed_data_completeness(plan)

    def _validate_seed_data_completeness(self, plan: SmokeTestPlan) -> None:
        """
        Bug #122 Fix: Validate that all UUIDs referenced in scenarios have seed_data.

        Logs warnings for missing seed data but doesn't fail the plan generation.
        """
        import re

        # Collect all UUIDs from seed_data
        seeded_uuids = {entity.uuid for entity in plan.seed_data}

        # UUID pattern
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        not_found_pattern = r'99999999-9999-4000-8000-999999999999'  # Not-found UUID is intentional

        # Collect all UUIDs referenced in scenarios
        referenced_uuids = set()
        for scenario in plan.scenarios:
            # Check path_params
            if scenario.path_params:
                for param_name, param_value in scenario.path_params.items():
                    if isinstance(param_value, str) and re.match(uuid_pattern, param_value, re.IGNORECASE):
                        if not re.match(not_found_pattern, param_value, re.IGNORECASE):
                            referenced_uuids.add((param_value, scenario.endpoint, scenario.name))

            # Check payload for FK references
            if scenario.payload and isinstance(scenario.payload, dict):
                for field_name, field_value in scenario.payload.items():
                    if isinstance(field_value, str) and re.match(uuid_pattern, field_value, re.IGNORECASE):
                        if not re.match(not_found_pattern, field_value, re.IGNORECASE):
                            referenced_uuids.add((field_value, scenario.endpoint, f"{scenario.name}.payload.{field_name}"))

        # Find orphan UUIDs (referenced but not seeded)
        orphan_uuids = []
        for uuid_val, endpoint, context in referenced_uuids:
            if uuid_val not in seeded_uuids:
                orphan_uuids.append((uuid_val, endpoint, context))

        if orphan_uuids:
            logger.warning(f"⚠️ Bug #122: Found {len(orphan_uuids)} orphan UUIDs (referenced but not seeded):")
            for uuid_val, endpoint, context in orphan_uuids[:5]:  # Show first 5
                logger.warning(f"   - {uuid_val} in {endpoint} ({context})")
            if len(orphan_uuids) > 5:
                logger.warning(f"   ... and {len(orphan_uuids) - 5} more")
        else:
            logger.info("   ✅ Bug #122: All referenced UUIDs have seed data")
