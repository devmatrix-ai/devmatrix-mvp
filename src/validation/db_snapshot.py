"""
DB Snapshot Diff Engine for IR-Agnostic Runtime Repair.

Phase 2.2: Captures and compares database state before/after flow execution.

Used to verify postconditions from BehaviorModelIR are satisfied.
"""
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import structlog
import httpx
from uuid import UUID

logger = structlog.get_logger(__name__)


class ChangeType(str, Enum):
    """Type of database change detected."""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"


@dataclass
class EntityChange:
    """A single entity change in the database."""
    entity_type: str
    entity_id: str
    change_type: ChangeType
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None


@dataclass
class SnapshotDiff:
    """Diff between two database snapshots."""
    changes: List[EntityChange]
    created_count: int
    updated_count: int
    deleted_count: int
    
    def has_change_for_entity(self, entity_type: str) -> bool:
        """Check if any change affects given entity type."""
        return any(c.entity_type.lower() == entity_type.lower() for c in self.changes)
    
    def get_changes_for_entity(self, entity_type: str) -> List[EntityChange]:
        """Get all changes for a specific entity type."""
        return [c for c in self.changes if c.entity_type.lower() == entity_type.lower()]


class DBSnapshotEngine:
    """
    Engine for capturing and comparing database snapshots.
    
    Domain-agnostic: Works with any entity type from IR.
    Uses HTTP API to query entities (no direct DB access).
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=10.0)
    
    async def take_snapshot(
        self,
        entity_types: List[str],
        entity_ids: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Capture current state of specified entities.
        
        Args:
            entity_types: List of entity type names (e.g., ["Product", "Cart"])
            entity_ids: Optional specific IDs to snapshot per entity type
        
        Returns:
            Dict mapping "EntityType:id" → entity data
        """
        snapshot = {}
        
        for entity_type in entity_types:
            endpoint = f"/{entity_type.lower()}s"  # Pluralize
            
            try:
                if entity_ids and entity_type in entity_ids:
                    # Fetch specific entities
                    for eid in entity_ids[entity_type]:
                        response = self._client.get(f"{self.base_url}{endpoint}/{eid}")
                        if response.status_code == 200:
                            key = f"{entity_type}:{eid}"
                            snapshot[key] = response.json()
                else:
                    # Fetch all entities (for small datasets)
                    response = self._client.get(f"{self.base_url}{endpoint}")
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("items", data) if isinstance(data, dict) else data
                        for item in items:
                            eid = item.get("id", str(item.get("uuid", "")))
                            key = f"{entity_type}:{eid}"
                            snapshot[key] = item
            except Exception as e:
                logger.warning(f"Failed to snapshot {entity_type}: {e}")
        
        return snapshot
    
    def diff(
        self,
        before: Dict[str, Dict[str, Any]],
        after: Dict[str, Dict[str, Any]]
    ) -> SnapshotDiff:
        """
        Compare two snapshots and return differences.
        """
        changes = []
        
        before_keys = set(before.keys())
        after_keys = set(after.keys())
        
        # Created entities (in after but not in before)
        for key in after_keys - before_keys:
            entity_type, entity_id = key.split(":", 1)
            changes.append(EntityChange(
                entity_type=entity_type,
                entity_id=entity_id,
                change_type=ChangeType.CREATED,
                new_values=after[key]
            ))
        
        # Deleted entities (in before but not in after)
        for key in before_keys - after_keys:
            entity_type, entity_id = key.split(":", 1)
            changes.append(EntityChange(
                entity_type=entity_type,
                entity_id=entity_id,
                change_type=ChangeType.DELETED,
                old_values=before[key]
            ))
        
        # Updated entities (in both but different)
        for key in before_keys & after_keys:
            if before[key] != after[key]:
                entity_type, entity_id = key.split(":", 1)
                changed_fields = self._get_changed_fields(before[key], after[key])
                changes.append(EntityChange(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    change_type=ChangeType.UPDATED,
                    old_values=before[key],
                    new_values=after[key],
                    changed_fields=changed_fields
                ))
        
        return SnapshotDiff(
            changes=changes,
            created_count=len([c for c in changes if c.change_type == ChangeType.CREATED]),
            updated_count=len([c for c in changes if c.change_type == ChangeType.UPDATED]),
            deleted_count=len([c for c in changes if c.change_type == ChangeType.DELETED])
        )
    
    def _get_changed_fields(
        self,
        old: Dict[str, Any],
        new: Dict[str, Any]
    ) -> List[str]:
        """Get list of fields that changed between old and new."""
        changed = []
        all_keys = set(old.keys()) | set(new.keys())
        
        for key in all_keys:
            if old.get(key) != new.get(key):
                changed.append(key)
        
        return changed
    
    def close(self):
        """Close HTTP client."""
        self._client.close()

