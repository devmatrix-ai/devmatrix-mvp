#!/usr/bin/env python3
"""
Quick test script to verify Task Calculator formulas produce ULTRA-ATOMIC task counts
"""
import sys
sys.path.insert(0, '/home/kwar/code/agentic-ai')

from src.services.masterplan_calculator import MasterPlanCalculator, ComplexityMetrics

def test_calculator():
    """Test task calculator with different system sizes"""
    calculator = MasterPlanCalculator()

    # Test scenarios
    scenarios = [
        {
            "name": "Small System (1 BC, 0 Agg, 0 Svc)",
            "bounded_contexts": 1,
            "aggregates": 0,
            "value_objects": 0,
            "domain_events": 0,
            "services": 0,
            "expected_min": 35,
            "expected_max": 45
        },
        {
            "name": "Medium System (3 BC, 15 Agg, 10 Svc)",
            "bounded_contexts": 3,
            "aggregates": 15,
            "value_objects": 5,
            "domain_events": 20,
            "services": 10,
            "expected_min": 220,
            "expected_max": 280
        },
        {
            "name": "Large System (10 BC, 50 Agg, 30 Svc)",
            "bounded_contexts": 10,
            "aggregates": 50,
            "value_objects": 20,
            "domain_events": 75,
            "services": 30,
            "expected_min": 675,
            "expected_max": 825
        }
    ]

    print("=" * 80)
    print("ULTRA-ATOMIC TASK CALCULATOR TEST")
    print("=" * 80)
    print()

    for scenario in scenarios:
        print(f"📊 {scenario['name']}")
        print("-" * 80)

        # Create metrics
        metrics = ComplexityMetrics()
        metrics.bounded_contexts = scenario["bounded_contexts"]
        metrics.aggregates = scenario["aggregates"]
        metrics.value_objects = scenario["value_objects"]
        metrics.domain_events = scenario["domain_events"]
        metrics.services = scenario["services"]
        metrics.total_entities = (
            metrics.bounded_contexts +
            metrics.aggregates +
            metrics.value_objects +
            metrics.domain_events +
            metrics.services
        )

        # Calculate breakdown
        breakdown = calculator._calculate_task_breakdown(metrics)

        # Results
        print(f"  Setup:          {breakdown.setup_tasks:3d} tasks")
        print(f"  Modeling:       {breakdown.modeling_tasks:3d} tasks")
        print(f"  Persistence:    {breakdown.persistence_tasks:3d} tasks")
        print(f"  Implementation: {breakdown.implementation_tasks:3d} tasks")
        print(f"  Integration:    {breakdown.integration_tasks:3d} tasks")
        print(f"  Testing:        {breakdown.testing_tasks:3d} tasks  ⚠️ CRITICAL")
        print(f"  Deployment:     {breakdown.deployment_tasks:3d} tasks")
        print(f"  Optimization:   {breakdown.optimization_tasks:3d} tasks")
        print()
        print(f"  TOTAL:          {breakdown.total_tasks:3d} tasks")
        print(f"  Expected range: {scenario['expected_min']}-{scenario['expected_max']} tasks")

        # Validation
        if scenario['expected_min'] <= breakdown.total_tasks <= scenario['expected_max']:
            print(f"  ✅ PASS - Within expected range")
        else:
            print(f"  ❌ FAIL - Outside expected range")

        # Testing validation
        if breakdown.testing_tasks >= 12:
            print(f"  ✅ Testing tasks >= 12 minimum")
        else:
            print(f"  ❌ Testing tasks < 12 minimum (CRITICAL BUG)")

        print()

        # Rationale
        rationale = calculator._generate_rationale(metrics, breakdown)
        print(f"  Rationale: {rationale}")
        print()
        print()

if __name__ == "__main__":
    test_calculator()
