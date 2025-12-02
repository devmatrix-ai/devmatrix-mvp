"""
F1: Create Product workflow implementation.

The system allows creating a new product with name, description, price, stock and status
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


class F1CreateProductWorkflow:
    """
    F1: Create Product workflow.

    Trigger: User submits product creation request
    """

    def __init__(self):
        self.name = "F1: Create Product"
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
            # Step 1: Validate product data (name required, price > 0, stock >= 0)
            step_result = await self._execute_validate(1, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 2: Create new product with provided data
            step_result = await self._execute_create(2, context, **kwargs)
            result["steps"].append(step_result)
            
            # Step 3: Return created product with generated ID
            step_result = await self._execute_validate(3, context, **kwargs)
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
        Step 1: Validate product data (name required, price > 0, stock >= 0)

        Action: validate
        Target: Product
        """
        self.logger.debug(f"Executing step {step_num}: Validate product data (name required, price > 0, stock >= 0)")
        
        # Check condition: name is not empty, price > 0, stock >= 0
        if not self._check_condition("name is not empty, price > 0, stock >= 0", context, **kwargs):
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
    async def _execute_create(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 2: Create new product with provided data

        Action: create
        Target: Product
        """
        self.logger.debug(f"Executing step {step_num}: Create new product with provided data")
        

        # Extension point: Implement create logic
        # This is where you would:
        # 1. Perform the actual create operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {
            "step": step_num,
            "action": "create",
            "status": "completed"
        }

        return result
    async def _execute_validate(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step 3: Return created product with generated ID

        Action: validate
        Target: Product
        """
        self.logger.debug(f"Executing step {step_num}: Return created product with generated ID")
        

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