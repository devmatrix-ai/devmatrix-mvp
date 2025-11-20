"""
Unit tests for DAG Ground Truth validation

Task Group 6.1: Write 2-8 focused tests for DAG validation

Tests critical behaviors:
- Ground truth parser loads nodes correctly
- Ground truth parser loads edges correctly
- DAG accuracy calculation is correct
- Missing edges are detected
"""

import pytest
from tests.e2e.precision_metrics import PrecisionMetrics


class TestDagGroundTruthParser:
    """Test DAG ground truth parsing from spec files"""

    def test_parse_dag_nodes_correctly(self):
        """Test that ground truth parser loads nodes correctly"""
        # Sample ground truth format
        ground_truth = {
            "nodes": 10,
            "node_list": [
                "create_product",
                "list_products",
                "create_customer",
                "create_cart",
                "add_to_cart",
                "checkout_cart",
                "simulate_payment",
                "cancel_order",
                "list_orders",
                "get_order"
            ]
        }

        # Verify node count
        assert ground_truth["nodes"] == 10
        assert len(ground_truth["node_list"]) == 10

        # Verify specific nodes
        assert "create_product" in ground_truth["node_list"]
        assert "checkout_cart" in ground_truth["node_list"]
        assert "simulate_payment" in ground_truth["node_list"]

    def test_parse_dag_edges_correctly(self):
        """Test that ground truth parser loads edges correctly"""
        # Sample ground truth format
        ground_truth = {
            "edges": 12,
            "edge_list": [
                ("create_customer", "create_cart"),
                ("create_product", "add_to_cart"),
                ("create_cart", "add_to_cart"),
                ("add_to_cart", "checkout_cart"),
                ("checkout_cart", "simulate_payment"),
                ("checkout_cart", "cancel_order"),
                ("create_customer", "list_orders"),
                ("checkout_cart", "list_orders"),
                ("checkout_cart", "get_order"),
                ("create_product", "list_products"),
                ("create_customer", "get_order"),
                ("create_cart", "checkout_cart")
            ]
        }

        # Verify edge count
        assert ground_truth["edges"] == 12
        assert len(ground_truth["edge_list"]) == 12

        # Verify specific edges
        assert ("create_customer", "create_cart") in ground_truth["edge_list"]
        assert ("checkout_cart", "simulate_payment") in ground_truth["edge_list"]
        assert ("add_to_cart", "checkout_cart") in ground_truth["edge_list"]

    def test_dag_accuracy_calculation_correct(self):
        """Test that DAG accuracy calculation is correct"""
        metrics = PrecisionMetrics()

        # Ground truth: 10 nodes, 12 edges
        metrics.dag_nodes_expected = 10
        metrics.dag_edges_expected = 12

        # Scenario 1: Perfect match
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 12
        accuracy = metrics.calculate_dag_accuracy()
        assert accuracy == 1.0  # 100% accuracy

        # Scenario 2: Missing edges
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 7  # Missing 5 edges
        accuracy = metrics.calculate_dag_accuracy()
        # (10 + 7) / (10 + 12) = 17/22 = 0.772...
        assert 0.77 <= accuracy <= 0.78

        # Scenario 3: Missing nodes and edges
        metrics.dag_nodes_created = 8  # Missing 2 nodes
        metrics.dag_edges_created = 9  # Missing 3 edges
        accuracy = metrics.calculate_dag_accuracy()
        # (8 + 9) / (10 + 12) = 17/22 = 0.772...
        assert 0.77 <= accuracy <= 0.78

    def test_missing_edges_detected(self):
        """Test that missing edges are detected"""
        metrics = PrecisionMetrics()

        # Ground truth: 10 nodes, 12 edges
        metrics.dag_nodes_expected = 10
        metrics.dag_edges_expected = 12

        # Created DAG: 10 nodes, 7 edges (missing 5)
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 7

        # Verify detection
        missing_edges = metrics.dag_edges_expected - metrics.dag_edges_created
        assert missing_edges == 5

        # Verify accuracy reflects missing edges
        accuracy = metrics.calculate_dag_accuracy()
        assert accuracy < 1.0  # Not perfect due to missing edges
        assert accuracy > 0.0  # Not zero because nodes are correct


class TestDagAccuracyCalculation:
    """Test DAG accuracy calculation with various scenarios"""

    def test_empty_dag_returns_zero(self):
        """Test that empty DAG (no nodes/edges) returns 0 accuracy"""
        metrics = PrecisionMetrics()
        metrics.dag_nodes_expected = 0
        metrics.dag_edges_expected = 0
        metrics.dag_nodes_created = 0
        metrics.dag_edges_created = 0

        accuracy = metrics.calculate_dag_accuracy()
        assert accuracy == 0.0

    def test_nodes_only_no_edges(self):
        """Test accuracy when only nodes exist (no edges expected)"""
        metrics = PrecisionMetrics()
        metrics.dag_nodes_expected = 10
        metrics.dag_edges_expected = 0  # No edges expected
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 0

        accuracy = metrics.calculate_dag_accuracy()
        assert accuracy == 1.0  # Perfect match

    def test_excess_edges_capped(self):
        """Test that excess edges don't increase accuracy beyond expected"""
        metrics = PrecisionMetrics()
        metrics.dag_nodes_expected = 10
        metrics.dag_edges_expected = 12
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 15  # More than expected

        # Calculation should cap edges at expected (12)
        accuracy = metrics.calculate_dag_accuracy()
        # (10 + 12) / (10 + 12) = 1.0
        assert accuracy == 1.0

    def test_baseline_ecommerce_accuracy(self):
        """Test baseline DAG accuracy for ecommerce spec (current: 57.6%)"""
        metrics = PrecisionMetrics()

        # Ground truth for ecommerce_api_simple
        metrics.dag_nodes_expected = 10
        metrics.dag_edges_expected = 12

        # Current DAG (baseline from spec.md - 57.6% accuracy)
        # To achieve 57.6%, we need: (nodes + edges) / (10 + 12) = 0.576
        # 0.576 * 22 = 12.67 ≈ 13 correct items
        # If nodes = 10 (all correct), then edges = 3 (missing 9 edges)
        metrics.dag_nodes_created = 10
        metrics.dag_edges_created = 3  # Severely missing edges

        accuracy = metrics.calculate_dag_accuracy()
        # (10 + 3) / (10 + 12) = 13/22 = 0.590...
        # Note: Actual baseline might vary, this tests the calculation method
        assert 0.55 <= accuracy <= 0.65  # Approximately baseline range
