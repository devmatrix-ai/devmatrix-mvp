"""
Entity Relationship Graph Builder (Phase 3)

Constructs semantic graphs from specifications to enable
relationship-aware validation inference.
"""

from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import networkx as nx

from src.services.graph_models import (
    EntityNode,
    AttributeNode,
    RelationshipEdge,
    RelationshipDirection,
    CardinalityType,
    GraphMetrics
)


class EntityRelationshipGraphBuilder:
    """Builds entity relationship graphs from specifications"""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec
        self.graph = nx.DiGraph()  # Directed graph
        self.nodes: Dict[str, EntityNode] = {}
        self.edges: List[RelationshipEdge] = []
        self.metrics = GraphMetrics()

    def build(self) -> 'EntityRelationshipGraph':
        """Build complete graph from specification"""
        # Step 1: Create nodes for each entity
        self._create_entity_nodes()

        # Step 2: Create edges for relationships
        self._create_relationship_edges()

        # Step 3: Analyze cardinality and constraints
        self._analyze_cardinality()

        # Step 4: Detect aggregate roots and boundaries
        self._detect_aggregate_roots()

        # Step 5: Analyze workflow states
        self._analyze_workflows()

        # Step 6: Compute transitive relationships
        self._compute_transitive_relationships()

        # Step 7: Calculate graph metrics
        self._calculate_metrics()

        return EntityRelationshipGraph(
            nodes=self.nodes,
            edges=self.edges,
            graph=self.graph,
            metrics=self.metrics
        )

    def _create_entity_nodes(self):
        """Create EntityNode for each entity in spec"""
        entities = self.spec.get("entities", {})

        if isinstance(entities, dict):
            # Format: {"EntityName": {...attributes...}}
            for entity_name, entity_spec in entities.items():
                node = self._create_node_from_dict(entity_name, entity_spec)
                self.nodes[entity_name] = node
                self.graph.add_node(entity_name, entity=node)
        elif isinstance(entities, list):
            # Format: [{"name": "EntityName", ...}]
            for entity_spec in entities:
                if isinstance(entity_spec, dict) and "name" in entity_spec:
                    entity_name = entity_spec["name"]
                    node = self._create_node_from_dict(entity_name, entity_spec)
                    self.nodes[entity_name] = node
                    self.graph.add_node(entity_name, entity=node)

    def _create_node_from_dict(self, entity_name: str, entity_spec: Dict) -> EntityNode:
        """Create EntityNode from dictionary specification"""
        node = EntityNode(name=entity_name)

        # Process attributes
        attributes = entity_spec.get("attributes", {})
        if isinstance(attributes, dict):
            for attr_name, attr_spec in attributes.items():
                attr = AttributeNode(
                    name=attr_name,
                    type=attr_spec.get("type", "string"),
                    required=attr_spec.get("required", False),
                    is_primary_key=attr_spec.get("is_primary_key", attr_name in ["id"]),
                    is_unique=attr_spec.get("unique", False),
                    allowed_values=attr_spec.get("allowed_values"),
                    min_length=attr_spec.get("min_length"),
                    max_length=attr_spec.get("max_length"),
                    minimum=attr_spec.get("minimum"),
                    maximum=attr_spec.get("maximum"),
                    pattern=attr_spec.get("pattern")
                )
                node.add_attribute(attr)

        # Process constraints
        node.constraints = entity_spec.get("constraints", [])

        return node

    def _create_relationship_edges(self):
        """Create RelationshipEdge for each relationship"""
        relationships = self.spec.get("relationships", [])

        for rel in relationships:
            if not isinstance(rel, dict):
                continue

            cardinality = self._parse_cardinality(rel.get("type", "one-to-many"))

            edge = RelationshipEdge(
                source=rel.get("from", ""),
                target=rel.get("to", ""),
                type=rel.get("type", "one-to-many"),
                cardinality=cardinality,
                direction=RelationshipDirection(rel.get("direction", "forward")),
                foreign_key_field=rel.get("foreign_key"),
                required=rel.get("required", False),
                cascade_delete=rel.get("cascade_delete", False),
                cascade_update=rel.get("cascade_update", False),
                depends_on=rel.get("depends_on")
            )

            self.edges.append(edge)
            self.graph.add_edge(rel.get("from", ""), rel.get("to", ""), relationship=edge)

    def _parse_cardinality(self, rel_type: str) -> Tuple[str, str]:
        """Parse cardinality from relationship type"""
        if "one-to-many" in rel_type or "1:N" in rel_type:
            return ("1", "N")
        elif "many-to-many" in rel_type or "N:N" in rel_type:
            return ("N", "N")
        elif "many-to-one" in rel_type or "N:1" in rel_type:
            return ("N", "1")
        else:  # one-to-one
            return ("1", "1")

    def _analyze_cardinality(self):
        """Analyze cardinality constraints"""
        for edge in self.edges:
            # One-to-many: target must have foreign key to source
            if edge.cardinality == ("1", "N"):
                edge.add_constraint(
                    "foreign_key_presence",
                    f"Foreign key to {edge.source} required",
                    confidence=0.95
                )

            # Many-to-many: requires junction entity
            elif edge.cardinality == ("N", "N"):
                edge.add_constraint(
                    "junction_entity_required",
                    f"Many-to-many relationship requires junction entity",
                    confidence=0.90
                )

            # One-to-one: unique foreign key
            elif edge.cardinality == ("1", "1"):
                edge.add_constraint(
                    "unique_foreign_key",
                    f"Foreign key to {edge.source} must be unique",
                    confidence=0.92
                )

    def _detect_aggregate_roots(self):
        """Detect aggregate roots (high out-degree nodes)"""
        for node_name in self.graph.nodes():
            out_degree = self.graph.out_degree(node_name)
            in_degree = self.graph.in_degree(node_name)

            # Heuristic: out-degree > in-degree = likely aggregate root
            node = self.nodes.get(node_name)
            if node and out_degree > in_degree:
                node.is_aggregate_root = True
                self.metrics.aggregate_roots += 1

    def _analyze_workflows(self):
        """Extract workflow states and transitions"""
        for entity_name, entity in self.nodes.items():
            # Look for status/state fields
            status_field = entity.get_status_field()
            if status_field:
                # Extract allowed states
                attr = entity.attributes.get(status_field)
                if attr and attr.allowed_values:
                    entity.lifecycle_states = attr.allowed_values

    def _compute_transitive_relationships(self):
        """Find paths between entities (transitive relationships)"""
        # For all pairs of nodes, compute shortest path
        # This reveals implicit dependencies
        for source in self.graph.nodes():
            for target in self.graph.nodes():
                if source != target:
                    try:
                        path = nx.shortest_path(self.graph, source, target)
                        if len(path) > 2:  # Transitive (more than direct edge)
                            # Path: A -> B -> C means C implicitly depends on A
                            pass  # Will be used in constraint inference
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        pass

    def _calculate_metrics(self):
        """Calculate graph metrics"""
        self.metrics.total_entities = len(self.nodes)
        self.metrics.total_relationships = len(self.edges)

        total_attributes = sum(
            len(node.attributes) for node in self.nodes.values()
        )
        self.metrics.total_attributes = total_attributes

        if self.nodes:
            self.metrics.average_attributes_per_entity = (
                total_attributes / len(self.nodes)
            )

        many_to_many = sum(1 for edge in self.edges if edge.cardinality == ("N", "N"))
        self.metrics.many_to_many_relationships = many_to_many

        cascade_deletes = sum(1 for edge in self.edges if edge.cascade_delete)
        self.metrics.cascade_delete_relationships = cascade_deletes

        # Calculate max relationship depth
        if self.graph.number_of_nodes() > 0:
            try:
                self.metrics.max_relationship_depth = nx.diameter(self.graph.to_undirected())
            except (nx.NetworkXError, nx.NodeNotFound):
                self.metrics.max_relationship_depth = 0


class EntityRelationshipGraph:
    """Represents the complete entity relationship graph"""

    def __init__(
        self,
        nodes: Dict[str, EntityNode],
        edges: List[RelationshipEdge],
        graph: nx.DiGraph,
        metrics: GraphMetrics
    ):
        self.nodes = nodes
        self.edges = edges
        self.graph = graph
        self.metrics = metrics

    def get_entity(self, name: str) -> Optional[EntityNode]:
        """Get entity by name"""
        return self.nodes.get(name)

    def get_related_entities(self, entity_name: str) -> List[str]:
        """Get all entities directly related to this entity"""
        related = set()
        # Outgoing relationships
        for edge in self.edges:
            if edge.source == entity_name:
                related.add(edge.target)
            elif edge.target == entity_name:
                related.add(edge.source)
        return list(related)

    def get_outgoing_relationships(self, entity_name: str) -> List[RelationshipEdge]:
        """Get all outgoing relationships from entity"""
        return [e for e in self.edges if e.source == entity_name]

    def get_incoming_relationships(self, entity_name: str) -> List[RelationshipEdge]:
        """Get all incoming relationships to entity"""
        return [e for e in self.edges if e.target == entity_name]

    def is_aggregate_root(self, entity_name: str) -> bool:
        """Check if entity is an aggregate root"""
        node = self.nodes.get(entity_name)
        return node.is_aggregate_root if node else False

    def get_aggregate_members(self, aggregate_root: str) -> List[str]:
        """Get all entities that are part of an aggregate"""
        if not self.is_aggregate_root(aggregate_root):
            return []

        members = []
        outgoing = self.get_outgoing_relationships(aggregate_root)
        for rel in outgoing:
            members.append(rel.target)
        return members

    def has_lifecycle(self, entity_name: str) -> bool:
        """Check if entity has lifecycle states"""
        node = self.nodes.get(entity_name)
        return node.lifecycle_states is not None if node else False

    def get_lifecycle_states(self, entity_name: str) -> Optional[List[str]]:
        """Get lifecycle states for entity"""
        node = self.nodes.get(entity_name)
        return node.lifecycle_states if node else None
