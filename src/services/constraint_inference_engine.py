"""
Constraint Inference Engine (Phase 3)

Infers missing validation constraints from entity relationship graphs
to achieve 100% validation coverage.
"""

from typing import List, Optional, Dict, Any
from enum import Enum

from src.services.graph_models import (
    EntityRelationshipGraph,
    InferredValidation,
    RelationshipEdge
)
from src.cognitive.ir.validation_model import ValidationRule, ValidationType


class ConstraintInferenceEngine:
    """Infers missing validation constraints from graph structure"""

    def __init__(self, graph: EntityRelationshipGraph):
        self.graph = graph
        self.inferred_validations: List[InferredValidation] = []

    def infer_all_constraints(self) -> List[InferredValidation]:
        """Infer all missing constraints from graph"""
        self.inferred_validations = []

        # Type 1: Cardinality constraints
        self.inferred_validations.extend(self._infer_cardinality_constraints())

        # Type 2: Uniqueness constraints
        self.inferred_validations.extend(self._infer_uniqueness_constraints())

        # Type 3: Foreign key constraints
        self.inferred_validations.extend(self._infer_foreign_key_constraints())

        # Type 4: Workflow state transitions
        self.inferred_validations.extend(self._infer_workflow_constraints())

        # Type 5: Cross-entity business rules
        self.inferred_validations.extend(self._infer_business_rules())

        # Type 6: Aggregate structure constraints
        self.inferred_validations.extend(self._infer_aggregate_constraints())

        return self.inferred_validations

    def _infer_cardinality_constraints(self) -> List[InferredValidation]:
        """Infer constraints from relationship cardinality"""
        validations = []

        for edge in self.graph.edges:
            # One-to-many: many side MUST have foreign key to one side
            if edge.cardinality == ("1", "N"):
                validations.append(InferredValidation(
                    entity=edge.target,
                    attribute=edge.foreign_key_field or f"{edge.source.lower()}_id",
                    validation_type="PRESENCE",
                    condition=f"Foreign key to {edge.source} required by cardinality (1:N)",
                    error_message=f"{edge.target} must reference a {edge.source}",
                    source="cardinality_constraint",
                    confidence=0.95,
                    related_entity=edge.source,
                    related_relationship=(edge.source, edge.target)
                ))

            # One-to-one: both sides MUST have unique foreign key
            elif edge.cardinality == ("1", "1"):
                validations.append(InferredValidation(
                    entity=edge.target,
                    attribute=edge.foreign_key_field or f"{edge.source.lower()}_id",
                    validation_type="UNIQUENESS",
                    condition=f"Foreign key to {edge.source} must be unique (1:1)",
                    error_message=f"Each {edge.target} must reference different {edge.source} instances",
                    source="cardinality_constraint",
                    confidence=0.93,
                    related_entity=edge.source,
                    related_relationship=(edge.source, edge.target)
                ))

            # Many-to-many: requires junction entity with foreign keys
            elif edge.cardinality == ("N", "N"):
                # Typically handled by junction table, but we can infer presence constraints
                validations.append(InferredValidation(
                    entity=edge.target,
                    attribute=None,
                    validation_type="RELATIONSHIP",
                    condition=f"Many-to-many relationship with {edge.source} via junction entity",
                    error_message=f"{edge.target} participates in many-to-many relationship",
                    source="cardinality_constraint",
                    confidence=0.90,
                    related_entity=edge.source,
                    related_relationship=(edge.source, edge.target)
                ))

        return validations

    def _infer_uniqueness_constraints(self) -> List[InferredValidation]:
        """Infer uniqueness constraints from primary keys and identifiers"""
        validations = []

        for entity_name, entity in self.graph.nodes.items():
            # Primary key must be unique
            pk = entity.get_primary_key()
            if pk:
                validations.append(InferredValidation(
                    entity=entity_name,
                    attribute=pk,
                    validation_type="UNIQUENESS",
                    condition="Primary key uniqueness constraint",
                    error_message=f"{pk} must be unique across all {entity_name} instances",
                    source="primary_key_constraint",
                    confidence=0.99
                ))

            # Natural identifiers (email, username, etc.)
            for attr_name, attr in entity.attributes.items():
                if attr.is_unique:
                    validations.append(InferredValidation(
                        entity=entity_name,
                        attribute=attr_name,
                        validation_type="UNIQUENESS",
                        condition=f"Unique constraint on {attr_name}",
                        error_message=f"{attr_name} must be unique",
                        source="unique_constraint",
                        confidence=0.96
                    ))

        return validations

    def _infer_foreign_key_constraints(self) -> List[InferredValidation]:
        """Infer foreign key relationship constraints"""
        validations = []

        for edge in self.graph.edges:
            fk_field = edge.foreign_key_field or f"{edge.source.lower()}_id"

            # Foreign key must reference valid entity
            validations.append(InferredValidation(
                entity=edge.target,
                attribute=fk_field,
                validation_type="RELATIONSHIP",
                condition=f"Foreign key must reference valid {edge.source}",
                error_message=f"Invalid {edge.source} reference in {fk_field}",
                source="foreign_key_constraint",
                confidence=0.94,
                related_entity=edge.source,
                related_relationship=(edge.source, edge.target)
            ))

            # If relationship is required, foreign key must be present
            if edge.required:
                validations.append(InferredValidation(
                    entity=edge.target,
                    attribute=fk_field,
                    validation_type="PRESENCE",
                    condition="Required relationship (non-null foreign key)",
                    error_message=f"{fk_field} is required (relationship is mandatory)",
                    source="required_relationship",
                    confidence=0.93,
                    related_entity=edge.source
                ))

        return validations

    def _infer_workflow_constraints(self) -> List[InferredValidation]:
        """Infer constraints from workflow state transitions"""
        validations = []

        for entity_name, entity in self.graph.nodes.items():
            if entity.lifecycle_states and len(entity.lifecycle_states) > 0:
                status_field = entity.get_status_field()
                if status_field:
                    # Valid state transitions
                    validations.append(InferredValidation(
                        entity=entity_name,
                        attribute=status_field,
                        validation_type="STATUS_TRANSITION",
                        condition=f"Valid status values: {', '.join(entity.lifecycle_states)}",
                        error_message=f"Invalid status for {entity_name}: must be one of {entity.lifecycle_states}",
                        source="workflow_state_constraint",
                        confidence=0.88
                    ))

                    # Status field presence (lifecycle entities need status)
                    validations.append(InferredValidation(
                        entity=entity_name,
                        attribute=status_field,
                        validation_type="PRESENCE",
                        condition="Status field required for lifecycle-aware entity",
                        error_message=f"{status_field} is required for {entity_name}",
                        source="lifecycle_constraint",
                        confidence=0.90
                    ))

        return validations

    def _infer_business_rules(self) -> List[InferredValidation]:
        """Infer business rules from relationship semantics"""
        validations = []

        # Rule 1: Cascade delete implications
        for edge in self.graph.edges:
            if edge.cascade_delete:
                # When parent is deleted, all children must be deleted
                validations.append(InferredValidation(
                    entity=edge.source,
                    attribute=None,
                    validation_type="WORKFLOW_CONSTRAINT",
                    condition=f"Cascade delete: deleting {edge.source} requires deleting dependent {edge.target}",
                    error_message=f"Cannot delete {edge.source} with existing {edge.target} records",
                    source="cascade_delete_rule",
                    confidence=0.92,
                    related_entity=edge.target,
                    related_relationship=(edge.source, edge.target)
                ))

        # Rule 2: Aggregate root owns entities
        for entity_name, entity in self.graph.nodes.items():
            if entity.is_aggregate_root:
                members = self.graph.get_aggregate_members(entity_name)
                for member_name in members:
                    fk_field = f"{entity_name.lower()}_id"
                    validations.append(InferredValidation(
                        entity=member_name,
                        attribute=fk_field,
                        validation_type="PRESENCE",
                        condition=f"{member_name} is part of {entity_name} aggregate",
                        error_message=f"{member_name} must belong to a {entity_name}",
                        source="aggregate_membership",
                        confidence=0.87,
                        related_entity=entity_name
                    ))

        return validations

    def _infer_aggregate_constraints(self) -> List[InferredValidation]:
        """Infer constraints from aggregate structure"""
        validations = []

        for entity_name, entity in self.graph.nodes.items():
            if entity.is_aggregate_root:
                # Aggregate roots typically have identity
                validations.append(InferredValidation(
                    entity=entity_name,
                    attribute=entity.get_primary_key() or "id",
                    validation_type="PRESENCE",
                    condition="Aggregate roots must have identity",
                    error_message=f"{entity_name} aggregate root requires unique identity",
                    source="aggregate_identity",
                    confidence=0.91
                ))

            # Entities with required relationships
            incoming = self.graph.get_incoming_relationships(entity_name)
            for rel in incoming:
                if rel.required:
                    fk_field = rel.foreign_key_field or f"{rel.source.lower()}_id"
                    validations.append(InferredValidation(
                        entity=entity_name,
                        attribute=fk_field,
                        validation_type="PRESENCE",
                        condition=f"Required relationship from {rel.source}",
                        error_message=f"{entity_name} must have reference to {rel.source}",
                        source="required_relationship",
                        confidence=0.89,
                        related_entity=rel.source
                    ))

        return validations

    def convert_to_validation_rules(self) -> List[ValidationRule]:
        """Convert inferred validations to ValidationRule objects"""
        rules = []

        for inference in self.inferred_validations:
            # Map validation type strings to ValidationType enum
            try:
                val_type = ValidationType[inference.validation_type]
            except KeyError:
                # Fallback for unknown types
                val_type = ValidationType.PRESENCE

            rule = ValidationRule(
                entity=inference.entity,
                attribute=inference.attribute or "",
                type=val_type,
                condition=inference.condition,
                error_message=inference.error_message,
                confidence=inference.confidence,
                source="graph_inference"
            )
            rules.append(rule)

        return rules
