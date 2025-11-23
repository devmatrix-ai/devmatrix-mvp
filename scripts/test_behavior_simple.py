#!/usr/bin/env python3
"""
Simple test script to verify BehaviorCodeGenerator functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.behavior_code_generator import BehaviorCodeGenerator
from src.cognitive.ir.behavior_model import (
    BehaviorModelIR, Flow, FlowType, Step, Invariant
)


def test_behavior_generation():
    """Test behavior code generation."""
    print("Testing Behavior Code Generation\n" + "="*50)

    # Create behavior model with all types
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
            # Another workflow
            Flow(
                name="Order Processing",
                type=FlowType.WORKFLOW,
                trigger="On order placement",
                description="Process customer order",
                steps=[
                    Step(
                        order=1,
                        description="Validate inventory",
                        action="check_inventory",
                        target_entity="Product"
                    ),
                    Step(
                        order=2,
                        description="Process payment",
                        action="process_payment",
                        target_entity="Payment"
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
                        description="Send confirmation",
                        action="send_notification",
                        target_entity="Customer"
                    )
                ]
            ),
            # Another event handler
            Flow(
                name="User Login",
                type=FlowType.EVENT_HANDLER,
                trigger="OnUserLogin",
                description="Handle user login event",
                steps=[
                    Step(
                        order=1,
                        description="Log login event",
                        action="log_event",
                        target_entity="AuditLog"
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
                entity="User",
                description="Username cannot be empty",
                expression="len(username) > 0",
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
            ),
            Invariant(
                entity="Account",
                description="Balance must be positive",
                expression="balance >= 0",
                enforcement_level="strict"
            )
        ]
    )

    # Check if CodeGenerationService is integrated
    print("\n1. Integration Check")
    print("-" * 40)
    try:
        with open("/home/kwar/code/agentic-ai/src/services/code_generation_service.py", 'r') as f:
            content = f.read()
            checks = [
                ("BehaviorCodeGenerator import", "from src.services.behavior_code_generator import BehaviorCodeGenerator"),
                ("BehaviorCodeGenerator init", "self.behavior_generator = BehaviorCodeGenerator()"),
                ("Behavior generation call", "behavior_files = self.behavior_generator.generate_business_logic")
            ]

            for check_name, check_string in checks:
                if check_string in content:
                    print(f"✅ {check_name} found")
                else:
                    print(f"❌ {check_name} NOT found")
    except Exception as e:
        print(f"❌ Could not check integration: {e}")

    # Test BehaviorCodeGenerator
    print("\n2. Behavior Code Generation")
    print("-" * 40)

    generator = BehaviorCodeGenerator()
    files = generator.generate_business_logic(behavior_model)

    print(f"📁 Generated {len(files)} files total")

    # Categorize and count files
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

    # Display results
    print("\n3. Generated Files by Category")
    print("-" * 40)
    for category, file_list in categories.items():
        if file_list:
            print(f"\n{category} ({len(file_list)} files):")
            for filepath in file_list:
                # Count lines in file
                lines = len(files[filepath].split('\n'))
                print(f"  - {filepath} ({lines} lines)")

    # Calculate metrics
    print("\n4. Generation Metrics")
    print("-" * 40)
    total_lines = sum(len(content.split('\n')) for content in files.values())
    print(f"✅ Total files: {len(files)}")
    print(f"✅ Total lines: {total_lines}")
    print(f"✅ Average lines/file: {total_lines // len(files) if files else 0}")

    # Count by category
    print(f"\n📊 Files by category:")
    print(f"   - Workflows: {len(categories['Workflows'])}")
    print(f"   - State Machines: {len(categories['State Machines'])}")
    print(f"   - Validators: {len(categories['Validators'])}")
    print(f"   - Event Handlers: {len(categories['Event Handlers'])}")
    print(f"   - Policies: {len(categories['Policies'])}")
    print(f"   - Orchestrator: {len(categories['Orchestrator'])}")

    # Sample generated code
    print("\n5. Sample Generated Code")
    print("-" * 40)

    # Show a workflow sample
    workflow_file = next((f for f in files if "user_registration.py" in f), None)
    if workflow_file:
        print(f"\n📄 {workflow_file} (first 25 lines):")
        print("```python")
        lines = files[workflow_file].split('\n')[:25]
        for line in lines:
            print(line)
        print("```")

    # Verify completeness
    print("\n6. Component Verification")
    print("-" * 40)

    verifications = [
        ("User Registration Workflow", any("user_registration" in f for f in files)),
        ("Order Processing Workflow", any("order_processing" in f for f in files)),
        ("Order State Machine", any("order" in f and "state" in f for f in files)),
        ("Payment Event Handler", any("payment_processed" in f for f in files)),
        ("User Validators", any("user_validator" in f for f in files)),
        ("Discount Policy", "src/policies/enforcer.py" in files),
        ("Business Orchestrator", "src/business_logic/orchestrator.py" in files)
    ]

    all_pass = True
    for component, exists in verifications:
        status = "✅" if exists else "❌"
        print(f"{status} {component}")
        if not exists:
            all_pass = False

    # Final summary
    print("\n" + "="*50)
    if all_pass:
        print("✅ All components generated successfully!")
    else:
        print("⚠️ Some components missing (see above)")

    print(f"\n🎉 Behavior code generation test completed!")
    print(f"   Generated {len(files)} files with {total_lines} lines of code")


if __name__ == "__main__":
    test_behavior_generation()