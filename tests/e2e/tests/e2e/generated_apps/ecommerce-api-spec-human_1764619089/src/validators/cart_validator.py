"""
Invariant validator for Cart entity.
"""
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CartValidator:
    """Validates invariants for Cart entity."""

    def __init__(self):
        self.entity_name = "Cart"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def validate_all(self, entity_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all invariants for the entity.

        Args:
            entity_data: Entity data to validate

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []

        if not self._validate_cart_requires_customer(entity_data):
            violations.append("Cart requires Customer")

        is_valid = len(violations) == 0

        if not is_valid:
            self.logger.warning(f"{self.entity_name} invariants violated: {violations}")

        return is_valid, violations

    def _validate_cart_requires_customer(self, entity_data: Dict[str, Any]) -> bool:
        """
        Cart requires Customer

        Enforcement: strict
        """
        # Extension point: Implement validation logic