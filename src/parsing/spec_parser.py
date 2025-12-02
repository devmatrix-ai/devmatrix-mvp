"""
Enhanced Specification Parser for Code Generation Pipeline

Parses functional requirements from markdown specs including:
- Markdown headers: **F1. Description**, ### Section
- Entity definitions with fields, types, constraints
- Endpoint specifications with methods, paths, parameters
- Business logic: validations, rules, calculations

Target: Extract functional requirements from any natural language spec
"""

from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import re
import logging
import yaml
import warnings

from src.parsing.hierarchical_models import (
    GlobalContext,
    EntitySummary,
    Relationship as EntityRelationship,  # Alias to avoid conflict with spec_parser.Relationship
    EndpointSummary,
    EntityDetail
)
from src.parsing.entity_locator import find_entity_locations, extract_context_window
from src.parsing.prompts import get_global_context_prompt
from src.parsing.field_extractor import extract_entity_fields

# Bug #11 Fix: Use robust YAML parsing helpers
from src.utils.yaml_helpers import safe_yaml_load, robust_yaml_parse

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures (from spec.md)
# ============================================================================


@dataclass
class Requirement:
    """Single parsed requirement"""

    id: str  # "F1", "NF1"
    type: str  # "functional", "non_functional"
    priority: str  # "MUST", "SHOULD", "COULD"
    description: str  # Full requirement text
    domain: str = ""  # "crud", "auth", "payment", "workflow" (filled by classifier)
    dependencies: List[str] = field(default_factory=list)  # ["F2", "F3"]


@dataclass
class Field:
    """Entity field definition"""

    name: str  # "id", "price"
    type: str  # "UUID", "Decimal", "str", "int"
    required: bool = True
    primary_key: bool = False
    unique: bool = False
    constraints: List[str] = field(default_factory=list)  # ["gt=0", "email_format"]
    default: Optional[str] = None
    description: str = ""
    
    # Phase 2.2: Enhanced validation metadata
    foreign_key: Optional[str] = None  # "Customer.id" for relationships
    enum_values: Optional[List[str]] = None  # ["open", "checked_out"] for enums
    metadata: Dict[str, Any] = field(default_factory=dict)  # {"read-only": True, "auto-calculated": "sum"}
    min_length: Optional[int] = None  # For string validation
    max_length: Optional[int] = None  # For string validation
    pattern: Optional[str] = None  # Regex pattern for validation


@dataclass
class Relationship:
    """Entity relationship definition"""

    type: str  # "ForeignKey", "OneToMany", "ManyToMany"
    target_entity: str  # "Product", "Customer"
    field_name: str  # "customer_id", "items"
    optional: bool = False


@dataclass
class Validation:
    """Business validation rule"""

    field: str  # "price", "email", "stock"
    rule: str  # "> 0", "email_format", ">= 0"
    error_message: str = ""


@dataclass
class Entity:
    """Entity/Model definition extracted from spec"""

    name: str  # "Product", "Customer"
    fields: List[Field] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    validations: List[Validation] = field(default_factory=list)
    description: str = ""

    @property
    def snake_name(self) -> str:
        """Convert entity name to snake_case for use in file/variable names"""
        # Convert CamelCase to snake_case: Product → product, CustomerOrder → customer_order
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


@dataclass
class Param:
    """Endpoint parameter"""

    name: str  # "page", "customer_id"
    type: str  # "int", "UUID"
    location: str  # "query", "path", "body"
    required: bool = True
    default: Optional[str] = None


@dataclass
class ResponseSpec:
    """Endpoint response specification"""

    status_code: int  # 200, 201, 404, 400
    description: str  # "Success", "Not Found"
    schema: Optional[str] = None  # "Product", "List[Product]"


@dataclass
class Endpoint:
    """API endpoint specification"""

    method: str  # "POST", "GET", "PUT", "DELETE"
    path: str  # "/products", "/cart/checkout"
    entity: str  # "Product", "Cart"
    operation: str  # "create", "list", "update", "delete", "custom"
    params: List[Param] = field(default_factory=list)
    response: Optional[ResponseSpec] = None
    business_logic: List[str] = field(default_factory=list)  # ["validate_stock", "calculate_total"]
    description: str = ""


@dataclass
class BusinessLogic:
    """Business logic rule or calculation"""

    type: str  # "validation", "calculation", "state_machine"
    description: str  # "Validate stock on checkout"
    conditions: List[str] = field(default_factory=list)  # ["stock > quantity"]
    actions: List[str] = field(default_factory=list)  # ["decrease_stock"]


@dataclass
class SpecRequirements:
    """Complete parsed specification"""

    requirements: List[Requirement] = field(default_factory=list)
    entities: List[Entity] = field(default_factory=list)
    endpoints: List[Endpoint] = field(default_factory=list)
    business_logic: List[BusinessLogic] = field(default_factory=list)
    validations: List[Validation] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    classification_ground_truth: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    dag_ground_truth: Dict[str, Any] = field(default_factory=dict)
    validation_ground_truth: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SpecParser Implementation
# ============================================================================


class SpecParser:
    """
    Enhanced markdown parser for functional requirements.

    .. deprecated::
        SpecParser is deprecated. Use SpecToApplicationIR instead for IR-centric
        architecture. ApplicationIR is the single source of truth for code generation.
        See: src/specs/spec_to_application_ir.py

    Extracts:
    - Functional requirements (F1-F99) from bold headers **F1. Description**
    - Non-functional requirements (NF1-NF99)
    - Entities with fields, types, constraints
    - Endpoints with methods, paths, parameters
    - Business logic (validations, rules, state machines)
    """

    def __init__(self) -> None:
        warnings.warn(
            "SpecParser is deprecated. Use SpecToApplicationIR instead for IR-centric "
            "architecture. See: src/specs/spec_to_application_ir.py",
            DeprecationWarning,
            stacklevel=2
        )
        # Regex patterns for requirement extraction
        # Pattern for **F1. Description** format
        self.functional_req_pattern = re.compile(r"\*\*F(\d+)\.\s+(.+?)\*\*", re.MULTILINE)

        # Pattern for **NF1. Description** format
        self.non_functional_req_pattern = re.compile(r"\*\*NF(\d+)\.\s+(.+?)\*\*", re.MULTILINE)

        # Pattern for numbered functional requirements: "1. **Create Task**: Description"
        self.numbered_functional_pattern = re.compile(
            r"^\d+\.\s+\*\*([^*]+)\*\*:\s*(.+)$", re.MULTILINE
        )

        # Pattern for API endpoint definitions: "- `POST /tasks` - Description"
        self.endpoint_definition_pattern = re.compile(
            r"^-\s+`(GET|POST|PUT|PATCH|DELETE)\s+(/[^\`]+)`\s+-\s+(.+)$", re.MULTILINE
        )

        # Pattern for entity definitions (sections with entity names)
        self.entity_section_pattern = re.compile(r"^\d+\.\s+\*\*(\w+)\*\*\s*$", re.MULTILINE)

        # Pattern for alternative entity format: **EntityName**:
        self.entity_alt_pattern = re.compile(r"^\*\*(\w+)\*\*:\s*$", re.MULTILINE)

        # Pattern for field definitions: "- name (type, constraints)"
        self.field_pattern = re.compile(r"^\s*-\s+(\w+)\s*\(([^)]+)\)\s*$", re.MULTILINE)

        # Pattern for field definitions: "- name: type description"
        self.field_alt_pattern = re.compile(r"^\s*-\s+(\w+):\s+(.+?)(?:\s*\(|$)", re.MULTILINE)

        # Pattern for constraints: price > 0, stock >= 0
        self.constraint_pattern = re.compile(
            r"([<>=]+)\s*(\d+)|(\w+)\s+format|único|obligatorio|opcional|por defecto|default",
            re.IGNORECASE,
        )

        # Pattern for HTTP methods in text
        self.http_method_pattern = re.compile(r"\b(GET|POST|PUT|PATCH|DELETE)\b")

        # Pattern for paths: /products, /cart/{id}
        self.path_pattern = re.compile(r"`?(/[\w/{}\-]+)`?")

        # --- Enhanced Patterns for Human/Spanish Specs ---
        
        # Entity: "### 1. Producto (Product)" -> Product
        self.entity_human_pattern = re.compile(r"^###\s+\d+\.\s+.*\((?P<name>\w+)\)", re.MULTILINE)
        
        # Field: "- **ID único** (UUID...)"
        self.field_human_pattern = re.compile(r"^\s*-\s+\*\*(?P<name>[^*]+)\*\*\s*(?P<info>.*)$", re.MULTILINE)


    def parse(self, spec_input: Union[Path, str]) -> SpecRequirements:
        """
        Parse specification markdown file or string content

        Args:
            spec_input: Path to markdown specification file OR string content

        Returns:
            SpecRequirements with all extracted components
        """
        try:
            # Handle both Path objects and string content
            if isinstance(spec_input, Path):
                content = spec_input.read_text(encoding="utf-8")
                spec_name = spec_input.name
            else:
                # spec_input is already the content string
                content = spec_input
                spec_name = "inline_spec"
        except Exception as e:
            logger.error(f"Failed to read spec file {spec_input}: {e}")
            return SpecRequirements()

        logger.info(f"Parsing specification: {spec_name}")

        # Try LLM-based extraction (Exclusive method)
        try:
            logger.info("Attempting LLM-based extraction...")
            result = self._extract_with_llm(content)
            if result and (result.entities or result.endpoints):
                logger.info("LLM extraction successful")
                # Add metadata
                result.metadata = {
                    "source_file": str(spec_input) if isinstance(spec_input, Path) else "inline_content",
                    "total_requirements": len(result.requirements),
                    "functional_count": sum(1 for r in result.requirements if r.type == "functional"),
                    "non_functional_count": sum(1 for r in result.requirements if r.type == "non_functional"),
                    "entity_count": len(result.entities),
                    "endpoint_count": len(result.endpoints),
                    "business_logic_count": len(result.business_logic),
                    "extraction_method": "llm"
                }
                
                # Extract ground truth (optional sections for validation)
                # We still parse these manually as they are specific YAML blocks in the spec
                result.classification_ground_truth = self._parse_classification_ground_truth(content)
                result.dag_ground_truth = self._parse_dag_ground_truth(content)
                result.validation_ground_truth = self._parse_validation_ground_truth(content)

                # If classification ground truth is missing, generate it with LLM from natural language
                if not result.classification_ground_truth and result.endpoints:
                    logger.info("Classification ground truth not found, generating from endpoints with LLM...")
                    result.classification_ground_truth = self._generate_classification_ground_truth_with_llm(
                        content, result.endpoints
                    )

                # If validation ground truth is missing, generate it with LLM from natural language
                if not result.validation_ground_truth and result.business_logic:
                    logger.info("Validation ground truth not found, generating from business logic with LLM...")
                    result.validation_ground_truth = self._generate_validation_ground_truth_with_llm(
                        content, result.business_logic
                    )
                
                logger.info(
                    f"Parsed {result.metadata['total_requirements']} requirements "
                    f"({result.metadata['functional_count']} functional, "
                    f"{result.metadata['non_functional_count']} non-functional), "
                    f"{result.metadata['entity_count']} entities, "
                    f"{result.metadata['endpoint_count']} endpoints, "
                    f"{result.metadata['business_logic_count']} business rules"
                )
                
                return result
            else:
                raise ValueError("LLM extraction returned empty results")
                
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            logger.warning("Falling back to regex-based extraction with LLM enrichment")
            return self._extract_hybrid(content, spec_input)

    def _extract_hybrid(self, content: str, spec_input) -> SpecRequirements:
        """Hybrid extraction: regex for structure + LLM for descriptions"""
        import re

        logger.info("Using hybrid extraction (regex structure + LLM descriptions)")
        reqs = SpecRequirements()

        # 1. Extract entities with regex - support multiple formats
        # Format 1: ### 1. Producto (Product)
        entity_pattern1 = r'###\s+\d+\.\s+([^(]+)\s*\(([^)]+)\)(.*?)(?=###\s+\d+\.|\Z)'
        # Format 2: **Entity: Product**
        entity_pattern2 = r'\*\*(?:Entidad|Entity):\s*(\w+)\*\*\s*\n(.*?)(?=\n\*\*(?:Entidad|Entity):|$)'

        entities_found1 = re.findall(entity_pattern1, content, re.DOTALL | re.IGNORECASE)
        entities_found2 = re.findall(entity_pattern2, content, re.DOTALL | re.IGNORECASE)

        # Process format 1 entities (### 1. Producto (Product))
        for spanish_name, english_name, entity_content in entities_found1:
            entity_name = english_name.strip()  # Use English name

            # Extract fields - format: - **ID único** (código UUID...)
            field_pattern = r'-\s+\*\*([^*]+)\*\*\s*\(([^)]+)\)(?:[^-\n]*?)(?:-\s*(.+?))?(?=\n-|\n\n|###|\Z)'
            fields_found = re.findall(field_pattern, entity_content, re.DOTALL)

            fields = []
            for field_name_raw, field_type_raw, field_desc in fields_found:
                field_name = field_name_raw.strip()

                # Simple field name mapping from Spanish to English
                field_name_map = {
                    "ID único": "id",
                    "Nombre": "name",
                    "Descripción": "description",
                    "Precio": "price",
                    "Stock": "stock",
                    "Email": "email",
                    "Fecha de creación": "creation_date",
                    "Total": "total_amount",
                    "Estado": "status"
                }
                field_name = field_name_map.get(field_name, field_name.lower().replace(" ", "_"))

                # Type mapping
                type_map = {
                    "código UUID": "UUID",
                    "UUID": "UUID",
                    "texto": "String",
                    "número decimal": "Float",
                    "entero": "Integer",
                    "fecha": "DateTime",
                    "enum": "String"
                }
                field_type = type_map.get(field_type_raw.strip(), "String")

                # Extract description with LLM for enforcement keywords
                description = self._extract_field_description(entity_name, field_name, content)

                fields.append(Field(
                    name=field_name,
                    type=field_type,
                    required=True,  # Default, could be refined
                    description=description or field_desc.strip() if field_desc else ""
                ))

            if fields:
                reqs.entities.append(Entity(name=entity_name, fields=fields))

        # Process format 2 entities (**Entity: Product**)
        for entity_name, entity_content in entities_found2:
            field_pattern = r'-\s+`?(\w+)`?\s*\(([^)]+)\)(?::\s*(.+?))?(?=\n-|\n\n|\Z)'
            fields_found = re.findall(field_pattern, entity_content, re.DOTALL)

            fields = []
            for field_name, field_type, field_desc in fields_found:
                description = self._extract_field_description(entity_name, field_name, content)

                fields.append(Field(
                    name=field_name.strip(),
                    type=field_type.strip(),
                    required=True,
                    description=description or field_desc.strip() if field_desc else ""
                ))

            if fields:
                reqs.entities.append(Entity(name=entity_name.strip(), fields=fields))

        # 2. Extract endpoints with regex
        endpoint_pattern = r'\*\*(?:POST|GET|PUT|DELETE|PATCH)\s+([^\*]+)\*\*'
        endpoints_found = re.findall(endpoint_pattern, content, re.IGNORECASE)

        for endpoint_path in endpoints_found:
            # Find method from context
            method_match = re.search(r'\*\*(POST|GET|PUT|DELETE|PATCH)\s+' + re.escape(endpoint_path), content, re.IGNORECASE)
            method = method_match.group(1).upper() if method_match else "GET"

            reqs.endpoints.append(Endpoint(
                method=method,
                path=endpoint_path.strip(),
                entity="Unknown",
                operation="custom",
                description=f"{method} {endpoint_path}"
            ))

        # 3. Add metadata
        reqs.metadata = {
            "source_file": str(spec_input) if isinstance(spec_input, Path) else "inline_content",
            "entity_count": len(reqs.entities),
            "endpoint_count": len(reqs.endpoints),
            "extraction_method": "hybrid"
        }

        logger.info(f"Hybrid extraction: {len(reqs.entities)} entities, {len(reqs.endpoints)} endpoints")
        return reqs

    def _extract_field_description(self, entity_name: str, field_name: str, content: str) -> Optional[str]:
        """Extract field description using focused LLM query"""
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
            from src.config.constants import DEFAULT_MODEL
            import asyncio

            # Find context around the field
            field_context_pattern = rf'(?:{entity_name}.*?{field_name}.*?)(.{{0,500}})'
            match = re.search(field_context_pattern, content, re.DOTALL | re.IGNORECASE)
            context = match.group(1) if match else ""

            if not context:
                return None

            prompt = f"""Extract the description for field "{field_name}" in entity "{entity_name}".

Context:
{context[:500]}

Look for keywords indicating enforcement type:
- "auto-calculated", "automática", "se calcula automáticamente" - indicates computed field
- "read-only", "solo lectura", "automática", "inmutable" - indicates immutable field
- "snapshot", "captures", "captura el precio EN ESE MOMENTO" - indicates snapshot behavior

Return ONLY the description text (1-2 sentences maximum), or "NONE" if no description found.
DO NOT return JSON, just the plain text description."""

            client = EnhancedAnthropicClient()

            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=200, temperature=0.0)
                    )
                    response = future.result(timeout=10)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=200, temperature=0.0)
                )

            # Parse response
            if hasattr(response, 'text'):
                desc = response.text.strip()
            elif hasattr(response, 'content'):
                desc = response.content.strip()
            elif isinstance(response, dict):
                desc = response.get('content', '').strip()
            else:
                desc = str(response).strip()

            if desc and desc != "NONE":
                return desc
            return None

        except Exception as e:
            logger.debug(f"Could not extract description for {entity_name}.{field_name}: {e}")
            return None

    def _extract_with_llm(self, content: str) -> Optional[SpecRequirements]:
        """Extract spec requirements using LLM"""
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
            from src.config.constants import DEFAULT_MODEL
            import json
            import asyncio

            prompt = f"""You are an expert API architect. Analyze this specification and extract structured requirements.

            # Specification
            {content[:12000]}

            # Task
            Extract the following components into a JSON structure:
            1. entities: List of data models with fields (name, type, required, constraints, description)
            2. endpoints: List of API endpoints (method, path, description, params)
            3. validations: List of business validations (entity, field, rule)
            4. requirements: List of functional requirements (id, description)

            # JSON Format
            {{
                "entities": [
                    {{
                        "name": "EntityName",
                        "fields": [
                            {{
                                "name": "fieldName",
                                "type": "DataType",
                                "required": true,
                                "constraints": ["constraint1"],
                                "description": "Field description (CRITICAL: include keywords like 'auto-calculated', 'read-only', 'snapshot', 'automática', 'solo lectura')"
                            }}
                        ]
                    }}
                ],
                "endpoints": [
                    {{
                        "method": "POST",
                        "path": "/resource",
                        "description": "Description",
                        "entity": "EntityName",
                        "operation": "create"
                    }}
                ],
                "validations": [
                    {{"field": "fieldName", "rule": "validation rule description"}}
                ],
                "requirements": [
                    {{"id": "F1", "description": "Requirement description"}}
                ]
            }}

            CRITICAL INSTRUCTIONS:
            1. For each field, extract its description from the spec. Look for:
               - "auto-calculated", "automática", "se calcula automáticamente" → Include in description
               - "read-only", "solo lectura", "automática" → Include in description
               - "snapshot", "captures", "captura el precio EN ESE MOMENTO" → Include in description
               - Any text explaining the field behavior → Include in description

            2. JSON VALIDITY REQUIREMENTS:
               - ALWAYS close all strings with matching quotes
               - Escape special characters in strings (quotes, newlines, backslashes)
               - If approaching token limit, STOP at a complete JSON object
               - Better to return fewer complete objects than incomplete JSON
               - All opened brackets {{ [ must be closed }} ]
               - Test your JSON is valid before returning

            3. Return ONLY valid JSON. No markdown formatting, no explanations.
            """

            client = EnhancedAnthropicClient()

            # Run sync with increased token limit
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=8000, temperature=0.0)
                    )
                    response = future.result(timeout=90)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=4000, temperature=0.0)
                )

            # Parse response
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Clean up JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            # Try to parse JSON with robust error handling and multiple repair strategies
            data = None
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError as json_err:
                logger.warning(f"JSON parse error at char {json_err.pos}: {json_err.msg}")

                # Strategy 1: Find last complete JSON object by searching for last valid '}'
                try:
                    # Find all positions of '}' and try parsing up to each one
                    closing_brace_positions = [i for i, char in enumerate(response_text) if char == '}']
                    for pos in reversed(closing_brace_positions):
                        try:
                            truncated = response_text[:pos+1]
                            data = json.loads(truncated)
                            logger.info(f"✅ JSON repaired by truncating to last complete object at position {pos}")
                            break
                        except:
                            continue
                except:
                    pass

                # Strategy 2: Line-by-line truncation with closing brackets
                if data is None:
                    lines = response_text.split('\n')
                    for i in range(len(lines) - 1, max(len(lines) - 50, 0), -1):  # Only try last 50 lines
                        try:
                            truncated = '\n'.join(lines[:i])
                            # Balance brackets
                            open_braces = truncated.count('{') - truncated.count('}')
                            open_brackets = truncated.count('[') - truncated.count(']')
                            if open_braces > 0:
                                truncated += '\n' + '}' * open_braces
                            if open_brackets > 0:
                                truncated += '\n' + ']' * open_brackets
                            data = json.loads(truncated)
                            logger.info(f"✅ JSON repaired by line truncation at line {i}")
                            break
                        except:
                            continue

                # Strategy 3: Return minimal valid structure if all else fails
                if data is None:
                    logger.error(f"Could not repair JSON after multiple strategies. Error was at position {json_err.pos}")
                    logger.error(f"Context around error: ...{response_text[max(0, json_err.pos-100):json_err.pos+100]}...")
                    # Return empty but valid structure
                    logger.warning("Returning empty SpecRequirements due to unparseable JSON")
                    return SpecRequirements()
            
            # Map to objects
            reqs = SpecRequirements()
            
            # Entities
            for e_data in data.get("entities", []):
                fields = [
                    Field(
                        name=f["name"],
                        type=f["type"],
                        required=f.get("required", True),
                        constraints=f.get("constraints", []),
                        description=f.get("description", "")  # ✅ CRITICAL for enforcement detection
                    ) for f in e_data.get("fields", [])
                ]
                reqs.entities.append(Entity(name=e_data["name"], fields=fields))
                
            # Endpoints
            for ep_data in data.get("endpoints", []):
                reqs.endpoints.append(Endpoint(
                    method=ep_data["method"],
                    path=ep_data["path"],
                    entity=ep_data.get("entity", "Unknown"),
                    operation=ep_data.get("operation", "custom"),
                    description=ep_data["description"]
                ))
                
            # Validations
            for v_data in data.get("validations", []):
                reqs.validations.append(Validation(
                    field=v_data.get("field", "unknown"),
                    rule=v_data["rule"]
                ))
                # Also add to business logic
                reqs.business_logic.append(BusinessLogic(
                    type="validation",
                    description=v_data["rule"]
                ))
                
            # Requirements
            for r_data in data.get("requirements", []):
                reqs.requirements.append(Requirement(
                    id=r_data.get("id", f"F{len(reqs.requirements)+1}"),
                    type="functional",
                    priority="MUST",
                    description=r_data["description"]
                ))
                
            return reqs

        except Exception as e:
            logger.error(f"Error in _extract_with_llm: {e}")
            raise e

    def _extract_global_context(self, content: str) -> Optional[GlobalContext]:
        """
        Pass 1: Extract global context from full spec (no truncation).

        This method processes the FULL specification content without truncation
        to extract high-level information:
        - Domain description
        - Entity summaries (names, descriptions, relationships)
        - Entity relationships
        - Business logic rules
        - Endpoint summaries

        Returns small output (~2-3K tokens) despite large input to avoid truncation.

        Args:
            content: Full specification text (NO truncation applied)

        Returns:
            GlobalContext object with domain, entity summaries, relationships, business logic, and endpoints.
            None if extraction fails.
        """
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
            from src.config.constants import DEFAULT_MODEL
            import json
            import asyncio

            # CRITICAL: Pass FULL content (no truncation)
            # Output is small (entity summaries only), so no truncation risk
            prompt = get_global_context_prompt(content)

            client = EnhancedAnthropicClient()

            # Run LLM call
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=4000, temperature=0.0)
                    )
                    response = future.result(timeout=90)
            except RuntimeError:
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=4000, temperature=0.0)
                )

            # Parse response
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Clean up JSON
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            data = json.loads(response_text)

            # Extract entity names for location finding
            entity_names = [e["name"] for e in data.get("entities", [])]

            # Find entity locations in spec
            entity_locations = find_entity_locations(content, entity_names)
            logger.info(f"Found locations for {len(entity_locations)}/{len(entity_names)} entities")

            # Map to GlobalContext object
            entity_summaries = []
            for e_data in data.get("entities", []):
                entity_summaries.append(EntitySummary(
                    name=e_data["name"],
                    location=entity_locations.get(e_data["name"], 0),  # Default to 0 if not found
                    description=e_data.get("description", ""),
                    relationships=e_data.get("relationships", [])
                ))

            relationships = []
            for r_data in data.get("relationships", []):
                relationships.append(EntityRelationship(
                    source=r_data["source"],
                    target=r_data["target"],
                    type=r_data.get("type", "one_to_many"),
                    description=r_data.get("description", "")
                ))

            endpoints = []
            for ep_data in data.get("endpoints", []):
                endpoints.append(EndpointSummary(
                    method=ep_data["method"],
                    path=ep_data["path"],
                    entity=ep_data.get("entity")
                ))

            global_context = GlobalContext(
                domain=data.get("domain", ""),
                entities=entity_summaries,
                relationships=relationships,
                business_logic=data.get("business_logic", []),
                endpoints=endpoints
            )

            logger.info(
                f"✅ Pass 1 complete: Extracted {len(entity_summaries)} entities, "
                f"{len(relationships)} relationships, {len(endpoints)} endpoints"
            )

            return global_context

        except Exception as e:
            logger.error(f"Error in _extract_global_context: {e}", exc_info=True)
            return None

    def _extract_entity_fields_with_regex(
        self,
        entity_name: str,
        context_window: str
    ) -> EntityDetail:
        """
        Extract entity fields using regex patterns (Pass 2).

        Args:
            entity_name: Name of the entity
            context_window: Text window around entity definition

        Returns:
            EntityDetail with extracted fields and enforcement types
        """
        try:
            # Use regex-based field extraction
            fields = extract_entity_fields(entity_name, context_window)

            logger.info(
                f"Extracted {len(fields)} fields for {entity_name} using regex"
            )

            return EntityDetail(entity=entity_name, fields=fields)

        except Exception as e:
            logger.error(f"Error extracting fields for {entity_name}: {e}", exc_info=True)
            return EntityDetail(entity=entity_name, fields=[])

    def _extract_with_hierarchical_llm(
        self,
        spec_content: str
    ) -> Dict[str, EntityDetail]:
        """
        Complete hierarchical extraction: Pass 1 (global) + Pass 2 (detailed).

        Orchestrates:
        - Pass 1: Extract global context from full spec
        - Pass 2: Extract entity fields with context windows

        Args:
            spec_content: Full specification text

        Returns:
            Dictionary mapping entity name -> EntityDetail
        """
        try:
            # PASS 1: Extract global context from full spec
            logger.info("PASS 1: Extracting global context...")
            global_context = self._extract_global_context(spec_content)

            if global_context is None:
                logger.error("Pass 1 extraction failed")
                return {}

            logger.info(
                f"Pass 1 extracted {len(global_context.entities)} entities, "
                f"{len(global_context.relationships)} relationships"
            )

            # PASS 2: Extract detailed fields for each entity
            logger.info("PASS 2: Extracting entity fields with context windows...")
            entity_details = {}

            for entity_summary in global_context.entities:
                entity_name = entity_summary.name
                location = entity_summary.location

                # Extract context window around entity definition
                context_window = extract_context_window(spec_content, location, window=2000)

                # Extract fields using regex patterns
                entity_detail = self._extract_entity_fields_with_regex(
                    entity_name,
                    context_window
                )

                entity_details[entity_name] = entity_detail

                logger.info(
                    f"Entity {entity_name}: {len(entity_detail.fields)} fields extracted"
                )

            logger.info(
                f"Hierarchical extraction complete: "
                f"{len(entity_details)} entities with detailed fields"
            )

            return entity_details

        except Exception as e:
            logger.error(f"Error in hierarchical extraction: {e}", exc_info=True)
            return {}


    def _parse_classification_ground_truth(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse Classification Ground Truth section from spec (YAML format).

        Expected format:
        ## Classification Ground Truth

        F1_create_product:
          domain: crud
          risk: high
          rationale: Creates product entity

        Returns:
            Dictionary mapping requirement_id -> {domain, risk, rationale}
        """
        import yaml

        ground_truth = {}

        try:
            # Try format 1: Classification Ground Truth with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Classification\s+Ground\s+Truth.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Classification\s+Ground\s+Truth.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Classification Ground Truth section found in spec")
                    return ground_truth

                yaml_content = match.group(1).strip()

            # Parse YAML (Bug #11 Fix: use safe_yaml_load with fallback)
            data = safe_yaml_load(yaml_content, default={})

            if data and isinstance(data, dict):
                ground_truth = data
                logger.info(f"Loaded classification ground truth for {len(ground_truth)} requirements")

        except Exception as e:
            logger.warning(f"Failed to parse Classification Ground Truth: {e}")

        return ground_truth

    def _parse_dag_ground_truth(self, content: str) -> Dict[str, Any]:
        """
        Parse Expected Dependency Graph section from spec (YAML format).

        Expected format:
        ## Expected Dependency Graph (Ground Truth)

        ```yaml
        nodes:
          - create_product
          - list_products
          ...

        edges:
          - create_product → list_products
          ...
        ```

        Returns:
            Dictionary with 'nodes' (list) and 'edges' (list of tuples)
        """
        import yaml
        import re as regex_module

        dag_gt = {}

        try:
            # Try format 1: Expected Dependency Graph with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Expected\s+Dependency\s+Graph.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Expected\s+Dependency\s+Graph.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Expected Dependency Graph section found in spec")
                    return dag_gt

                yaml_content = match.group(1).strip()

            # Parse YAML (Bug #11 Fix: use safe_yaml_load with fallback)
            data = safe_yaml_load(yaml_content, default={})

            if data and isinstance(data, dict):
                # Extract nodes
                if 'nodes' in data:
                    # Handle both formats: "nodes: 17" (count) and list of nodes
                    nodes_data = data['nodes']
                    if isinstance(nodes_data, list):
                        dag_gt['nodes'] = nodes_data
                        dag_gt['node_count'] = len(nodes_data)
                    elif isinstance(nodes_data, int):
                        dag_gt['node_count'] = nodes_data

                # Extract edges
                if 'edges' in data:
                    # Handle both formats: "edges: 15" (count) and list of edges
                    edges_data = data['edges']
                    if isinstance(edges_data, list):
                        # Parse edge strings like "create_product → list_products"
                        parsed_edges = []
                        edge_pattern = regex_module.compile(r'(\w+)\s*(?:→|->)\s*(\w+)')

                        for edge_item in edges_data:
                            if isinstance(edge_item, str):
                                edge_match = edge_pattern.search(edge_item)
                                if edge_match:
                                    from_node = edge_match.group(1)
                                    to_node = edge_match.group(2)
                                    parsed_edges.append((from_node, to_node))

                        dag_gt['edges'] = parsed_edges
                        dag_gt['edge_count'] = len(parsed_edges)
                    elif isinstance(edges_data, int):
                        dag_gt['edge_count'] = edges_data

                logger.info(
                    f"Loaded DAG ground truth: "
                    f"{dag_gt.get('node_count', 0)} nodes, "
                    f"{dag_gt.get('edge_count', 0)} edges"
                )

        except Exception as e:
            logger.warning(f"Failed to parse Expected Dependency Graph: {e}")

        return dag_gt

    def _parse_validation_ground_truth(self, content: str) -> Dict[str, Any]:
        """
        Parse Validation Ground Truth section from spec (YAML format).

        Expected format:
        ## Validation Ground Truth

        ```yaml
        validation_count: 6

        validations:
          V1_product_price:
            entity: Product
            field: price
            constraint: gt=0
            description: "Product price must be greater than 0"
          ...
        ```

        Returns:
            Dictionary with 'validation_count' and 'validations' dict
        """
        import yaml

        val_gt = {}

        try:
            # Try format 1: Validation Ground Truth with ```yaml blocks
            # Allow optional whitespace (including blank lines) between header and ```yaml
            section_pattern_blocks = re.compile(
                r'##\s+Validation\s+Ground\s+Truth.*?\n\s*```yaml\n(.*?)\n```',
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern_blocks.search(content)

            if match:
                yaml_content = match.group(1).strip()
            else:
                # Try format 2: Plain YAML without code blocks
                # Capture everything from header until next ## section or end of file
                section_pattern_plain = re.compile(
                    r'##\s+Validation\s+Ground\s+Truth.*?\n(.*?)(?=\n##|\Z)',
                    re.DOTALL | re.IGNORECASE
                )
                match = section_pattern_plain.search(content)

                if not match:
                    logger.debug("No Validation Ground Truth section found in spec")
                    return val_gt

                yaml_content = match.group(1).strip()

            # Parse YAML (Bug #11 Fix: use safe_yaml_load with fallback)
            data = safe_yaml_load(yaml_content, default={})

            if data and isinstance(data, dict):
                # Extract validation_count
                if 'validation_count' in data:
                    val_gt['validation_count'] = data['validation_count']

                # Extract validations
                if 'validations' in data and isinstance(data['validations'], dict):
                    val_gt['validations'] = data['validations']

                logger.info(
                    f"Loaded validation ground truth: "
                    f"{val_gt.get('validation_count', 0)} validations defined"
                )

        except Exception as e:
            logger.warning(f"Failed to parse Validation Ground Truth: {e}")

        return val_gt

    def _generate_classification_ground_truth_with_llm(
        self, content: str, endpoints: List['Endpoint']
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate classification ground truth from natural language spec using LLM.

        This allows specs to be written in any format - the LLM extracts and
        structures the ground truth in standard YAML format.

        Args:
            content: Raw markdown spec content
            endpoints: Parsed endpoints

        Returns:
            Dictionary mapping node names to domain/risk classifications
        """
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

            # Build endpoint summary for LLM
            endpoint_list = "\n".join([
                f"- {ep.method} {ep.path}: {ep.description}"
                for ep in endpoints
            ])

            prompt = f"""Analyze this API specification and generate classification ground truth in YAML format.

# Specification
{content[:3000]}  # Limit context to avoid token limits

# Detected Endpoints
{endpoint_list}

# Task
Generate a YAML classification for each endpoint. For each endpoint, assign:
- A unique requirement ID (F1, F2, etc. sequentially)
- domain: crud | workflow | payment | auth | integration
- risk: low | medium | high

Format:
```yaml
F{{ID}}_{{node_name}}:
  domain: {{domain}}
  risk: {{risk}}
```

Where node_name is derived from the endpoint operation (e.g., create_product, list_products, get_product).

Rules:
- CRUD operations (GET, POST single items, PUT, DELETE) → crud domain, low-medium risk
- Workflows (checkout, payment processing, multi-step operations) → workflow/payment domain, medium-high risk
- List/search operations → crud domain, low risk
- Payment operations → payment domain, high risk

Generate ONLY the YAML block, no explanation."""

            import asyncio

            client = EnhancedAnthropicClient()

            from src.config.constants import DEFAULT_MODEL

            # Handle both sync and async contexts
            try:
                # Try to get running loop (we're inside async context)
                loop = asyncio.get_running_loop()
                # We're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(
                            prompt=prompt,
                            model=DEFAULT_MODEL,
                            max_tokens=2000,
                            temperature=0.0
                        )
                    )
                    response = future.result(timeout=60)
            except RuntimeError:
                # No running loop, we can use run_until_complete
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                response = loop.run_until_complete(
                    client.generate(
                        prompt=prompt,
                        model=DEFAULT_MODEL,
                        max_tokens=2000,
                        temperature=0.0
                    )
                )

            # Response could be SimpleResponse object with .text attribute
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Debug: log response for development
            logger.debug(f"LLM response (first 500 chars): {response_text[:500]}")

            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if not yaml_match:
                # Try without code blocks
                yaml_match = re.search(r'(F\d+_\w+:.*)', response_text, re.DOTALL)

            if yaml_match:
                yaml_content = yaml_match.group(1)
                # Bug #11 Fix: use robust_yaml_parse for LLM responses
                classification_gt = robust_yaml_parse(yaml_content)

                if classification_gt:
                    logger.info(
                        f"✅ Generated classification ground truth with LLM: "
                        f"{len(classification_gt)} entries"
                    )
                    return classification_gt
                else:
                    logger.warning("robust_yaml_parse failed for classification ground truth")
                    return {}
            else:
                logger.warning(f"LLM response did not contain valid YAML. Response preview: {response_text[:200]}")
                return {}

        except ImportError:
            logger.warning("EnhancedAnthropicClient not available, skipping LLM generation")
            return {}
        except Exception as e:
            logger.warning(f"Failed to generate classification ground truth with LLM: {e}")
            return {}

    def _generate_validation_ground_truth_with_llm(
        self, content: str, business_logic: List['BusinessLogic']
    ) -> Dict[str, Any]:
        """
        Generate validation ground truth from natural language spec using LLM.

        Extracts validation rules from Business Validations section and structures
        them in YAML format for ComplianceValidator.

        Args:
            content: Raw markdown spec content
            business_logic: Parsed business logic including validations

        Returns:
            Dictionary with 'validation_count' and 'validations' dict
        """
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient

            # Filter only validations from business logic
            validations_list = [bl for bl in business_logic if bl.type == "validation"]

            if not validations_list:
                logger.debug("No validations found in business logic, skipping LLM generation")
                return {}

            # Build validation summary for LLM
            validation_descriptions = "\n".join([
                f"- {val.description}"
                for val in validations_list
            ])

            prompt = f"""Generate COMPLETE validation ground truth for perfect code generation.

# Specification
{content[:3000]}

# Explicit Validations from Spec
{validation_descriptions}

# STEP-BY-STEP PROCESS (Follow this exactly):

## Step 1: Read each validation description CAREFULLY
For each validation like "Stock >= 0" or "Quantity > 0":
- Identify the FIELD being validated (e.g., "stock", "quantity")
- Identify the OPERATOR (e.g., >=, >, <, <=, ==)
- Identify the NUMERIC VALUE (e.g., 0, 1, 100) - THIS MUST BE A NUMBER, NEVER A FIELD NAME

## Step 2: Map to correct constraint format
- "Stock >= 0" → constraint: ge=0 (NOT ge=stock, NOT ge=quantity)
- "Quantity > 0" → constraint: gt=0 (NOT gt=quantity, NOT gt=stock)
- "Price > 0" → constraint: gt=0 (NOT gt=price)
- "Email format" → constraint: email_format (keyword, no value)
- "ID is UUID" → constraint: uuid_format (keyword, no value)

## Step 3: Determine which ENTITY has this FIELD
Look at the spec to find which entity has this field.
IMPORTANT: Don't confuse similar field names across different entities!

## Step 4: Generate validation entry
Create one validation entry with:
- entity: EntityName (capitalized)
- field: field_name (lowercase)
- constraint: the_constraint (MUST be number or keyword, NEVER a field name)
- description: simple one-line description

# COMMON ERRORS TO AVOID:

❌ WRONG: constraint: ge=quantity (using field name as value)
✅ RIGHT: constraint: ge=0 (using number as value)

❌ WRONG: constraint: gt=stock (using field name as value)
✅ RIGHT: constraint: gt=0 (using number as value)

❌ WRONG: entity: {ChildItem}, field: stock, constraint: ge=0 (wrong entity - stock is in {Resource}, not {ChildItem}!)
✅ RIGHT: entity: {Resource}, field: stock, constraint: ge=0

❌ WRONG: entity: {Resource}, field: quantity, constraint: gt=0 (wrong entity - quantity is in {ChildItem}, not {Resource}!)
✅ RIGHT: entity: {ChildItem}, field: quantity, constraint: gt=0

# VALIDATION TYPES TO GENERATE:

1. **Explicit validations** from Business Validations section (analyze each one carefully)
2. **Implicit validations** for production code:
   - UUID format for all ID fields
   - Email format for email fields
   - Required for non-nullable fields
   - Enum for status/type fields with fixed values
   - Min/max lengths for strings
   - Positive/non-negative for numeric fields that shouldn't be negative

Format:
```yaml
validation_count: {{total_count}}

validations:
  V{{ID}}_{{entity}}_{{field}}:
    entity: {{EntityName}}
    field: {{field_name}}
    constraint: {{constraint_type}}
    description: {{simple_validation_description}}
```

# ALLOWED CONSTRAINT TYPES (constraint value must be NUMBER or KEYWORD - NEVER a field name):

Numeric Constraints (value MUST be a number):
- gt=0 → "greater than 0" (example: price > 0, quantity > 0)
- ge=0 → "greater than or equal to 0" (example: stock >= 0, total >= 0)
- lt=100 → "less than 100" (use actual number, not field name)
- le=100 → "less than or equal to 100" (use actual number, not field name)

Format Constraints (keyword only, NO value):
- email_format → for email fields
- uuid_format → for ID fields (Product.id, Customer.id, etc.)

Presence Constraints (keyword only, NO value):
- required → field must be present and not null

Value Constraints (WITH values - extract from spec):
- enum=VALUE1,VALUE2,VALUE3 → for status/type fields with fixed allowed values
  Example: If spec says 'status: enum ["OPEN", "CLOSED"]' → constraint: enum=OPEN,CLOSED
  Example: If spec says 'status: enum ["PENDING", "PAID", "CANCELLED"]' → constraint: enum=PENDING,PAID,CANCELLED

String Length Constraints (value MUST be a number):
- min_length=1 → minimum string length (use actual number)
- max_length=255 → maximum string length (use actual number)

# VALIDATION CHECKLIST (Check each constraint you write):

Before writing "constraint: X", ask yourself:
1. ✅ Is X a NUMBER (0, 1, 100) or a KEYWORD (required, email_format)?
2. ❌ Is X a field name (quantity, stock, price)? → WRONG! Use the numeric value instead
3. ✅ Does this constraint match the validation description exactly?
4. ✅ Am I using the correct entity for this field?

Example showing CORRECT constraint mapping:
```yaml
# NOTE: These are EXAMPLE entity/field names for LLM guidance.
# The actual entity/field names come from the spec being parsed.
# The compiler is domain-agnostic - it works with ANY domain.
validation_count: 8

validations:
  # Example 1: "Price > 0" → constraint MUST be gt=0 (the number), NOT gt=price (field name)
  V1_entity_price:
    entity: {Entity}
    field: price
    constraint: gt=0
    description: Entity price must be greater than 0

  # Example 2: "Stock >= 0" → constraint MUST be ge=0 (the number), NOT ge=stock or ge=quantity
  V2_entity_stock:
    entity: {Entity}
    field: stock
    constraint: ge=0
    description: Entity stock must be non-negative

  # Example 3: "Item quantity > 0" → entity is {Child}Item (where quantity field exists), NOT {Parent}
  V3_childitem_quantity:
    entity: {Child}Item
    field: quantity
    constraint: gt=0
    description: Item quantity must be greater than 0

  # Example 4: "Email format" → constraint is keyword email_format, NO value needed
  V4_entity_email_format:
    entity: {Entity}
    field: email
    constraint: email_format
    description: Entity email must be valid email format

  # Example 5: All ID fields need UUID format (implicit validation)
  V5_entity_id:
    entity: {Entity}
    field: id
    constraint: uuid_format
    description: Entity ID must be valid UUID

  # Example 6: Non-nullable fields need required constraint (implicit validation)
  V6_entity_name:
    entity: {Entity}
    field: name
    constraint: required
    description: Entity name is required

  # Example 7: Email fields need BOTH email_format AND required (two separate validations)
  V7_entity_email_required:
    entity: {Entity}
    field: email
    constraint: required
    description: Entity email is required

  # Example 8: Status fields with fixed values need enum constraint WITH VALUES
  # If spec says: status: enum ["PENDING", "ACTIVE", "CLOSED"]
  # Then extract the values and write: constraint: enum=PENDING,ACTIVE,CLOSED
  V8_entity_status:
    entity: {Entity}
    field: status
    constraint: enum=PENDING,ACTIVE,CLOSED
    description: Entity status must be PENDING, ACTIVE, or CLOSED
```

CRITICAL YAML FORMATTING RULES:
1. DO NOT use quotes around description values - write them directly without quotes
2. Keep descriptions simple and on a single line
3. Avoid special characters, apostrophes, or quotes in descriptions
4. Each description must be valid YAML without escaping

FINAL REMINDER BEFORE YOU START:
- Read each validation SLOWLY and CAREFULLY
- For "Stock >= 0" write constraint: ge=0 (the NUMBER zero, NOT the word "stock" or "quantity")
- For "Quantity > 0" write constraint: gt=0 (the NUMBER zero, NOT the word "quantity")
- NEVER EVER use a field name (like stock, quantity, price) as a constraint value
- Always use the ACTUAL NUMERIC VALUE from the validation description
- Double-check each entity-field mapping before writing it

Generate validation ground truth that represents what PERFECT production code should have.
This ground truth will be used to validate the generated code, so include ALL validations needed.

Generate ONLY the YAML block, no explanation."""

            import asyncio

            client = EnhancedAnthropicClient()

            from src.config.constants import DEFAULT_MODEL

            # Handle both sync and async contexts
            try:
                # Try to get running loop (we're inside async context)
                loop = asyncio.get_running_loop()
                # We're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(
                            prompt=prompt,
                            model=DEFAULT_MODEL,
                            max_tokens=2000,
                            temperature=0.0
                        )
                    )
                    response = future.result(timeout=60)
            except RuntimeError:
                # No running loop, we can use run_until_complete
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                response = loop.run_until_complete(
                    client.generate(
                        prompt=prompt,
                        model=DEFAULT_MODEL,
                        max_tokens=2000,
                        temperature=0.0
                    )
                )

            # Response could be SimpleResponse object with .text attribute
            if hasattr(response, 'text'):
                response_text = response.text
            elif hasattr(response, 'content'):
                response_text = response.content
            elif isinstance(response, dict):
                response_text = response.get('content', '')
            else:
                response_text = str(response)

            # Debug: log response for development
            logger.debug(f"LLM validation response (first 500 chars): {response_text[:500]}")

            # Extract YAML from response
            yaml_match = re.search(r'```yaml\n(.*?)\n```', response_text, re.DOTALL)
            if not yaml_match:
                # Try without code blocks
                yaml_match = re.search(r'(validation_count:.*)', response_text, re.DOTALL)

            if yaml_match:
                yaml_content = yaml_match.group(1)
                # Bug #11 Fix: use robust_yaml_parse for LLM responses
                validation_gt = robust_yaml_parse(yaml_content)

                if validation_gt:
                    logger.info(
                        f"✅ Generated validation ground truth with LLM: "
                        f"{validation_gt.get('validation_count', 0)} validations"
                    )
                    return validation_gt
                else:
                    logger.warning("robust_yaml_parse failed for validation ground truth")
                    return {}
            else:
                logger.warning(f"LLM response did not contain valid YAML. Response preview: {response_text[:200]}")
                return {}

        except ImportError:
            logger.warning("EnhancedAnthropicClient not available, skipping LLM validation generation")
            return {}
        except Exception as e:
            logger.warning(f"Failed to generate validation ground truth with LLM: {e}")
            return {}
