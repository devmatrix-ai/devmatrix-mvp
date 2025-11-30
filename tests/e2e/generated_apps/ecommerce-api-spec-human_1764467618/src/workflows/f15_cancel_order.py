"""
F15: Cancel Order workflow implementation.

Cancel an order and return stock. Current status must be PENDING_PAYMENT. Change to CANCELLED and add back the quantity to products
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WorkflowContext:
    """Context for workflow execution."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class F15CancelOrderWorkflow:
    """
    F15: Cancel Order workflow.

    Trigger: Customer cancels order
    """

    def __init__(self):
        self.name = "F15: Cancel Order"
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Execute the complete workflow.

        Args:
            context: Workflow execution context
            **kwargs: Additional workflow parameters

        Returns:
            Dict containing workflow results
        """
        self.logger.info(f"Starting {self.name} workflow")
        result = {"status": "started", "steps": []}

        try:
            # Execute workflow steps
            # Step 1: Validate order exists
            step_result = await self._execute_validate(1, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 2: Validate order status is PENDING_PAYMENT
            step_result = await self._execute_validate(2, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 3: Update order_status to CANCELLED
            step_result = await self._execute_update(3, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 4: Return stock to products for all order items
            step_result = await self._execute_update(4, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 5: Return updated order
            step_result = await self._execute_validate(5, context, **kwargs)
            result["steps"].append(step_result)
            

            result["status"] = "completed"
            self.logger.info(f"Completed {self.name} workflow successfully")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.logger.error(f"Workflow {self.name} failed: {e}")
            raise

        return result

    async def _execute_validate(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 1: Validate order exists

        Action: validate
        Target: Order
        """
        self.logger.debug(f"Executing step {step_num}: Validate order exists")
        
        # Check condition: Order with given ID exists
        if not self._check_condition("Order with given ID exists", context, **kwargs):
            self.logger.info(f"Skipping step {step_num}: condition not met")
            return {"skipped": True, "reason": "condition not met"}


        # Extension point: Implement validate logic
        # This is where you would:
        # 1. Perform the actual validate operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "validate",
            "status": "completed"
        }

        return result
    async def _execute_validate(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 2: Validate order status is PENDING_PAYMENT

        Action: validate
        Target: Order
        """
        self.logger.debug(f"Executing step {step_num}: Validate order status is PENDING_PAYMENT")
        
        # Check condition: order_status = PENDING_PAYMENT
        if not self._check_condition("order_status = PENDING_PAYMENT", context, **kwargs):
            self.logger.info(f"Skipping step {step_num}: condition not met")
            return {"skipped": True, "reason": "condition not met"}


        # Extension point: Implement validate logic
        # This is where you would:
        # 1. Perform the actual validate operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "validate",
            "status": "completed"
        }

        return result
    async def _execute_update(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 3: Update order_status to CANCELLED

        Action: update
        Target: Order
        """
        self.logger.debug(f"Executing step {step_num}: Update order_status to CANCELLED")
        

        # Extension point: Implement update logic
        # This is where you would:
        # 1. Perform the actual update operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "update",
            "status": "completed"
        }

        return result
    async def _execute_update(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 4: Return stock to products for all order items

        Action: update
        Target: Product
        """
        self.logger.debug(f"Executing step {step_num}: Return stock to products for all order items")
        

        # Extension point: Implement update logic
        # This is where you would:
        # 1. Perform the actual update operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "update",
            "status": "completed"
        }

        return result
    async def _execute_validate(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 5: Return updated order

        Action: validate
        Target: Order
        """
        self.logger.debug(f"Executing step {step_num}: Return updated order")
        

        # Extension point: Implement validate logic
        # This is where you would:
        # 1. Perform the actual validate operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "validate",
            "status": "completed"
        }

        return result