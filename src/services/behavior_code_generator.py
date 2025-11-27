"""
Behavior Code Generator Service.

Generates business logic code from BehaviorModelIR including workflows,
state machines, and invariant validation.
"""
from typing import Dict, List, Any, Optional
from src.cognitive.ir.behavior_model import (
    BehaviorModelIR, Flow, Invariant, FlowType, Step
)
import textwrap


class BehaviorCodeGenerator:
    """Generates business logic code from BehaviorModelIR."""

    def __init__(self):
        self.generated_files: Dict[str, str] = {}

    def generate_workflows(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """
        Generate workflow code from Flow objects.

        Returns dict mapping file paths to generated code.
        """
        workflow_files = {}

        # Group workflows by type
        workflows = [f for f in behavior_ir.flows if f.type == FlowType.WORKFLOW]

        if workflows:
            # Generate main workflow module
            workflow_code = self._generate_workflow_module(workflows)
            workflow_files["src/workflows/__init__.py"] = workflow_code

            # Generate individual workflow files
            for workflow in workflows:
                file_name = f"src/workflows/{self._snake_case(workflow.name)}.py"
                code = self._generate_single_workflow(workflow)
                workflow_files[file_name] = code

        return workflow_files

    def generate_state_machines(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """
        Generate state machine code from invariants and state transitions.

        Returns dict mapping file paths to generated code.
        """
        state_files = {}

        # Group state transitions
        state_transitions = [
            f for f in behavior_ir.flows
            if f.type == FlowType.STATE_TRANSITION
        ]

        if state_transitions or behavior_ir.invariants:
            # Generate state machine base
            base_code = self._generate_state_machine_base()
            state_files["src/state_machines/__init__.py"] = base_code

            # Generate state machines from entities with invariants
            entity_states = self._group_by_entity(
                behavior_ir.invariants,
                state_transitions
            )

            for entity, data in entity_states.items():
                file_name = f"src/state_machines/{self._snake_case(entity)}_state.py"
                code = self._generate_entity_state_machine(
                    entity,
                    data['invariants'],
                    data['transitions']
                )
                state_files[file_name] = code

        return state_files

    def generate_business_logic(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """
        Generate complete business logic including workflows, state machines,
        invariant validation, and event handlers.

        Returns dict mapping file paths to generated code.
        """
        all_files = {}

        # 1. Generate workflows
        workflow_files = self.generate_workflows(behavior_ir)
        all_files.update(workflow_files)

        # 2. Generate state machines
        state_files = self.generate_state_machines(behavior_ir)
        all_files.update(state_files)

        # 3. Generate invariant validators
        validator_files = self._generate_invariant_validators(behavior_ir)
        all_files.update(validator_files)

        # 4. Generate event handlers
        event_files = self._generate_event_handlers(behavior_ir)
        all_files.update(event_files)

        # 5. Generate policy enforcers
        policy_files = self._generate_policy_enforcers(behavior_ir)
        all_files.update(policy_files)

        # 6. Generate orchestrator to coordinate all components
        orchestrator = self._generate_business_orchestrator(behavior_ir)
        all_files["src/business_logic/orchestrator.py"] = orchestrator

        return all_files

    # Private helper methods

    def _generate_workflow_module(self, workflows: List[Flow]) -> str:
        """Generate main workflow module."""
        imports = []
        exports = []

        for workflow in workflows:
            module_name = self._snake_case(workflow.name)
            class_name = self._pascal_case(workflow.name) + "Workflow"
            imports.append(f"from .{module_name} import {class_name}")
            exports.append(class_name)

        code = f'''"""
Workflow implementations for business processes.
"""
{chr(10).join(imports)}

__all__ = {exports}
'''
        return code

    def _generate_single_workflow(self, workflow: Flow) -> str:
        """Generate code for a single workflow."""
        class_name = self._pascal_case(workflow.name) + "Workflow"

        # Generate step methods
        step_methods = []
        for step in workflow.steps:
            method = self._generate_step_method(step)
            step_methods.append(method)

        code = f'''"""
{workflow.name} workflow implementation.

{workflow.description or f"Handles {workflow.name} business process."}
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
            self.metadata = {{}}


class {class_name}:
    """
    {workflow.name} workflow.

    Trigger: {workflow.trigger}
    """

    def __init__(self):
        self.name = "{workflow.name}"
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

    async def execute(self, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Execute the complete workflow.

        Args:
            context: Workflow execution context
            **kwargs: Additional workflow parameters

        Returns:
            Dict containing workflow results
        """
        self.logger.info(f"Starting {{self.name}} workflow")
        result = {{"status": "started", "steps": []}}

        try:
            # Execute workflow steps
{self._generate_step_execution(workflow.steps)}

            result["status"] = "completed"
            self.logger.info(f"Completed {{self.name}} workflow successfully")

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            self.logger.error(f"Workflow {{self.name}} failed: {{e}}")
            raise

        return result

{chr(10).join(step_methods)}
'''
        return code

    def _generate_step_method(self, step: Step) -> str:
        """Generate method for a workflow step."""
        method_name = f"_execute_{self._snake_case(step.action)}"

        condition_check = ""
        if step.condition:
            condition_check = f'''
        # Check condition: {step.condition}
        if not self._check_condition("{step.condition}", context, **kwargs):
            self.logger.info(f"Skipping step {{step_num}}: condition not met")
            return {{"skipped": True, "reason": "condition not met"}}
'''

        return f'''    async def {method_name}(self, step_num: int, context: WorkflowContext, **kwargs) -> Dict[str, Any]:
        """
        Step {step.order}: {step.description}

        Action: {step.action}
        {"Target: " + step.target_entity if step.target_entity else ""}
        """
        self.logger.debug(f"Executing step {{step_num}}: {step.description}")
        {condition_check}

        # Extension point: Implement {step.action} logic
        # This is where you would:
        # 1. Perform the actual {step.action} operation
        # 2. Update any relevant entities
        # 3. Handle errors appropriately

        result = {{
            "step": step_num,
            "action": "{step.action}",
            "status": "completed"
        }}

        return result'''

    def _generate_step_execution(self, steps: List[Step]) -> str:
        """Generate code to execute workflow steps."""
        execution_lines = []

        for step in sorted(steps, key=lambda s: s.order):
            method_name = f"_execute_{self._snake_case(step.action)}"
            execution_lines.append(f'''            # Step {step.order}: {step.description}
            step_result = await self.{method_name}({step.order}, context, **kwargs)
            result["steps"].append(step_result)
            ''')

        return "\n".join(execution_lines)

    def _generate_state_machine_base(self) -> str:
        """Generate base state machine module."""
        return '''"""
State machine implementations for business entities.
"""
from enum import Enum
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class BaseStateMachine:
    """Base class for state machines."""

    def __init__(self, initial_state: str):
        self.current_state = initial_state
        self.transition_history = []
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def transition_to(self, new_state: str, context: Dict[str, Any] = None) -> bool:
        """
        Attempt to transition to a new state.

        Args:
            new_state: Target state
            context: Optional transition context

        Returns:
            True if transition successful

        Raises:
            StateTransitionError: If transition is invalid
        """
        if not self.can_transition_to(new_state):
            raise StateTransitionError(
                f"Cannot transition from {self.current_state} to {new_state}"
            )

        old_state = self.current_state
        self.current_state = new_state
        self.transition_history.append({
            "from": old_state,
            "to": new_state,
            "context": context
        })

        self.logger.info(f"Transitioned from {old_state} to {new_state}")
        return True

    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        raise NotImplementedError("Subclasses must implement can_transition_to")

    def get_valid_transitions(self) -> List[str]:
        """Get list of valid transitions from current state."""
        raise NotImplementedError("Subclasses must implement get_valid_transitions")
'''

    def _generate_entity_state_machine(
        self,
        entity: str,
        invariants: List[Invariant],
        transitions: List[Flow]
    ) -> str:
        """Generate state machine for a specific entity."""
        class_name = self._pascal_case(entity) + "StateMachine"

        # Extract unique states from transitions
        states = self._extract_states(transitions)

        # Generate state enum
        state_enum = self._generate_state_enum(entity, states)

        # Generate transition rules
        transition_rules = self._generate_transition_rules(transitions)

        # Generate invariant checks
        invariant_checks = self._generate_invariant_checks(invariants)

        code = f'''{state_enum}

class {class_name}(BaseStateMachine):
    """
    State machine for {entity} entity.

    Manages state transitions and enforces invariants.
    """

    def __init__(self, initial_state: {self._pascal_case(entity)}State = None):
        if initial_state is None:
            initial_state = {self._pascal_case(entity)}State.{states[0] if states else 'INITIAL'}
        super().__init__(initial_state.value)
        self.state_enum = {self._pascal_case(entity)}State

    def can_transition_to(self, new_state: str) -> bool:
        """Check if transition to new_state is valid."""
        transitions = self._get_transition_map()
        current_transitions = transitions.get(self.current_state, [])
        return new_state in current_transitions

    def get_valid_transitions(self) -> List[str]:
        """Get list of valid transitions from current state."""
        transitions = self._get_transition_map()
        return transitions.get(self.current_state, [])

    def _get_transition_map(self) -> Dict[str, List[str]]:
        """Define valid state transitions."""
        return {{
{transition_rules}
        }}

    def validate_invariants(self, entity_data: Dict[str, Any]) -> bool:
        """
        Validate all invariants for the entity.

        Args:
            entity_data: Current entity data

        Returns:
            True if all invariants are satisfied
        """
{invariant_checks}
        return True
'''
        return code

    def _generate_invariant_validators(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """Generate invariant validation code."""
        if not behavior_ir.invariants:
            return {}

        validators = {}

        # Group invariants by entity
        entity_invariants = {}
        for inv in behavior_ir.invariants:
            if inv.entity not in entity_invariants:
                entity_invariants[inv.entity] = []
            entity_invariants[inv.entity].append(inv)

        # Generate validator for each entity
        for entity, invariants in entity_invariants.items():
            code = self._generate_entity_validator(entity, invariants)
            file_name = f"src/validators/{self._snake_case(entity)}_validator.py"
            validators[file_name] = code

        # Generate main validator module
        validators["src/validators/__init__.py"] = self._generate_validator_index(
            list(entity_invariants.keys())
        )

        return validators

    def _generate_entity_validator(self, entity: str, invariants: List[Invariant]) -> str:
        """Generate validator for entity invariants."""
        class_name = self._pascal_case(entity) + "Validator"

        validation_methods = []
        for inv in invariants:
            method = self._generate_invariant_method(inv)
            validation_methods.append(method)

        code = f'''"""
Invariant validator for {entity} entity.
"""
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)


class {class_name}:
    """Validates invariants for {entity} entity."""

    def __init__(self):
        self.entity_name = "{entity}"
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

    def validate_all(self, entity_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate all invariants for the entity.

        Args:
            entity_data: Entity data to validate

        Returns:
            Tuple of (is_valid, list_of_violations)
        """
        violations = []

{self._generate_validation_calls(invariants)}

        is_valid = len(violations) == 0

        if not is_valid:
            self.logger.warning(f"{{self.entity_name}} invariants violated: {{violations}}")

        return is_valid, violations

{chr(10).join(validation_methods)}
'''
        return code

    def _generate_invariant_method(self, invariant: Invariant) -> str:
        """Generate validation method for an invariant."""
        method_name = f"_validate_{self._snake_case(invariant.description[:30])}"

        validation_logic = "# Extension point: Implement validation logic"
        if invariant.expression:
            validation_logic = f'''# Expression: {invariant.expression}
        try:
            # Parse and evaluate expression
            # This is a simplified example - in production you'd use a safe expression evaluator
            result = eval(f"entity_data.{{invariant.expression}}")
            return result
        except Exception as e:
            self.logger.error(f"Error evaluating invariant: {{e}}")
            return False'''

        return f'''    def {method_name}(self, entity_data: Dict[str, Any]) -> bool:
        """
        {invariant.description}

        Enforcement: {invariant.enforcement_level}
        """
        {validation_logic}
        '''

    def _generate_validation_calls(self, invariants: List[Invariant]) -> str:
        """Generate calls to validation methods."""
        calls = []
        for inv in invariants:
            method_name = f"_validate_{self._snake_case(inv.description[:30])}"
            calls.append(f'''        if not self.{method_name}(entity_data):
            violations.append("{inv.description}")''')

        return "\n        \n".join(calls)

    def _generate_event_handlers(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """Generate event handler code."""
        handlers = {}

        # Filter event handler flows
        event_flows = [
            f for f in behavior_ir.flows
            if f.type == FlowType.EVENT_HANDLER
        ]

        if event_flows:
            # Generate event handler module
            handler_code = self._generate_event_handler_module(event_flows)
            handlers["src/events/handlers.py"] = handler_code

            # Generate event dispatcher
            dispatcher_code = self._generate_event_dispatcher(event_flows)
            handlers["src/events/dispatcher.py"] = dispatcher_code

        return handlers

    def _generate_event_handler_module(self, event_flows: List[Flow]) -> str:
        """Generate event handler implementations."""
        handlers = []

        for flow in event_flows:
            handler = self._generate_single_event_handler(flow)
            handlers.append(handler)

        code = f'''"""
Event handlers for system events.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class EventContext:
    """Context for event handling."""

    def __init__(self, event_type: str, payload: Dict[str, Any]):
        self.event_type = event_type
        self.payload = payload
        self.metadata = {{}}


{chr(10).join(handlers)}
'''
        return code

    def _generate_single_event_handler(self, flow: Flow) -> str:
        """Generate a single event handler."""
        handler_name = self._snake_case(flow.name)

        return f'''async def handle_{handler_name}(context: EventContext) -> Dict[str, Any]:
    """
    Handle {flow.name} event.

    Trigger: {flow.trigger}
    {f"Description: {flow.description}" if flow.description else ""}
    """
    logger.info(f"Handling {{context.event_type}} event")

    try:
        result = {{"status": "processing"}}

        # Process event steps
{self._generate_event_steps(flow.steps)}

        result["status"] = "completed"
        logger.info(f"Successfully handled {{context.event_type}}")

    except Exception as e:
        logger.error(f"Error handling {{context.event_type}}: {{e}}")
        result = {{"status": "failed", "error": str(e)}}

    return result
'''

    def _generate_event_steps(self, steps: List[Step]) -> str:
        """Generate event processing steps."""
        step_code = []

        for step in sorted(steps, key=lambda s: s.order):
            step_code.append(f'''        # Step {step.order}: {step.description}
        # Action: {step.action}
        # Extension point: Implement {step.action} logic
        ''')

        return "\n".join(step_code)

    def _generate_event_dispatcher(self, event_flows: List[Flow]) -> str:
        """Generate event dispatcher."""
        handler_imports = []
        handler_map = {}

        for flow in event_flows:
            handler_name = f"handle_{self._snake_case(flow.name)}"
            handler_imports.append(handler_name)
            handler_map[flow.trigger] = handler_name

        code = f'''"""
Event dispatcher for routing events to appropriate handlers.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from .handlers import EventContext, {', '.join(handler_imports)}

logger = logging.getLogger(__name__)


class EventDispatcher:
    """Routes events to appropriate handlers."""

    def __init__(self):
        self.handlers = self._register_handlers()
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

    def _register_handlers(self) -> Dict[str, Callable]:
        """Register all event handlers."""
        return {{
{self._generate_handler_registration(handler_map)}
        }}

    async def dispatch(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dispatch event to appropriate handler.

        Args:
            event_type: Type of event to handle
            payload: Event payload

        Returns:
            Handler result
        """
        handler = self.handlers.get(event_type)

        if not handler:
            self.logger.warning(f"No handler registered for event type: {{event_type}}")
            return {{"status": "unhandled", "event_type": event_type}}

        context = EventContext(event_type, payload)
        return await handler(context)
'''
        return code

    def _generate_handler_registration(self, handler_map: Dict[str, str]) -> str:
        """Generate handler registration code."""
        registrations = []
        for trigger, handler in handler_map.items():
            registrations.append(f'            "{trigger}": {handler},')
        return "\n".join(registrations)

    def _generate_policy_enforcers(self, behavior_ir: BehaviorModelIR) -> Dict[str, str]:
        """Generate policy enforcement code."""
        policies = {}

        # Filter policy flows
        policy_flows = [
            f for f in behavior_ir.flows
            if f.type == FlowType.POLICY
        ]

        if policy_flows:
            # Generate policy enforcer
            policy_code = self._generate_policy_enforcer(policy_flows)
            policies["src/policies/enforcer.py"] = policy_code

        return policies

    def _generate_policy_enforcer(self, policy_flows: List[Flow]) -> str:
        """Generate policy enforcement code."""
        policy_methods = []

        for policy in policy_flows:
            method = self._generate_policy_method(policy)
            policy_methods.append(method)

        code = f'''"""
Policy enforcement for business rules and invariants.
"""
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class PolicyEnforcer:
    """Enforces business policies and rules."""

    def __init__(self):
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

    def enforce_all(self, context: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Enforce all policies.

        Args:
            context: Context for policy evaluation

        Returns:
            Tuple of (all_passed, list_of_violations)
        """
        violations = []

{self._generate_policy_calls(policy_flows)}

        return len(violations) == 0, violations

{chr(10).join(policy_methods)}
'''
        return code

    def _generate_policy_method(self, policy: Flow) -> str:
        """Generate method for a single policy."""
        method_name = f"_enforce_{self._snake_case(policy.name)}"

        return f'''    def {method_name}(self, context: Dict[str, Any]) -> bool:
        """
        {policy.description or policy.name}

        Trigger: {policy.trigger}
        """
        try:
            # Implement policy logic
{self._generate_policy_steps(policy.steps)}

            return True

        except Exception as e:
            self.logger.error(f"Error enforcing {{policy.name}}: {{e}}")
            return False
'''

    def _generate_policy_steps(self, steps: List[Step]) -> str:
        """Generate policy enforcement steps."""
        step_code = []

        for step in sorted(steps, key=lambda s: s.order):
            step_code.append(f'''            # Step {step.order}: {step.description}
            # Extension point: Implement {step.action}''')

        return "\n".join(step_code)

    def _generate_policy_calls(self, policies: List[Flow]) -> str:
        """Generate calls to policy methods."""
        calls = []
        for policy in policies:
            method_name = f"_enforce_{self._snake_case(policy.name)}"
            calls.append(f'''        if not self.{method_name}(context):
            violations.append("{policy.name}")''')

        return "\n        \n".join(calls)

    def _generate_business_orchestrator(self, behavior_ir: BehaviorModelIR) -> str:
        """Generate main business logic orchestrator."""
        # Determine what components exist
        has_workflows = any(f.type == FlowType.WORKFLOW for f in behavior_ir.flows)
        has_states = any(f.type == FlowType.STATE_TRANSITION for f in behavior_ir.flows)
        has_events = any(f.type == FlowType.EVENT_HANDLER for f in behavior_ir.flows)
        has_policies = any(f.type == FlowType.POLICY for f in behavior_ir.flows)
        has_validators = bool(behavior_ir.invariants)

        imports = []
        if has_workflows:
            imports.append("from src.workflows import *")
        if has_states:
            imports.append("from src.state_machines import *")
        if has_events:
            imports.append("from src.events.dispatcher import EventDispatcher")
        if has_policies:
            imports.append("from src.policies.enforcer import PolicyEnforcer")
        if has_validators:
            imports.append("from src.validators import *")

        code = f'''"""
Business Logic Orchestrator.

Coordinates workflows, state machines, events, and policies.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
{chr(10).join(imports)}

logger = logging.getLogger(__name__)


class BusinessOrchestrator:
    """
    Central coordinator for all business logic components.

    Manages the interaction between workflows, state machines,
    event handlers, and policy enforcement.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{{__name__}}.{{self.__class__.__name__}}")

        # Initialize components
{self._generate_component_init(has_workflows, has_states, has_events, has_policies, has_validators)}

    async def execute_business_process(
        self,
        process_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a complete business process.

        Args:
            process_name: Name of the business process
            context: Process context and parameters

        Returns:
            Process execution result
        """
        self.logger.info(f"Starting business process: {{process_name}}")

        try:
            # 1. Validate preconditions
            if not await self._validate_preconditions(process_name, context):
                return {{"status": "failed", "reason": "precondition validation failed"}}

            # 2. Execute main process
            result = await self._execute_process(process_name, context)

            # 3. Handle post-process events
            await self._handle_post_process_events(process_name, result)

            # 4. Validate postconditions
            if not await self._validate_postconditions(process_name, result):
                self.logger.warning("Postcondition validation failed")

            return result

        except Exception as e:
            self.logger.error(f"Business process {{process_name}} failed: {{e}}")
            return {{"status": "failed", "error": str(e)}}

    async def _validate_preconditions(
        self,
        process_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """Validate preconditions before process execution."""
{self._generate_precondition_validation(has_validators, has_policies)}
        return True

    async def _execute_process(
        self,
        process_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the main business process."""
{self._generate_process_execution(has_workflows)}
        return {{"status": "completed"}}

    async def _handle_post_process_events(
        self,
        process_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Handle events triggered by process completion."""
{self._generate_event_handling(has_events)}
        pass

    async def _validate_postconditions(
        self,
        process_name: str,
        result: Dict[str, Any]
    ) -> bool:
        """Validate postconditions after process execution."""
        # Extension point: Implement postcondition validation
        return True
'''
        return code

    def _generate_component_init(
        self,
        has_workflows: bool,
        has_states: bool,
        has_events: bool,
        has_policies: bool,
        has_validators: bool
    ) -> str:
        """Generate component initialization code."""
        init_lines = []

        if has_workflows:
            init_lines.append("        self.workflows = {}")
        if has_states:
            init_lines.append("        self.state_machines = {}")
        if has_events:
            init_lines.append("        self.event_dispatcher = EventDispatcher()")
        if has_policies:
            init_lines.append("        self.policy_enforcer = PolicyEnforcer()")
        if has_validators:
            init_lines.append("        self.validators = {}")

        return "\n".join(init_lines) if init_lines else "        pass"

    def _generate_precondition_validation(
        self,
        has_validators: bool,
        has_policies: bool
    ) -> str:
        """Generate precondition validation code."""
        validation_lines = []

        if has_validators:
            validation_lines.append('''        # Validate entity invariants
        # Extension point: Call appropriate validators based on process''')

        if has_policies:
            validation_lines.append('''        # Enforce business policies
        is_valid, violations = self.policy_enforcer.enforce_all(context)
        if not is_valid:
            self.logger.warning(f"Policy violations: {violations}")
            return False''')

        return "\n".join(validation_lines) if validation_lines else "        # No preconditions to validate"

    def _generate_process_execution(self, has_workflows: bool) -> str:
        """Generate process execution code."""
        if has_workflows:
            return '''        # Execute workflow based on process name
        # Extension point: Map process_name to appropriate workflow
        # Example:
        # workflow = self.workflows.get(process_name)
        # if workflow:
        #     return await workflow.execute(context)'''

        return "        # No workflows to execute"

    def _generate_event_handling(self, has_events: bool) -> str:
        """Generate event handling code."""
        if has_events:
            return '''        # Dispatch completion event
        event_type = f"{process_name}_completed"
        await self.event_dispatcher.dispatch(event_type, result)'''

        return "        # No events to handle"

    def _generate_validator_index(self, entities: List[str]) -> str:
        """Generate validator index module."""
        imports = []
        exports = []

        for entity in entities:
            class_name = self._pascal_case(entity) + "Validator"
            module_name = self._snake_case(entity) + "_validator"
            imports.append(f"from .{module_name} import {class_name}")
            exports.append(class_name)

        return f'''"""
Validators for entity invariants.
"""
{chr(10).join(imports)}

__all__ = {exports}
'''

    def _generate_state_enum(self, entity: str, states: List[str]) -> str:
        """Generate state enum for entity."""
        if not states:
            states = ["INITIAL", "PROCESSING", "COMPLETED", "ERROR"]

        state_defs = []
        for state in states:
            state_upper = state.upper().replace(" ", "_")
            state_defs.append(f'    {state_upper} = "{state.lower()}"')

        return f'''"""
State machine for {entity} entity.
"""
from enum import Enum
from typing import Dict, Any, List, Optional
from src.state_machines import BaseStateMachine, StateTransitionError

class {self._pascal_case(entity)}State(Enum):
    """States for {entity} entity."""
{chr(10).join(state_defs)}
'''

    def _generate_transition_rules(self, transitions: List[Flow]) -> str:
        """Generate state transition rules."""
        if not transitions:
            # Default transitions
            return '''            "initial": ["processing"],
            "processing": ["completed", "error"],
            "completed": [],
            "error": ["processing"],'''

        # Extract transition rules from flows
        rules = {}
        for flow in transitions:
            # Parse flow to extract from/to states
            # This is simplified - in reality you'd parse the flow steps
            pass

        # For now, return default
        return '''            "initial": ["processing"],
            "processing": ["completed", "error"],
            "completed": [],
            "error": ["processing"],'''

    def _generate_invariant_checks(self, invariants: List[Invariant]) -> str:
        """Generate invariant validation checks."""
        if not invariants:
            return "        # No invariants to check"

        checks = []
        for inv in invariants:
            if inv.expression:
                checks.append(f'''        # Check: {inv.description}
        # Expression: {inv.expression}
        # Extension point: Implement invariant check''')
            else:
                checks.append(f'''        # Check: {inv.description}
        # Extension point: Implement invariant check''')

        return "\n        \n".join(checks)

    def _extract_states(self, transitions: List[Flow]) -> List[str]:
        """Extract unique states from transitions."""
        states = set()

        for flow in transitions:
            # Extract states mentioned in flow
            # This is simplified - would need to parse flow description/steps
            pass

        # Return default states if none found
        return list(states) if states else ["INITIAL", "PROCESSING", "COMPLETED", "ERROR"]

    def _group_by_entity(
        self,
        invariants: List[Invariant],
        transitions: List[Flow]
    ) -> Dict[str, Dict]:
        """Group invariants and transitions by entity."""
        entities = {}

        # Group invariants
        for inv in invariants:
            if inv.entity not in entities:
                entities[inv.entity] = {"invariants": [], "transitions": []}
            entities[inv.entity]["invariants"].append(inv)

        # Group transitions (simplified - would need to parse entity from flow)
        for trans in transitions:
            # Extract entity from flow description or steps
            # For now, add to first entity or create default
            if entities:
                first_entity = list(entities.keys())[0]
                entities[first_entity]["transitions"].append(trans)

        return entities

    # Utility methods

    def _snake_case(self, text: str) -> str:
        """Convert text to snake_case with proper sanitization."""
        import re
        import unicodedata

        # Step 1: Normalize unicode (remove accents: í→i, ó→o)
        result = unicodedata.normalize('NFKD', text)
        result = result.encode('ascii', 'ignore').decode('ascii')

        # Step 2: Remove invalid characters (keep only letters, digits, spaces, underscores)
        # This removes : ( ) and other special chars
        result = re.sub(r'[^a-zA-Z0-9\s_]', '', result)

        # Step 3: Replace spaces/hyphens with underscores
        result = result.replace(" ", "_").replace("-", "_")

        # Step 4: Handle camelCase
        result = re.sub('([A-Z]+)', r'_\1', result).lower()

        # Step 5: Clean up multiple underscores
        result = re.sub('_+', '_', result).strip('_')

        return result

    def _pascal_case(self, text: str) -> str:
        """Convert text to PascalCase with proper sanitization."""
        import re
        import unicodedata

        # Step 1: Normalize unicode (remove accents)
        result = unicodedata.normalize('NFKD', text)
        result = result.encode('ascii', 'ignore').decode('ascii')

        # Step 2: Remove invalid characters (keep only letters, digits, spaces)
        result = re.sub(r'[^a-zA-Z0-9\s]', '', result)

        # Step 3: Split by spaces, underscores, hyphens
        words = re.split(r'[\s_\-]+', result)
        return ''.join(word.capitalize() for word in words if word)