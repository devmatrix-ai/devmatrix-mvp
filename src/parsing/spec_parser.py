"""
Enhanced Specification Parser for Code Generation Pipeline

Parses functional requirements from markdown specs including:
- Markdown headers: **F1. Description**, ### Section
- Entity definitions with fields, types, constraints
- Endpoint specifications with methods, paths, parameters
- Business logic: validations, rules, calculations

Target: Extract functional requirements from any natural language spec
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import re
import logging
import yaml

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
    Enhanced markdown parser for functional requirements

    Extracts:
    - Functional requirements (F1-F99) from bold headers **F1. Description**
    - Non-functional requirements (NF1-NF99)
    - Entities with fields, types, constraints
    - Endpoints with methods, paths, parameters
    - Business logic (validations, rules, state machines)
    """

    def __init__(self) -> None:
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


    def parse(self, spec_path: Path) -> SpecRequirements:
        """
        Parse specification markdown file
        
        Args:
            spec_path: Path to markdown specification file
            
        Returns:
            SpecRequirements with all extracted components
        """
        try:
            content = spec_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read spec file {spec_path}: {e}")
            return SpecRequirements()

        logger.info(f"Parsing specification: {spec_path.name}")

        # Try LLM-based extraction (Exclusive method)
        try:
            logger.info("Attempting LLM-based extraction...")
            result = self._extract_with_llm(content)
            if result and (result.entities or result.endpoints):
                logger.info("LLM extraction successful")
                # Add metadata
                result.metadata = {
                    "source_file": str(spec_path),
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
            # No fallback as requested
            raise e

    def _extract_with_llm(self, content: str) -> Optional[SpecRequirements]:
        """Extract spec requirements using LLM"""
        try:
            from src.llm.enhanced_anthropic_client import EnhancedAnthropicClient
            from src.config.constants import DEFAULT_MODEL
            import json
            import asyncio

            prompt = f"""You are an expert API architect. Analyze this specification and extract structured requirements.
            
            # Specification
            {content[:8000]}
            
            # Task
            Extract the following components into a JSON structure:
            1. entities: List of data models with fields (name, type, required, constraints)
            2. endpoints: List of API endpoints (method, path, description, params)
            3. validations: List of business validations (entity, field, rule)
            4. requirements: List of functional requirements (id, description)
            
            # JSON Format
            {{
                "entities": [
                    {{
                        "name": "EntityName",
                        "fields": [
                            {{"name": "fieldName", "type": "DataType", "required": true, "constraints": ["constraint1"]}}
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
            
            Return ONLY valid JSON. No markdown formatting.
            """

            client = EnhancedAnthropicClient()
            
            # Run sync
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        client.generate(prompt=prompt, model=DEFAULT_MODEL, max_tokens=4000, temperature=0.0)
                    )
                    response = future.result(timeout=60)
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
            
            data = json.loads(response_text)
            
            # Map to objects
            reqs = SpecRequirements()
            
            # Entities
            for e_data in data.get("entities", []):
                fields = [
                    Field(
                        name=f["name"], 
                        type=f["type"], 
                        required=f.get("required", True),
                        constraints=f.get("constraints", [])
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

            # Parse YAML
            data = yaml.safe_load(yaml_content)

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

            # Parse YAML
            data = yaml.safe_load(yaml_content)

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

            # Parse YAML
            data = yaml.safe_load(yaml_content)

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
                classification_gt = yaml.safe_load(yaml_content)

                logger.info(
                    f"✅ Generated classification ground truth with LLM: "
                    f"{len(classification_gt)} entries"
                )
                return classification_gt
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
Look at the spec to find which entity (Product, Customer, Cart, etc.) has this field.
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

❌ WRONG: entity: CartItem, field: stock, constraint: ge=0 (wrong entity - stock is in Product, not CartItem!)
✅ RIGHT: entity: Product, field: stock, constraint: ge=0

❌ WRONG: entity: Product, field: quantity, constraint: gt=0 (wrong entity - quantity is in CartItem/OrderItem, not Product!)
✅ RIGHT: entity: CartItem, field: quantity, constraint: gt=0

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
validation_count: 8

validations:
  # Example 1: "Price > 0" → constraint MUST be gt=0 (the number), NOT gt=price (field name)
  V1_product_price:
    entity: Product
    field: price
    constraint: gt=0
    description: Product price must be greater than 0

  # Example 2: "Stock >= 0" → constraint MUST be ge=0 (the number), NOT ge=stock or ge=quantity
  V2_product_stock:
    entity: Product
    field: stock
    constraint: ge=0
    description: Product stock must be non-negative

  # Example 3: "Cart item quantity > 0" → entity is CartItem (where quantity field exists), NOT Product
  V3_cartitem_quantity:
    entity: CartItem
    field: quantity
    constraint: gt=0
    description: Cart item quantity must be greater than 0

  # Example 4: "Email format" → constraint is keyword email_format, NO value needed
  V4_customer_email_format:
    entity: Customer
    field: email
    constraint: email_format
    description: Customer email must be valid email format

  # Example 5: All ID fields need UUID format (implicit validation)
  V5_product_id:
    entity: Product
    field: id
    constraint: uuid_format
    description: Product ID must be valid UUID

  # Example 6: Non-nullable fields need required constraint (implicit validation)
  V6_product_name:
    entity: Product
    field: name
    constraint: required
    description: Product name is required

  # Example 7: Email fields need BOTH email_format AND required (two separate validations)
  V7_customer_email_required:
    entity: Customer
    field: email
    constraint: required
    description: Customer email is required

  # Example 8: Status fields with fixed values need enum constraint WITH VALUES
  # If spec says: status: enum ["PENDING_PAYMENT", "PAID", "CANCELLED"]
  # Then extract the values and write: constraint: enum=PENDING_PAYMENT,PAID,CANCELLED
  V8_order_status:
    entity: Order
    field: status
    constraint: enum=PENDING_PAYMENT,PAID,CANCELLED
    description: Order status must be PENDING_PAYMENT, PAID, or CANCELLED
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
                validation_gt = yaml.safe_load(yaml_content)

                logger.info(
                    f"✅ Generated validation ground truth with LLM: "
                    f"{validation_gt.get('validation_count', 0)} validations"
                )
                return validation_gt
            else:
                logger.warning(f"LLM response did not contain valid YAML. Response preview: {response_text[:200]}")
                return {}

        except ImportError:
            logger.warning("EnhancedAnthropicClient not available, skipping LLM validation generation")
            return {}
        except Exception as e:
            logger.warning(f"Failed to generate validation ground truth with LLM: {e}")
            return {}
