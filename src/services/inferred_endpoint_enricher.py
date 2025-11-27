"""
Inferred Endpoint Enricher - IR-Level Best Practice Injection

Adds inferred endpoints to ApplicationIR BEFORE code generation.
This ensures IR remains the single source of truth.

Key principle: If it appears in code, it MUST appear in IR first.
"""

import logging
import re
from typing import List, Dict, Set, Optional
from dataclasses import dataclass

from src.cognitive.ir.api_model import (
    Endpoint,
    HttpMethod,
    APIModelIR,
    APIParameter,
    ParameterLocation,
    InferenceSource,
)

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

    def enrich(self, api_model: APIModelIR) -> APIModelIR:
        """
        Enrich APIModelIR with inferred endpoints.

        Args:
            api_model: Original APIModelIR from spec extraction

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
    strict_mode: bool = False
) -> APIModelIR:
    """
    Convenience function to enrich APIModelIR.

    Args:
        api_model: Original APIModelIR
        strict_mode: If True, skip inference

    Returns:
        Enriched APIModelIR
    """
    config = EnrichmentConfig(strict_mode=strict_mode)
    enricher = InferredEndpointEnricher(config)
    return enricher.enrich(api_model)
