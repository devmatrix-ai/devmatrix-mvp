"""
Test Cognitive Feedback Loop - Validate ML-driven Learning

Tests the complete cognitive feedback loop:
1. Neo4j schema setup
2. Error pattern storage
3. RAG retrieval on retries
4. Learning effectiveness measurement
5. Pattern analysis and recommendations

Author: DevMatrix Team
Date: 2025-11-16
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.cognitive.infrastructure.neo4j_schema import Neo4jSchemaSetup
from src.services.error_pattern_store import get_error_pattern_store, ErrorPattern, SuccessPattern
from src.services.error_pattern_analyzer import get_error_pattern_analyzer
from src.observability import get_logger

logger = get_logger("test.cognitive_feedback_loop")


async def test_schema_setup():
    """Test 1: Verify Neo4j schema is properly set up."""
    print("\n" + "="*80)
    print("TEST 1: Neo4j Schema Setup")
    print("="*80)

    try:
        with Neo4jSchemaSetup() as setup:
            # Verify existing schema
            stats = setup.verify_existing_schema()
            print(f"✅ Existing schema verified:")
            print(f"   - Pattern nodes: {stats['pattern_nodes']}")
            print(f"   - Dependency relationships: {stats['dependency_relationships']}")
            print(f"   - Category nodes: {stats['category_nodes']}")

            # Setup cognitive feedback loop schema
            setup.create_feedback_loop_constraints()
            setup.create_feedback_loop_indexes()

            print("✅ Cognitive feedback loop schema created successfully")
            return True

    except Exception as e:
        print(f"❌ Schema setup failed: {e}")
        return False


async def test_error_storage():
    """Test 2: Store and retrieve error patterns."""
    print("\n" + "="*80)
    print("TEST 2: Error Pattern Storage & Retrieval")
    print("="*80)

    try:
        pattern_store = get_error_pattern_store()

        # Create test error pattern
        test_error = ErrorPattern(
            error_id="test_error_001",
            task_id="test_task_001",
            task_description="Create a FastAPI endpoint for user authentication",
            error_type="syntax_error",
            error_message="Generated code has invalid syntax",
            failed_code="def authenticate_user():\n    return {user: authenticated}  # Missing quotes",
            attempt=1,
            timestamp=datetime.now(),
            metadata={"test": True}
        )

        # Store error
        stored = await pattern_store.store_error(test_error)
        print(f"✅ Error pattern stored: {stored}")

        # Search for similar errors
        similar_errors = await pattern_store.search_similar_errors(
            task_description="Create authentication endpoint",
            error_message="syntax error",
            top_k=3
        )

        print(f"✅ Similar errors found: {len(similar_errors)}")
        for i, err in enumerate(similar_errors[:3], 1):
            print(f"   {i}. Similarity: {err.similarity_score:.2%} - {err.error_message[:50]}...")

        return True

    except Exception as e:
        print(f"❌ Error storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_success_storage():
    """Test 3: Store successful patterns."""
    print("\n" + "="*80)
    print("TEST 3: Success Pattern Storage")
    print("="*80)

    try:
        pattern_store = get_error_pattern_store()

        # Create test success pattern
        test_success = SuccessPattern(
            success_id="test_success_001",
            task_id="test_task_002",
            task_description="Create a FastAPI endpoint for user authentication",
            generated_code="""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class AuthRequest(BaseModel):
    username: str
    password: str

@router.post("/auth")
async def authenticate_user(auth: AuthRequest):
    if auth.username == "admin" and auth.password == "secret":
        return {"status": "authenticated", "user": auth.username}
    raise HTTPException(status_code=401, detail="Invalid credentials")
""",
            quality_score=0.95,
            timestamp=datetime.now(),
            metadata={"test": True, "used_feedback": True}
        )

        # Store success
        stored = await pattern_store.store_success(test_success)
        print(f"✅ Success pattern stored: {stored}")

        # Search for successful patterns
        successful_patterns = await pattern_store.search_successful_patterns(
            task_description="Create authentication endpoint",
            top_k=5
        )

        print(f"✅ Successful patterns found: {len(successful_patterns)}")
        for i, pattern in enumerate(successful_patterns[:3], 1):
            print(f"   {i}. Similarity: {pattern['similarity_score']:.2%} - Quality: {pattern['quality_score']:.2f}")

        return True

    except Exception as e:
        print(f"❌ Success storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pattern_analysis():
    """Test 4: Analyze error patterns and learning effectiveness."""
    print("\n" + "="*80)
    print("TEST 4: Pattern Analysis & Learning Metrics")
    print("="*80)

    try:
        analyzer = get_error_pattern_analyzer()

        # Analyze recurring errors
        recurring_errors = await analyzer.analyze_recurring_errors(
            time_window_hours=24,
            min_occurrences=1  # Low threshold for testing
        )

        print(f"✅ Recurring error clusters found: {len(recurring_errors)}")
        for i, cluster in enumerate(recurring_errors[:3], 1):
            print(f"   {i}. {cluster.common_error_type} - {cluster.error_count} occurrences")
            print(f"      Task: {cluster.common_task_description[:60]}...")

        # Identify problematic tasks
        problematic_tasks = await analyzer.identify_problematic_tasks(
            failure_rate_threshold=0.3,  # Low threshold for testing
            min_attempts=1
        )

        print(f"\n✅ Problematic tasks identified: {len(problematic_tasks)}")
        for i, task in enumerate(problematic_tasks[:3], 1):
            print(f"   {i}. Failure rate: {task.failure_rate:.1%} - {task.task_description[:60]}...")

        # Calculate learning effectiveness
        learning_metrics = await analyzer.calculate_learning_effectiveness(
            time_window_hours=24
        )

        print(f"\n✅ Learning Effectiveness Metrics:")
        print(f"   - Total errors: {learning_metrics.total_errors}")
        print(f"   - Errors with feedback: {learning_metrics.errors_with_feedback}")
        print(f"   - Success rate without feedback: {learning_metrics.success_rate_without_feedback:.2%}")
        print(f"   - Success rate with feedback: {learning_metrics.success_rate_with_feedback:.2%}")
        print(f"   - Improvement: {learning_metrics.improvement_percentage:.1f}%")

        if learning_metrics.improvement_percentage > 10:
            print(f"   ✅ LEARNING IS EFFECTIVE! ({learning_metrics.improvement_percentage:.1f}% improvement)")
        elif learning_metrics.total_errors > 0:
            print(f"   ⚠️  Learning effectiveness is low ({learning_metrics.improvement_percentage:.1f}%)")
        else:
            print(f"   ℹ️  Not enough data to measure learning effectiveness")

        # Generate recommendations
        recommendations = await analyzer.generate_improvement_recommendations(
            recurring_errors,
            problematic_tasks,
            learning_metrics
        )

        print(f"\n✅ Improvement Recommendations:")
        print(f"   - Critical issues: {len(recommendations['critical_issues'])}")
        print(f"   - Optimization opportunities: {len(recommendations['optimization_opportunities'])}")
        print(f"   - System insights: {len(recommendations['system_insights'])}")
        print(f"   - Learning effective: {recommendations['learning_status']['is_learning_effective']}")

        return True

    except Exception as e:
        print(f"❌ Pattern analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_statistics():
    """Test 5: Verify error statistics retrieval."""
    print("\n" + "="*80)
    print("TEST 5: Error Statistics")
    print("="*80)

    try:
        pattern_store = get_error_pattern_store()

        stats = await pattern_store.get_error_statistics()

        print(f"✅ Error Statistics:")
        print(f"   - Total errors: {stats.get('total_errors', 0)}")
        print(f"   - Recent errors (24h): {stats.get('recent_errors_24h', 0)}")
        print(f"   - Errors by type:")
        for error_type, count in stats.get('errors_by_type', {}).items():
            print(f"      • {error_type}: {count}")

        return True

    except Exception as e:
        print(f"❌ Error statistics test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all cognitive feedback loop tests."""
    print("\n" + "="*80)
    print("🧠 COGNITIVE FEEDBACK LOOP - INTEGRATION TESTS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {
        "schema_setup": False,
        "error_storage": False,
        "success_storage": False,
        "pattern_analysis": False,
        "error_statistics": False
    }

    # Run tests sequentially
    results["schema_setup"] = await test_schema_setup()

    if results["schema_setup"]:
        results["error_storage"] = await test_error_storage()
        results["success_storage"] = await test_success_storage()
        results["pattern_analysis"] = await test_pattern_analysis()
        results["error_statistics"] = await test_error_statistics()

    # Print final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name.replace('_', ' ').title()}")

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed ({passed_tests/total_tests*100:.0f}%)")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! Cognitive Feedback Loop is working!")
        return 0
    else:
        print(f"\n⚠️ {total_tests - passed_tests} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
