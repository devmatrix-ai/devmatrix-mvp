"""
Structured Spec Parser for YAML/JSON specifications.

Simple, reliable parser for structured specifications with explicit enforcement types.
No LLM complexity, no regex fragility - just straightforward YAML parsing.
"""
import yaml
import logging
from pathlib import Path
from typing import Union

from src.parsing.spec_parser import SpecRequirements, Entity, Field, Endpoint
from src.utils.yaml_helpers import safe_yaml_load

logger = logging.getLogger(__name__)


class StructuredSpecParser:
    """Parser for structured YAML/JSON specifications"""

    def parse(self, spec_input: Union[Path, str]) -> SpecRequirements:
        """
        Parse structured YAML specification.

        Args:
            spec_input: Path to YAML file OR YAML string content

        Returns:
            SpecRequirements with all extracted components
        """
        try:
            # Handle both Path objects and string content
            if isinstance(spec_input, Path):
                content = spec_input.read_text(encoding="utf-8")
                spec_name = spec_input.name
            else:
                content = spec_input
                spec_name = "inline_spec"

            # Parse YAML with robust error handling
            spec_data = safe_yaml_load(content, default=None)
            if spec_data is None:
                logger.warning(f"YAML parsing failed for {spec_name}, returning empty spec")
                return SpecRequirements()

            logger.info(f"Parsing structured specification: {spec_name}")

            reqs = SpecRequirements()

            # Extract metadata
            metadata = spec_data.get("metadata", {})
            reqs.metadata = {
                "spec_name": metadata.get("name", spec_name),
                "version": metadata.get("version", "1.0"),
                "description": metadata.get("description", ""),
                "extraction_method": "structured_yaml"
            }

            # Extract entities
            for entity_data in spec_data.get("entities", []):
                fields = []
                for field_data in entity_data.get("fields", []):
                    # Build description with enforcement keywords for BusinessLogicExtractor
                    description = field_data.get("description", "")
                    enforcement = field_data.get("enforcement")

                    # Add enforcement keyword to description for detection
                    if enforcement == "computed_field":
                        description = f"{description} (auto-calculated, automática)"
                    elif enforcement == "immutable":
                        description = f"{description} (read-only, solo lectura, inmutable)"

                    field = Field(
                        name=field_data["name"],
                        type=field_data["type"],
                        required=field_data.get("required", True),
                        unique=field_data.get("unique", False),
                        primary_key=field_data.get("primary_key", False),
                        constraints=field_data.get("constraints", []),
                        description=description,
                        default=field_data.get("default")
                    )
                    fields.append(field)

                entity = Entity(
                    name=entity_data["name"],
                    fields=fields,
                    description=entity_data.get("description", "")
                )
                reqs.entities.append(entity)

            # Extract endpoints
            for endpoint_data in spec_data.get("endpoints", []):
                endpoint = Endpoint(
                    method=endpoint_data["method"],
                    path=endpoint_data["path"],
                    entity=endpoint_data.get("entity", "Unknown"),
                    operation=endpoint_data.get("operation_id", "custom"),
                    description=endpoint_data.get("description", "")
                )
                reqs.endpoints.append(endpoint)

            # Update metadata counts
            reqs.metadata["entity_count"] = len(reqs.entities)
            reqs.metadata["endpoint_count"] = len(reqs.endpoints)

            logger.info(
                f"Parsed {len(reqs.entities)} entities, "
                f"{len(reqs.endpoints)} endpoints from structured spec"
            )

            return reqs

        except Exception as e:
            logger.error(f"Failed to parse structured spec: {e}", exc_info=True)
            return SpecRequirements()
