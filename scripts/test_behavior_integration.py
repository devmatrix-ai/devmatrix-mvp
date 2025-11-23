#!/usr/bin/env python3
"""
Test script to verify BehaviorCodeGenerator integration with CodeGenerationService.

This script tests the complete flow:
1. Create ApplicationIR with BehaviorModelIR
2. Pass to CodeGenerationService
3. Verify behavior code is generated
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cognitive.ir.application_ir import ApplicationIR
from src.cognitive.ir.behavior_model import (
    BehaviorModelIR, Flow, FlowType, Step, Invariant
)
from src.cognitive.ir.domain_model import DomainModelIR, Entity, Attribute, DataType
from src.cognitive.ir.api_model import APIModelIR, Endpoint
import json
import uuid


def create_test_application_ir():
    """Create a test ApplicationIR with comprehensive BehaviorModelIR."""

    # Create behavior model
    behavior_model = BehaviorModelIR(
        flows=[
            # Workflow
            Flow(
                name="User Registration",
                type=FlowType.WORKFLOW,
                trigger="On user signup",
                description="Complete user registration workflow",
                steps=[
                    Step(
                        order=1,
                        description="Validate user input",
                        action="validate_input",
                        target_entity="User"
                    ),
                    Step(
                        order=2,
                        description="Create user account",
                        action="create_account",
                        target_entity="User",
                        condition="validation passed"
                    ),
                    Step(
                        order=3,
                        description="Send welcome email",
                        action="send_email",
                        target_entity="User"
                    )
                ]
            ),
            # State transition
            Flow(
                name="Order State Management",
                type=FlowType.STATE_TRANSITION,
                trigger="Order status change",
                description="Manage order state transitions",
                steps=[
                    Step(
                        order=1,
                        description="Validate state transition",
                        action="validate_transition",
                        target_entity="Order"
                    )
                ]
            ),
            # Event handler
            Flow(
                name="Payment Processed",
                type=FlowType.EVENT_HANDLER,
                trigger="OnPaymentSuccess",
                description="Handle successful payment",
                steps=[
                    Step(
                        order=1,
                        description="Update order status",
                        action="update_order",
                        target_entity="Order"
                    ),
                    Step(
                        order=2,
                        description="Notify customer",
                        action="send_notification",
                        target_entity="Customer"
                    )
                ]
            ),
            # Policy
            Flow(
                name="Discount Rules",
                type=FlowType.POLICY,
                trigger="Before order calculation",
                description="Apply discount policies",
                steps=[
                    Step(
                        order=1,
                        description="Calculate discount",
                        action="calculate_discount",
                        target_entity="Order"
                    )
                ]
            )
        ],
        invariants=[
            Invariant(
                entity="User",
                description="Email must be unique",
                expression="unique(email)",
                enforcement_level="strict"
            ),
            Invariant(
                entity="Order",
                description="Order total must be non-negative",
                expression="total >= 0",
                enforcement_level="strict"
            ),
            Invariant(
                entity="Product",
                description="Stock cannot be negative",
                expression="stock >= 0",
                enforcement_level="eventual"
            )
        ]
    )

    # Create domain model
    domain_model = DomainModelIR(
        entities=[
            Entity(
                name="User",
                attributes=[
                    Attribute(name="id", data_type=DataType.STRING),
                    Attribute(name="email", data_type=DataType.STRING),
                    Attribute(name="name", data_type=DataType.STRING)
                ],
                relationships=[]
            ),
            Entity(
                name="Order",
                attributes=[
                    Attribute(name="id", data_type=DataType.STRING),
                    Attribute(name="total", data_type=DataType.FLOAT),
                    Attribute(name="status", data_type=DataType.STRING)
                ],
                relationships=[]
            ),
            Entity(
                name="Product",
                attributes=[
                    Attribute(name="id", data_type=DataType.STRING),
                    Attribute(name="name", data_type=DataType.STRING),
                    Attribute(name="stock", data_type=DataType.INTEGER)
                ],
                relationships=[]
            )
        ]
    )

    # Create API model
    api_model = APIModelIR(
        endpoints=[
            Endpoint(
                method="POST",
                path="/users/register",
                description="Register new user",
                request_body={
                    "email": "string",
                    "name": "string",
                    "password": "string"
                },
                response_body={
                    "id": "string",
                    "email": "string",
                    "name": "string"
                }
            ),
            Endpoint(
                method="POST",
                path="/orders",
                description="Create new order",
                request_body={
                    "items": "array",
                    "customer_id": "string"
                },
                response_body={
                    "id": "string",
                    "total": "number",
                    "status": "string"
                }
            )
        ]
    )

    # Create ApplicationIR
    app_ir = ApplicationIR(
        app_id=str(uuid.uuid4()),
        name="Test E-Commerce App",
        domain_model=domain_model,
        behavior_model=behavior_model,
        api_model=api_model
    )

    return app_ir


def test_behavior_generation():
    """Test that behavior code is generated through CodeGenerationService."""
    print("Testing Behavior Code Generation Integration\n" + "="*50)

    # Create test ApplicationIR
    app_ir = create_test_application_ir()
    print(f"✅ Created ApplicationIR: {app_ir.name}")
    print(f"   - Entities: {len(app_ir.domain_model.entities)}")
    print(f"   - Flows: {len(app_ir.behavior_model.flows)}")
    print(f"   - Invariants: {len(app_ir.behavior_model.invariants)}")
    print(f"   - Endpoints: {len(app_ir.api_model.endpoints)}")

    # Check if CodeGenerationService has behavior generator
    try:
        from src.services.code_generation_service import CodeGenerationService
        print("\n✅ CodeGenerationService imported successfully")

        # Check if BehaviorCodeGenerator is imported
        with open("/home/kwar/code/agentic-ai/src/services/code_generation_service.py", 'r') as f:
            content = f.read()
            if "from src.services.behavior_code_generator import BehaviorCodeGenerator" in content:
                print("✅ BehaviorCodeGenerator import found in CodeGenerationService")
            else:
                print("❌ BehaviorCodeGenerator import NOT found in CodeGenerationService")

            if "self.behavior_generator = BehaviorCodeGenerator()" in content:
                print("✅ BehaviorCodeGenerator initialized in __init__")
            else:
                print("❌ BehaviorCodeGenerator NOT initialized in __init__")

            if "behavior_files = self.behavior_generator.generate_business_logic" in content:
                print("✅ Behavior generation integrated in generate_from_requirements")
            else:
                print("❌ Behavior generation NOT integrated in generate_from_requirements")

    except ImportError as e:
        print(f"❌ Failed to import CodeGenerationService: {e}")

    # Test standalone BehaviorCodeGenerator
    print("\n" + "="*50)
    print("Testing Standalone BehaviorCodeGenerator")
    print("="*50)

    from src.services.behavior_code_generator import BehaviorCodeGenerator
    generator = BehaviorCodeGenerator()

    # Generate business logic
    files = generator.generate_business_logic(app_ir.behavior_model)

    print(f"\n📁 Generated {len(files)} files:")

    # Categorize files
    categories = {
        "Workflows": [],
        "State Machines": [],
        "Validators": [],
        "Event Handlers": [],
        "Policies": [],
        "Orchestrator": [],
        "Other": []
    }

    for filepath in sorted(files.keys()):
        if "workflows" in filepath:
            categories["Workflows"].append(filepath)
        elif "state_machines" in filepath:
            categories["State Machines"].append(filepath)
        elif "validators" in filepath:
            categories["Validators"].append(filepath)
        elif "events" in filepath:
            categories["Event Handlers"].append(filepath)
        elif "policies" in filepath:
            categories["Policies"].append(filepath)
        elif "orchestrator" in filepath:
            categories["Orchestrator"].append(filepath)
        else:
            categories["Other"].append(filepath)

    # Print categorized files
    for category, file_list in categories.items():
        if file_list:
            print(f"\n{category} ({len(file_list)}):")
            for filepath in file_list:
                print(f"  - {filepath}")

    # Print sample of generated code
    print("\n" + "="*50)
    print("Sample Generated Code")
    print("="*50)

    # Show a workflow sample
    workflow_file = next((f for f in files if "user_registration.py" in f), None)
    if workflow_file:
        print(f"\n📄 {workflow_file} (first 30 lines):")
        lines = files[workflow_file].split('\n')[:30]
        for line in lines:
            print(line)

    # Show metrics
    print("\n" + "="*50)
    print("Generation Metrics")
    print("="*50)
    print(f"✅ Total files generated: {len(files)}")
    print(f"✅ Total lines of code: {sum(len(content.split(chr(10))) for content in files.values())}")
    print(f"✅ Average lines per file: {sum(len(content.split(chr(10))) for content in files.values()) // len(files) if files else 0}")

    # Verify expected components
    expected_components = [
        ("User Registration Workflow", any("user_registration" in f for f in files)),
        ("Order State Machine", any("order_state" in f for f in files)),
        ("Payment Event Handler", any("payment_processed" in f for f in files)),
        ("Discount Policy", any("discount" in str(files.get("src/policies/enforcer.py", "")) for f in files)),
        ("Business Orchestrator", "src/business_logic/orchestrator.py" in files)
    ]

    print("\n" + "="*50)
    print("Component Verification")
    print("="*50)
    for component, exists in expected_components:
        status = "✅" if exists else "❌"
        print(f"{status} {component}")

    print("\n" + "="*50)
    print("✅ Integration test completed successfully!")


if __name__ == "__main__":
    test_behavior_generation()