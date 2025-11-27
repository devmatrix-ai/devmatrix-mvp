"""
Inferred Endpoint Enricher - IR-Level Best Practice Injection

Adds inferred endpoints to ApplicationIR BEFORE code generation.
This ensures IR remains the single source of truth.

Key principle: If it appears in code, it MUST appear in IR first.
"""

import logging
import re
from typing import List, Dict, Set, Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.cognitive.ir.api_model import (
    Endpoint,
    HttpMethod,
    APIModelIR,
    APIParameter,
    ParameterLocation,
    InferenceSource,
)

# Avoid circular imports
if TYPE_CHECKING:
    from src.cognitive.ir.domain_model import DomainModelIR

logger = logging.getLogger(__name__)


@dataclass
class InferenceRule:
    """Definition of an inference rule."""
    name: str
    source: InferenceSource
    reason: str
    enabled: bool = True


@dataclass
class EnrichmentConfig:
    """Configuration for endpoint enrichment."""
    strict_mode: bool = False  # True = only spec endpoints, False = + inferred
    infer_list_endpoints: bool = True
    infer_delete_endpoints: bool = True
    infer_health_endpoints: bool = True
    infer_metrics_endpoint: bool = True


class InferredEndpointEnricher:
    """
    Enriches APIModelIR with inferred best-practice endpoints.

    All inferred endpoints are marked with:
    - inferred: True
    - inference_source: InferenceSource enum
    - inference_reason: Human-readable explanation

    This ensures complete traceability and auditability.
    """

    def __init__(self, config: Optional[EnrichmentConfig] = None):
        self.config = config or EnrichmentConfig()
        self._inferred_count = 0

    def enrich(
        self,
        api_model: APIModelIR,
        domain_model: Optional['DomainModelIR'] = None,
        flows_data: Optional[List[Dict]] = None
    ) -> APIModelIR:
        """
        Enrich APIModelIR with inferred endpoints.

        Bug #47 Fix: Now infers custom operations and nested resources.

        Args:
            api_model: Original APIModelIR from spec extraction
            domain_model: DomainModelIR for relationship-based inference
            flows_data: Raw flow data for custom operation detection

        Returns:
            Enriched APIModelIR with inferred endpoints added
        """
        if self.config.strict_mode:
            logger.info("🔒 Strict mode enabled - skipping endpoint inference")
            return api_model

        self._inferred_count = 0
        existing_endpoints = set(
            (e.method.value, self._normalize_path(e.path))
            for e in api_model.endpoints
        )

        new_endpoints: List[Endpoint] = []

        # Infer list endpoints (GET /resource/)
        if self.config.infer_list_endpoints:
            new_endpoints.extend(
                self._infer_list_endpoints(api_model, existing_endpoints)
            )

        # Infer delete endpoints (DELETE /resource/{id})
        if self.config.infer_delete_endpoints:
            new_endpoints.extend(
                self._infer_delete_endpoints(api_model, existing_endpoints)
            )

        # Bug #47 Fix: Infer custom operations from flows
        if flows_data:
            new_endpoints.extend(
                self._infer_custom_operations(flows_data, existing_endpoints)
            )

        # Bug #47 Fix: Infer nested resource endpoints from relationships
        if domain_model:
            new_endpoints.extend(
                self._infer_nested_resource_endpoints(domain_model, existing_endpoints)
            )

        # Infer health endpoints
        if self.config.infer_health_endpoints:
            new_endpoints.extend(
                self._infer_health_endpoints(existing_endpoints)
            )

        # Infer metrics endpoint
        if self.config.infer_metrics_endpoint:
            new_endpoints.extend(
                self._infer_metrics_endpoint(existing_endpoints)
            )

        # Add inferred endpoints to model
        all_endpoints = list(api_model.endpoints) + new_endpoints

        logger.info(
            f"📊 Endpoint enrichment complete: "
            f"{len(api_model.endpoints)} spec + {self._inferred_count} inferred = "
            f"{len(all_endpoints)} total"
        )

        return APIModelIR(
            endpoints=all_endpoints,
            schemas=api_model.schemas,
            base_path=api_model.base_path,
            version=api_model.version,
        )

    def _infer_list_endpoints(
        self,
        api_model: APIModelIR,
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """Infer GET /resource/ (list) for resources with POST."""
        inferred = []

        # Find resources that have POST but no GET list
        resources = self._extract_resources(api_model)

        for resource in resources:
            list_path = f"/{resource}"
            normalized = self._normalize_path(list_path)

            if ("GET", normalized) not in existing:
                endpoint = Endpoint(
                    path=list_path,
                    method=HttpMethod.GET,
                    operation_id=f"list_{resource}",
                    summary=f"List all {resource}",
                    description=f"Retrieve a list of all {resource} (inferred best practice)",
                    tags=[resource],
                    auth_required=True,
                    inferred=True,
                    inference_source=InferenceSource.CRUD_BEST_PRACTICE,
                    inference_reason=f"CRUD best practice: list endpoint for {resource}",
                )
                inferred.append(endpoint)
                existing.add(("GET", normalized))
                self._inferred_count += 1
                logger.debug(f"  + Inferred: GET {list_path}")

        return inferred

    def _infer_delete_endpoints(
        self,
        api_model: APIModelIR,
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """Infer DELETE /resource/{id} for resources without delete."""
        inferred = []

        resources = self._extract_resources(api_model)

        for resource in resources:
            # Check for singular resource name
            singular = self._singularize(resource)
            delete_path = f"/{resource}/{{id}}"
            normalized = self._normalize_path(delete_path)

            if ("DELETE", normalized) not in existing:
                endpoint = Endpoint(
                    path=delete_path,
                    method=HttpMethod.DELETE,
                    operation_id=f"delete_{singular}",
                    summary=f"Delete a {singular}",
                    description=f"Delete a specific {singular} by ID (inferred best practice)",
                    parameters=[
                        APIParameter(
                            name="id",
                            location=ParameterLocation.PATH,
                            data_type="string",
                            required=True,
                            description=f"The {singular} ID",
                        )
                    ],
                    tags=[resource],
                    auth_required=True,
                    inferred=True,
                    inference_source=InferenceSource.CRUD_BEST_PRACTICE,
                    inference_reason=f"CRUD best practice: delete endpoint for {singular}",
                )
                inferred.append(endpoint)
                existing.add(("DELETE", normalized))
                self._inferred_count += 1
                logger.debug(f"  + Inferred: DELETE {delete_path}")

        return inferred

    def _infer_health_endpoints(
        self,
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """Infer health check endpoints."""
        inferred = []

        health_endpoints = [
            ("/health", "health_check", "Basic health check"),
            ("/health/ready", "readiness_check", "Readiness check with dependencies"),
        ]

        for path, op_id, summary in health_endpoints:
            normalized = self._normalize_path(path)

            if ("GET", normalized) not in existing:
                endpoint = Endpoint(
                    path=path,
                    method=HttpMethod.GET,
                    operation_id=op_id,
                    summary=summary,
                    description=f"{summary} (inferred infrastructure best practice)",
                    tags=["health"],
                    auth_required=False,
                    inferred=True,
                    inference_source=InferenceSource.INFRA_BEST_PRACTICE,
                    inference_reason="Infrastructure best practice: health endpoints",
                )
                inferred.append(endpoint)
                existing.add(("GET", normalized))
                self._inferred_count += 1
                logger.debug(f"  + Inferred: GET {path}")

        return inferred

    def _infer_metrics_endpoint(
        self,
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """Infer metrics endpoint for observability."""
        inferred = []
        path = "/metrics"
        normalized = self._normalize_path(path)

        if ("GET", normalized) not in existing:
            endpoint = Endpoint(
                path=path,
                method=HttpMethod.GET,
                operation_id="get_metrics",
                summary="Prometheus metrics",
                description="Prometheus-compatible metrics endpoint (inferred infrastructure best practice)",
                tags=["observability"],
                auth_required=False,
                inferred=True,
                inference_source=InferenceSource.INFRA_BEST_PRACTICE,
                inference_reason="Infrastructure best practice: metrics endpoint",
            )
            inferred.append(endpoint)
            existing.add(("GET", normalized))
            self._inferred_count += 1
            logger.debug(f"  + Inferred: GET {path}")

        return inferred

    def _infer_custom_operations(
        self,
        flows_data: List[Dict],
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """
        Bug #47 Fix: Infer custom operation endpoints from flow descriptions.

        Detects patterns like:
        - "Desactivar Producto" → PATCH /products/{id}/deactivate
        - "Activar Producto" → PATCH /products/{id}/activate
        - "Agregar al Carrito" → PUT /carts/{id}/items/{product_id}
        """
        inferred = []

        # Custom operation patterns (action → HTTP method + path suffix)
        CUSTOM_OPS = {
            # Deactivation/activation
            "deactivate": ("PATCH", "/deactivate"),
            "desactivar": ("PATCH", "/deactivate"),
            "activate": ("PATCH", "/activate"),
            "activar": ("PATCH", "/activate"),
            # Cart/order operations
            "checkout": ("POST", "/checkout"),
            "cancel": ("POST", "/cancel"),
            "cancelar": ("POST", "/cancel"),
            "pay": ("POST", "/pay"),
            "pagar": ("POST", "/pay"),
        }

        for flow in flows_data:
            flow_name = flow.get("name", "").lower()
            flow_desc = flow.get("description", "").lower()
            target_entities = flow.get("target_entities", [])

            # Check if flow name contains custom operation
            for operation, (method, path_suffix) in CUSTOM_OPS.items():
                if operation in flow_name or operation in flow_desc:
                    # Infer resource from target entities
                    for entity in target_entities:
                        entity_lower = entity.lower()
                        # Pluralize entity name
                        resource = self._pluralize(entity_lower)
                        path = f"/{resource}/{{id}}{path_suffix}"
                        normalized = self._normalize_path(path)

                        if (method, normalized) not in existing:
                            endpoint = Endpoint(
                                path=path,
                                method=HttpMethod[method],
                                operation_id=f"{operation}_{entity_lower}",
                                summary=f"{operation.capitalize()} {entity}",
                                description=f"Custom operation: {flow_name} (inferred from flow)",
                                parameters=[
                                    APIParameter(
                                        name="id",
                                        location=ParameterLocation.PATH,
                                        data_type="string",
                                        required=True,
                                        description=f"The {entity_lower} ID",
                                    )
                                ],
                                tags=[resource],
                                auth_required=True,
                                inferred=True,
                                inference_source=InferenceSource.SPEC,
                                inference_reason=f"Custom operation from flow: {flow.get('name')}",
                            )
                            inferred.append(endpoint)
                            existing.add((method, normalized))
                            self._inferred_count += 1
                            logger.debug(f"  + Inferred custom op: {method} {path}")

        return inferred

    def _infer_nested_resource_endpoints(
        self,
        domain_model: 'DomainModelIR',
        existing: Set[tuple]
    ) -> List[Endpoint]:
        """
        Bug #47 Fix: Infer nested resource endpoints from entity relationships.

        Detects patterns like:
        - Cart has CartItems → PUT /carts/{id}/items/{product_id}
        - Cart has CartItems → DELETE /carts/{id}/items/{product_id}
        - Order has OrderItems → GET /orders/{id}/items
        """
        inferred = []

        # Patterns for nested resources
        NESTED_PATTERNS = {
            "cartitem": ("cart", "carts", "item", "product_id"),
            "orderitem": ("order", "orders", "item", "product_id"),
        }

        for entity in domain_model.entities:
            entity_lower = entity.name.lower()

            # Check if this is a child entity (CartItem, OrderItem)
            for child_pattern, (parent_singular, parent_plural, item_name, item_id_field) in NESTED_PATTERNS.items():
                if child_pattern in entity_lower:
                    # Infer: PUT /parents/{id}/items/{item_id}
                    add_path = f"/{parent_plural}/{{id}}/{item_name}s/{{" + item_id_field + "}}"
                    add_normalized = self._normalize_path(add_path)

                    if ("PUT", add_normalized) not in existing:
                        endpoint = Endpoint(
                            path=add_path,
                            method=HttpMethod.PUT,
                            operation_id=f"add_{item_name}_to_{parent_singular}",
                            summary=f"Add item to {parent_singular}",
                            description=f"Add/update item in {parent_singular} (nested resource)",
                            parameters=[
                                APIParameter(
                                    name="id",
                                    location=ParameterLocation.PATH,
                                    data_type="string",
                                    required=True,
                                    description=f"The {parent_singular} ID",
                                ),
                                APIParameter(
                                    name=item_id_field,
                                    location=ParameterLocation.PATH,
                                    data_type="string",
                                    required=True,
                                    description=f"The {item_name} ID",
                                ),
                            ],
                            tags=[parent_plural],
                            auth_required=True,
                            inferred=True,
                            inference_source=InferenceSource.CRUD_BEST_PRACTICE,
                            inference_reason=f"Nested resource endpoint for {entity.name}",
                        )
                        inferred.append(endpoint)
                        existing.add(("PUT", add_normalized))
                        self._inferred_count += 1
                        logger.debug(f"  + Inferred nested: PUT {add_path}")

                    # Infer: DELETE /parents/{id}/items/{item_id}
                    delete_path = f"/{parent_plural}/{{id}}/{item_name}s/{{" + item_id_field + "}}"
                    delete_normalized = self._normalize_path(delete_path)

                    if ("DELETE", delete_normalized) not in existing:
                        endpoint = Endpoint(
                            path=delete_path,
                            method=HttpMethod.DELETE,
                            operation_id=f"remove_{item_name}_from_{parent_singular}",
                            summary=f"Remove item from {parent_singular}",
                            description=f"Remove item from {parent_singular} (nested resource)",
                            parameters=[
                                APIParameter(
                                    name="id",
                                    location=ParameterLocation.PATH,
                                    data_type="string",
                                    required=True,
                                    description=f"The {parent_singular} ID",
                                ),
                                APIParameter(
                                    name=item_id_field,
                                    location=ParameterLocation.PATH,
                                    data_type="string",
                                    required=True,
                                    description=f"The {item_name} ID",
                                ),
                            ],
                            tags=[parent_plural],
                            auth_required=True,
                            inferred=True,
                            inference_source=InferenceSource.CRUD_BEST_PRACTICE,
                            inference_reason=f"Nested resource endpoint for {entity.name}",
                        )
                        inferred.append(endpoint)
                        existing.add(("DELETE", delete_normalized))
                        self._inferred_count += 1
                        logger.debug(f"  + Inferred nested: DELETE {delete_path}")

        return inferred

    def _pluralize(self, word: str) -> str:
        """Simple pluralization (product -> products)."""
        if word.endswith("y"):
            return word[:-1] + "ies"
        elif word.endswith("s"):
            return word + "es"
        else:
            return word + "s"

    def _extract_resources(self, api_model: APIModelIR) -> Set[str]:
        """Extract resource names from existing endpoints."""
        resources = set()

        for endpoint in api_model.endpoints:
            # Extract first path segment as resource name
            # /products/{id} -> products
            # /carts/{id}/items -> carts
            parts = endpoint.path.strip("/").split("/")
            if parts and parts[0]:
                resource = parts[0]
                # Skip infrastructure paths
                if resource not in {"health", "metrics", "docs", "openapi.json"}:
                    resources.add(resource)

        return resources

    def _normalize_path(self, path: str) -> str:
        """Normalize path for comparison (replace params with {_})."""
        return re.sub(r'\{[^}]+\}', '{_}', path.strip("/"))

    def _singularize(self, word: str) -> str:
        """Simple singularization (products -> product)."""
        if word.endswith("ies"):
            return word[:-3] + "y"
        elif word.endswith("es"):
            return word[:-2]
        elif word.endswith("s"):
            return word[:-1]
        return word

    def get_inferred_count(self) -> int:
        """Get count of inferred endpoints from last enrichment."""
        return self._inferred_count


# Singleton with default config
_enricher: Optional[InferredEndpointEnricher] = None


def get_endpoint_enricher(
    config: Optional[EnrichmentConfig] = None
) -> InferredEndpointEnricher:
    """Get endpoint enricher instance."""
    global _enricher
    if _enricher is None or config is not None:
        _enricher = InferredEndpointEnricher(config)
    return _enricher


def enrich_api_model(
    api_model: APIModelIR,
    strict_mode: bool = False,
    domain_model: Optional['DomainModelIR'] = None,
    flows_data: Optional[List[Dict]] = None
) -> APIModelIR:
    """
    Convenience function to enrich APIModelIR.

    Bug #47 Fix: Now accepts domain_model and flows_data for advanced inference.

    Args:
        api_model: Original APIModelIR
        strict_mode: If True, skip inference
        domain_model: DomainModelIR for relationship-based inference
        flows_data: Raw flow data for custom operation detection

    Returns:
        Enriched APIModelIR
    """
    config = EnrichmentConfig(strict_mode=strict_mode)
    enricher = InferredEndpointEnricher(config)
    return enricher.enrich(api_model, domain_model, flows_data)
