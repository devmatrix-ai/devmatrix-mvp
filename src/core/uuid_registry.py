"""
Seed UUID Registry

Centralized, deterministic UUID generation for seed data and smoke tests.
Ensures consistency across code generation and smoke test phases.

Bug Fix: Eliminates UUID mismatch between code_generation_service.py 
and smoke_test_orchestrator.py.
"""
from typing import Dict, List, Tuple, Optional
import structlog

logger = structlog.get_logger(__name__)


class SeedUUIDRegistry:
    """
    Generates predictable UUIDs for seed data and smoke tests.
    
    UUID Schema:
    - Primary UUIDs: 00000000-0000-4000-8000-00000000000X (X = 1-9 for entities 1-9)
    - Delete UUIDs:  00000000-0000-4000-8000-0000000000XX (XX = 11-19 for delete variants)
    - Join Tables:   00000000-0000-4000-8000-0000000000XX (XX = 20+ for join table items)
    
    Example:
        registry = SeedUUIDRegistry.from_entity_names(["Product", "Customer", "Cart"])
        registry.get_uuid("product")  # -> "00000000-0000-4000-8000-000000000001"
        registry.get_uuid("product", "delete")  # -> "00000000-0000-4000-8000-000000000011"
    """
    
    UUID_BASE = "00000000-0000-4000-8000-00000000000"      # 11 trailing zeros + 1 digit
    UUID_BASE_DELETE = "00000000-0000-4000-8000-0000000000"  # 10 trailing zeros + 2 digits
    NOT_FOUND_UUID = "99999999-9999-4000-8000-999999999999"
    
    def __init__(self, entity_uuids: Dict[str, Tuple[str, str]]):
        """
        Initialize with pre-computed entity UUIDs.
        
        Args:
            entity_uuids: Dict mapping entity_name (lowercase) -> (primary_uuid, delete_uuid)
        """
        self._entity_uuids = entity_uuids
        self._join_table_counter = 20  # Start at 20 for join table items
        
    @classmethod
    def from_entity_names(cls, entity_names: List[str]) -> "SeedUUIDRegistry":
        """
        Create registry from list of entity names.
        
        Args:
            entity_names: List of entity names (e.g., ["Product", "Customer"])
            
        Returns:
            Initialized SeedUUIDRegistry
        """
        entity_uuids = {}
        
        for idx, name in enumerate(entity_names, start=1):
            entity_key = name.lower()
            primary_uuid = f"{cls.UUID_BASE}{idx}"
            delete_uuid = f"{cls.UUID_BASE_DELETE}{idx + 10}"
            entity_uuids[entity_key] = (primary_uuid, delete_uuid)
            
        logger.debug(f"SeedUUIDRegistry initialized with {len(entity_uuids)} entities")
        return cls(entity_uuids)
    
    @classmethod
    def from_ir(cls, ir) -> "SeedUUIDRegistry":
        """
        Create registry from ApplicationIR.
        
        Args:
            ir: ApplicationIR instance
            
        Returns:
            Initialized SeedUUIDRegistry
        """
        entities = ir.get_entities() if hasattr(ir, 'get_entities') else []
        entity_names = [e.name for e in entities]
        return cls.from_entity_names(entity_names)
    
    def get_uuid(self, entity: str, variant: str = "primary") -> str:
        """
        Get UUID for an entity.
        
        Args:
            entity: Entity name (case-insensitive)
            variant: "primary" for normal tests, "delete" for DELETE tests
            
        Returns:
            UUID string
            
        Raises:
            ValueError: If entity not found in registry
        """
        entity_key = entity.lower()
        uuid_tuple = self._entity_uuids.get(entity_key)
        
        if not uuid_tuple:
            available = list(self._entity_uuids.keys())
            raise ValueError(f"Entity '{entity}' not in registry. Available: {available}")
        
        return uuid_tuple[0] if variant == "primary" else uuid_tuple[1]
    
    def get_fk_uuid(self, target_entity: str) -> str:
        """
        Get UUID for FK reference to another entity.
        
        Args:
            target_entity: Target entity name (e.g., "customer" from "customer_id")
            
        Returns:
            Primary UUID of target entity
        """
        return self.get_uuid(target_entity, "primary")
    
    def get_next_item_uuid(self) -> str:
        """
        Get next UUID for join table items (CartItem, OrderItem, etc.).
        
        Returns:
            UUID string starting at 20 and incrementing
        """
        uuid = f"{self.UUID_BASE_DELETE}{self._join_table_counter}"
        self._join_table_counter += 1
        return uuid
    
    def to_dict(self) -> Dict[str, Tuple[str, str]]:
        """Export entity -> (primary, delete) mapping."""
        return self._entity_uuids.copy()
    
    def to_prompt_json(self) -> str:
        """
        Export as JSON for LLM prompt injection.
        
        Returns:
            JSON string with UUID assignments
        """
        import json
        prompt_data = {
            entity: {"primary": uuids[0], "delete": uuids[1]}
            for entity, uuids in self._entity_uuids.items()
        }
        prompt_data["_not_found"] = self.NOT_FOUND_UUID
        return json.dumps(prompt_data, indent=2)
    
    @property
    def not_found_uuid(self) -> str:
        """UUID to use for not-found test scenarios."""
        return self.NOT_FOUND_UUID
    
    def __contains__(self, entity: str) -> bool:
        return entity.lower() in self._entity_uuids
    
    def __repr__(self) -> str:
        return f"SeedUUIDRegistry({list(self._entity_uuids.keys())})"

