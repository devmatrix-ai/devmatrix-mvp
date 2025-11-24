"""
Tests for Behavior Code Generation from BehaviorModelIR.

Tests workflow generation, state machine creation, and invariant validation.
"""
import pytest
from src.services.behavior_code_generator import BehaviorCodeGenerator
from src.cognitive.ir.behavior_model import (
    BehaviorModelIR,
    Flow,
    FlowType,
    Step,
    Invariant
)


class TestBehaviorCodeGenerator:
    """Test behavior code generation functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.generator = BehaviorCodeGenerator()

    def test_workflow_generation(self):
        """Test that workflows are generated from Flow objects."""
        # Create test behavior IR with workflow
        behavior_ir = BehaviorModelIR(
            flows=[
                Flow(
                    name="User Registration",
                    type=FlowType.WORKFLOW,
                    trigger="On user signup",
                    description="Complete user registration process",
                    steps=[
                        Step(
                            order=1,
                            description="Validate email format",
                            action="validate_email",
                            target_entity="User"
                        ),
                        Step(
                            order=2,
                            description="Check email uniqueness",
                            action="check_unique_email",
                            target_entity="User",
                            condition="email is valid"
                        ),
                        Step(
                            order=3,
                            description="Create user account",
                            action="create_user",
                            target_entity="User"
                        ),
                        Step(
                            order=4,
                            description="Send confirmation email",
                            action="send_confirmation",
                            target_entity="User"
                        )
                    ]
                )
            ]
        )

        # Generate workflow code
        workflow_files = self.generator.generate_workflows(behavior_ir)

        # Verify files were generated
        assert len(workflow_files) > 0, "No workflow files generated"

        # Check for main workflow module
        assert "src/workflows/__init__.py" in workflow_files

        # Check for specific workflow file
        assert "src/workflows/user_registration.py" in workflow_files

        # Verify workflow code content
        user_reg_code = workflow_files["src/workflows/user_registration.py"]
        assert "class UserRegistrationWorkflow" in user_reg_code
        assert "async def execute" in user_reg_code
        assert "_execute_validate_email" in user_reg_code
        assert "_execute_check_unique_email" in user_reg_code
        assert "_execute_create_user" in user_reg_code
        assert "_execute_send_confirmation" in user_reg_code

        # Verify step execution order
        assert user_reg_code.index("Step 1:") < user_reg_code.index("Step 2:")
        assert user_reg_code.index("Step 2:") < user_reg_code.index("Step 3:")
        assert user_reg_code.index("Step 3:") < user_reg_code.index("Step 4:")

    def test_state_machine_generation(self):
        """Test that state machines are generated from invariants and transitions."""
        # Create test behavior IR with state transitions
        behavior_ir = BehaviorModelIR(
            flows=[
                Flow(
                    name="Order State Transition",
                    type=FlowType.STATE_TRANSITION,
                    trigger="On order status change",
                    description="Manage order state transitions",
                    steps=[
                        Step(
                            order=1,
                            description="Transition from pending to processing",
                            action="transition_state",
                            target_entity="Order"
                        )
                    ]
                )
            ],
            invariants=[
                Invariant(
                    entity="Order",
                    description="Order total must be positive",
                    expression="total > 0",
                    enforcement_level="strict"
                ),
                Invariant(
                    entity="Order",
                    description="Order must have at least one item",
                    expression="len(items) > 0",
                    enforcement_level="strict"
                )
            ]
        )

        # Generate state machine code
        state_files = self.generator.generate_state_machines(behavior_ir)

        # Verify files were generated
        assert len(state_files) > 0, "No state machine files generated"

        # Check for base state machine module
        assert "src/state_machines/__init__.py" in state_files

        # Check for order state machine
        assert "src/state_machines/order_state.py" in state_files

        # Verify state machine code content
        order_state_code = state_files["src/state_machines/order_state.py"]
        assert "class OrderStateMachine" in order_state_code
        assert "OrderState" in order_state_code
        assert "can_transition_to" in order_state_code
        assert "validate_invariants" in order_state_code

    def test_invariant_validator_generation(self):
        """Test that invariant validators are generated correctly."""
        # Create test behavior IR with invariants
        behavior_ir = BehaviorModelIR(
            invariants=[
                Invariant(
                    entity="Account",
                    description="Balance cannot be negative",
                    expression="balance >= 0",
                    enforcement_level="strict"
                ),
                Invariant(
                    entity="Account",
                    description="Account must have owner",
                    expression="owner_id is not None",
                    enforcement_level="strict"
                ),
                Invariant(
                    entity="Product",
                    description="Price must be positive",
                    expression="price > 0",
                    enforcement_level="eventual"
                )
            ]
        )

        # Generate validators using private method
        validator_files = self.generator._generate_invariant_validators(behavior_ir)

        # Verify files were generated
        assert len(validator_files) > 0, "No validator files generated"

        # Check for validator module
        assert "src/validators/__init__.py" in validator_files

        # Check for entity validators
        assert "src/validators/account_validator.py" in validator_files
        assert "src/validators/product_validator.py" in validator_files

        # Verify account validator content
        account_validator = validator_files["src/validators/account_validator.py"]
        assert "class AccountValidator" in account_validator
        assert "validate_all" in account_validator
        assert "Balance cannot be negative" in account_validator
        assert "Account must have owner" in account_validator

        # Verify product validator content
        product_validator = validator_files["src/validators/product_validator.py"]
        assert "class ProductValidator" in product_validator
        assert "Price must be positive" in product_validator

    def test_event_handler_generation(self):
        """Test that event handlers are generated from event flows."""
        # Create test behavior IR with event handlers
        behavior_ir = BehaviorModelIR(
            flows=[
                Flow(
                    name="Order Placed",
                    type=FlowType.EVENT_HANDLER,
                    trigger="OnOrderPlaced",
                    description="Handle order placement event",
                    steps=[
                        Step(
                            order=1,
                            description="Validate inventory",
                            action="check_inventory",
                            target_entity="Product"
                        ),
                        Step(
                            order=2,
                            description="Reserve inventory",
                            action="reserve_items",
                            target_entity="Inventory"
                        ),
                        Step(
                            order=3,
                            description="Send confirmation",
                            action="send_order_confirmation",
                            target_entity="Order"
                        )
                    ]
                ),
                Flow(
                    name="Payment Received",
                    type=FlowType.EVENT_HANDLER,
                    trigger="OnPaymentReceived",
                    description="Handle payment confirmation",
                    steps=[
                        Step(
                            order=1,
                            description="Update order status",
                            action="update_status",
                            target_entity="Order"
                        )
                    ]
                )
            ]
        )

        # Generate event handlers
        event_files = self.generator._generate_event_handlers(behavior_ir)

        # Verify files were generated
        assert len(event_files) > 0, "No event handler files generated"

        # Check for event handler files
        assert "src/events/handlers.py" in event_files
        assert "src/events/dispatcher.py" in event_files

        # Verify handler content
        handlers_code = event_files["src/events/handlers.py"]
        assert "handle_order_placed" in handlers_code
        assert "handle_payment_received" in handlers_code
        assert "check_inventory" in handlers_code
        assert "update_status" in handlers_code

        # Verify dispatcher content
        dispatcher_code = event_files["src/events/dispatcher.py"]
        assert "class EventDispatcher" in dispatcher_code
        assert "OnOrderPlaced" in dispatcher_code
        assert "OnPaymentReceived" in dispatcher_code

    def test_policy_enforcer_generation(self):
        """Test that policy enforcers are generated from policy flows."""
        # Create test behavior IR with policies
        behavior_ir = BehaviorModelIR(
            flows=[
                Flow(
                    name="Discount Policy",
                    type=FlowType.POLICY,
                    trigger="Before order calculation",
                    description="Apply discount rules",
                    steps=[
                        Step(
                            order=1,
                            description="Check customer tier",
                            action="get_customer_tier",
                            target_entity="Customer"
                        ),
                        Step(
                            order=2,
                            description="Apply tier discount",
                            action="apply_discount",
                            target_entity="Order"
                        )
                    ]
                )
            ]
        )

        # Generate policy enforcers
        policy_files = self.generator._generate_policy_enforcers(behavior_ir)

        # Verify files were generated
        assert len(policy_files) > 0, "No policy files generated"

        # Check for policy enforcer file
        assert "src/policies/enforcer.py" in policy_files

        # Verify policy content
        enforcer_code = policy_files["src/policies/enforcer.py"]
        assert "class PolicyEnforcer" in enforcer_code
        assert "_enforce_discount_policy" in enforcer_code
        assert "get_customer_tier" in enforcer_code
        assert "apply_discount" in enforcer_code

    def test_business_orchestrator_generation(self):
        """Test that business orchestrator coordinates all components."""
        # Create comprehensive behavior IR
        behavior_ir = BehaviorModelIR(
            flows=[
                Flow(
                    name="Order Processing",
                    type=FlowType.WORKFLOW,
                    trigger="On checkout",
                    steps=[
                        Step(order=1, description="Process payment", action="process_payment")
                    ]
                ),
                Flow(
                    name="Order State",
                    type=FlowType.STATE_TRANSITION,
                    trigger="State change",
                    steps=[
                        Step(order=1, description="Transition", action="transition")
                    ]
                ),
                Flow(
                    name="Order Created",
                    type=FlowType.EVENT_HANDLER,
                    trigger="OnOrderCreated",
                    steps=[
                        Step(order=1, description="Handle event", action="handle")
                    ]
                ),
                Flow(
                    name="Pricing Policy",
                    type=FlowType.POLICY,
                    trigger="Before pricing",
                    steps=[
                        Step(order=1, description="Apply rules", action="apply_rules")
                    ]
                )
            ],
            invariants=[
                Invariant(
                    entity="Order",
                    description="Total positive",
                    expression="total > 0"
                )
            ]
        )

        # Generate complete business logic
        all_files = self.generator.generate_business_logic(behavior_ir)

        # Verify orchestrator was generated
        assert "src/business_logic/orchestrator.py" in all_files

        # Verify orchestrator content
        orchestrator_code = all_files["src/business_logic/orchestrator.py"]
        assert "class BusinessOrchestrator" in orchestrator_code
        assert "execute_business_process" in orchestrator_code
        assert "_validate_preconditions" in orchestrator_code
        assert "_execute_process" in orchestrator_code
        assert "_handle_post_process_events" in orchestrator_code

        # Verify all component types are included
        assert "workflows" in orchestrator_code or "from src.workflows" in orchestrator_code
        assert "state_machines" in orchestrator_code or "from src.state_machines" in orchestrator_code
        assert "EventDispatcher" in orchestrator_code
        assert "PolicyEnforcer" in orchestrator_code
        assert "validators" in orchestrator_code or "from src.validators" in orchestrator_code

    def test_empty_behavior_ir(self):
        """Test that generator handles empty BehaviorModelIR gracefully."""
        # Create empty behavior IR
        behavior_ir = BehaviorModelIR()

        # Generate code
        all_files = self.generator.generate_business_logic(behavior_ir)

        # Should generate at least orchestrator
        assert "src/business_logic/orchestrator.py" in all_files

        # Orchestrator should handle empty case
        orchestrator_code = all_files["src/business_logic/orchestrator.py"]
        assert "class BusinessOrchestrator" in orchestrator_code

    def test_comprehensive_integration(self):
        """Test full integration with complex BehaviorModelIR."""
        # Create comprehensive behavior model
        behavior_ir = BehaviorModelIR(
            flows=[
                # Multiple workflows
                Flow(
                    name="User Registration",
                    type=FlowType.WORKFLOW,
                    trigger="On signup",
                    steps=[
                        Step(order=1, description="Validate", action="validate"),
                        Step(order=2, description="Create", action="create"),
                        Step(order=3, description="Notify", action="notify")
                    ]
                ),
                Flow(
                    name="Order Checkout",
                    type=FlowType.WORKFLOW,
                    trigger="On checkout",
                    steps=[
                        Step(order=1, description="Calculate", action="calculate"),
                        Step(order=2, description="Payment", action="process_payment"),
                        Step(order=3, description="Fulfill", action="fulfill_order")
                    ]
                ),
                # State transitions
                Flow(
                    name="Order States",
                    type=FlowType.STATE_TRANSITION,
                    trigger="State change",
                    steps=[
                        Step(order=1, description="Validate transition", action="validate_transition")
                    ]
                ),
                # Event handlers
                Flow(
                    name="User Created",
                    type=FlowType.EVENT_HANDLER,
                    trigger="OnUserCreated",
                    steps=[
                        Step(order=1, description="Send welcome", action="send_welcome_email")
                    ]
                ),
                # Policies
                Flow(
                    name="Fraud Detection",
                    type=FlowType.POLICY,
                    trigger="Before transaction",
                    steps=[
                        Step(order=1, description="Check fraud", action="check_fraud_indicators")
                    ]
                )
            ],
            invariants=[
                Invariant(entity="User", description="Email unique", expression="unique(email)"),
                Invariant(entity="Order", description="Positive total", expression="total > 0"),
                Invariant(entity="Product", description="Valid price", expression="price >= 0")
            ]
        )

        # Generate all business logic
        all_files = self.generator.generate_business_logic(behavior_ir)

        # Count generated files by category
        workflow_count = len([f for f in all_files if "workflows" in f])
        state_count = len([f for f in all_files if "state_machines" in f])
        validator_count = len([f for f in all_files if "validators" in f])
        event_count = len([f for f in all_files if "events" in f])
        policy_count = len([f for f in all_files if "policies" in f])

        # Verify comprehensive generation
        assert workflow_count >= 3  # __init__ + 2 workflows
        assert state_count >= 2     # __init__ + order state
        assert validator_count >= 4  # __init__ + 3 entity validators
        assert event_count >= 2     # handlers + dispatcher
        assert policy_count >= 1    # enforcer

        # Verify orchestrator integrates everything
        orchestrator = all_files["src/business_logic/orchestrator.py"]
        assert "UserRegistrationWorkflow" in all_files["src/workflows/__init__.py"]
        assert "OrderCheckoutWorkflow" in all_files["src/workflows/__init__.py"]

        print(f"\nGenerated {len(all_files)} total files:")
        print(f"  - Workflows: {workflow_count}")
        print(f"  - State Machines: {state_count}")
        print(f"  - Validators: {validator_count}")
        print(f"  - Event Handlers: {event_count}")
        print(f"  - Policies: {policy_count}")
        print(f"  - Total: {len(all_files)}")


if __name__ == "__main__":
    # Run tests
    test = TestBehaviorCodeGenerator()
    test.setup_method()

    print("Testing workflow generation...")
    test.test_workflow_generation()
    print("✅ Workflow generation passed")

    print("\nTesting state machine generation...")
    test.test_state_machine_generation()
    print("✅ State machine generation passed")

    print("\nTesting invariant validator generation...")
    test.test_invariant_validator_generation()
    print("✅ Invariant validator generation passed")

    print("\nTesting event handler generation...")
    test.test_event_handler_generation()
    print("✅ Event handler generation passed")

    print("\nTesting policy enforcer generation...")
    test.test_policy_enforcer_generation()
    print("✅ Policy enforcer generation passed")

    print("\nTesting business orchestrator generation...")
    test.test_business_orchestrator_generation()
    print("✅ Business orchestrator generation passed")

    print("\nTesting empty behavior IR...")
    test.test_empty_behavior_ir()
    print("✅ Empty behavior IR handled")

    print("\nTesting comprehensive integration...")
    test.test_comprehensive_integration()
    print("✅ Comprehensive integration passed")

    print("\n🎉 All tests passed successfully!")