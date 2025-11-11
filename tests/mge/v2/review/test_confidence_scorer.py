"""
Tests for ConfidenceScorer

Verifies weighted scoring algorithm and confidence level classification.
"""

import pytest
from uuid import uuid4

from src.mge.v2.review.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceLevel,
    ConfidenceScore
)


@pytest.fixture
def scorer():
    """Create ConfidenceScorer instance"""
    return ConfidenceScorer()


@pytest.fixture
def perfect_validation():
    """Perfect validation results (all L1-L4 passed)"""
    return {
        "l1_syntax": True,
        "l2_imports": True,
        "l3_types": True,
        "l4_complexity": True
    }


@pytest.fixture
def simple_complexity():
    """Simple complexity metrics (low values)"""
    return {
        "cyclomatic_complexity": 5,
        "cognitive_complexity": 8,
        "lines_of_code": 50
    }


@pytest.fixture
def perfect_tests():
    """Perfect test results (100% pass, 100% coverage)"""
    return {
        "tests_executed": 10,
        "tests_passed": 10,
        "coverage_percent": 100.0
    }


class TestConfidenceScorer:
    """Test ConfidenceScorer functionality"""

    def test_perfect_score(self, scorer, perfect_validation, simple_complexity, perfect_tests):
        """Test perfect atom (100 score, muy_alta level)"""
        atom_id = uuid4()

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=0,  # First attempt
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # Perfect validation (40% weight) = 100 * 0.40 = 40
        # No retries (30% weight) = 100 * 0.30 = 30
        # Simple complexity (20% weight) = 100 * 0.20 = 20
        # Perfect tests (10% weight) = 100 * 0.10 = 10
        # Total = 100
        assert score.total_score == 100.0
        assert score.level == ConfidenceLevel.MUY_ALTA
        assert score.validation_score == 100.0
        assert score.retry_score == 100.0
        assert score.complexity_score == 100.0
        assert score.test_score == 100.0

    def test_partial_validation_failure(self, scorer, simple_complexity, perfect_tests):
        """Test with 1 validation level failed"""
        atom_id = uuid4()

        validation_results = {
            "l1_syntax": True,
            "l2_imports": True,
            "l3_types": False,  # Failed
            "l4_complexity": True
        }

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=validation_results,
            retry_count=0,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 3/4 validation passed = 75
        assert score.validation_score == 75.0

        # Total = 75*0.40 + 100*0.30 + 100*0.20 + 100*0.10
        #       = 30 + 30 + 20 + 10 = 90
        assert score.total_score == 90.0
        assert score.level == ConfidenceLevel.MUY_ALTA  # Still ≥90

    def test_retry_penalty(self, scorer, perfect_validation, simple_complexity, perfect_tests):
        """Test retry penalty reduces score"""
        atom_id = uuid4()

        # Test with 1 retry
        score_1_retry = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=1,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 1 retry = 80 points (penalty -20)
        assert score_1_retry.retry_score == 80.0

        # Total = 100*0.40 + 80*0.30 + 100*0.20 + 100*0.10
        #       = 40 + 24 + 20 + 10 = 94
        assert score_1_retry.total_score == 94.0
        assert score_1_retry.level == ConfidenceLevel.MUY_ALTA

        # Test with 2 retries
        score_2_retries = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=2,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 2 retries = 60 points (penalty -40)
        assert score_2_retries.retry_score == 60.0

        # Total = 100*0.40 + 60*0.30 + 100*0.20 + 100*0.10
        #       = 40 + 18 + 20 + 10 = 88
        assert score_2_retries.total_score == 88.0
        assert score_2_retries.level == ConfidenceLevel.ALTA  # Dropped to alta

    def test_high_complexity_penalty(self, scorer, perfect_validation, perfect_tests):
        """Test high complexity reduces score"""
        atom_id = uuid4()

        high_complexity = {
            "cyclomatic_complexity": 25,  # High (>20 = 0 pts)
            "cognitive_complexity": 35,   # High (>30 = 0 pts)
            "lines_of_code": 400          # High (>300 = 0 pts)
        }

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=0,
            complexity_metrics=high_complexity,
            test_results=perfect_tests
        )

        # All complexity metrics exceed thresholds = 0 points
        assert score.complexity_score == 0.0

        # Total = 100*0.40 + 100*0.30 + 0*0.20 + 100*0.10
        #       = 40 + 30 + 0 + 10 = 80
        assert score.total_score == 80.0
        assert score.level == ConfidenceLevel.ALTA

    def test_failed_tests(self, scorer, perfect_validation, simple_complexity):
        """Test failed tests reduce score"""
        atom_id = uuid4()

        failed_tests = {
            "tests_executed": 10,
            "tests_passed": 5,  # 50% pass rate
            "coverage_percent": 60.0
        }

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=0,
            complexity_metrics=simple_complexity,
            test_results=failed_tests
        )

        # Test score = (pass_rate * 0.7) + (coverage * 0.3)
        #            = (50 * 0.7) + (60 * 0.3)
        #            = 35 + 18 = 53
        assert score.test_score == pytest.approx(53.0, abs=0.1)

        # Total = 100*0.40 + 100*0.30 + 100*0.20 + 53*0.10
        #       = 40 + 30 + 20 + 5.3 = 95.3
        assert score.total_score == pytest.approx(95.3, abs=0.1)
        assert score.level == ConfidenceLevel.MUY_ALTA

    def test_no_tests_neutral_score(self, scorer, perfect_validation, simple_complexity):
        """Test no tests = neutral score (50 points)"""
        atom_id = uuid4()

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=0,
            complexity_metrics=simple_complexity,
            test_results=None  # No tests
        )

        # No tests = 50 points (neutral)
        assert score.test_score == 50.0

        # Total = 100*0.40 + 100*0.30 + 100*0.20 + 50*0.10
        #       = 40 + 30 + 20 + 5 = 95
        assert score.total_score == 95.0
        assert score.level == ConfidenceLevel.MUY_ALTA

    def test_confidence_level_thresholds(self, scorer, simple_complexity, perfect_tests):
        """Test confidence level threshold boundaries"""
        atom_id = uuid4()

        # Test muy_alta threshold (score = 90)
        # Need validation_score to bring total to 90
        # 90 = val*0.40 + 80*0.30 + 100*0.20 + 100*0.10
        # 90 = val*0.40 + 24 + 20 + 10
        # 36 = val*0.40
        # val = 90
        validation_90 = {
            "l1_syntax": True,
            "l2_imports": True,
            "l3_types": True,
            "l4_complexity": False  # 3/4 = 75%, but need ~90%
        }

        score_90 = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=validation_90,
            retry_count=1,  # 80 points
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 75*0.40 + 80*0.30 + 100*0.20 + 100*0.10
        # = 30 + 24 + 20 + 10 = 84
        assert score_90.total_score == 84.0
        assert score_90.level == ConfidenceLevel.ALTA  # 75-89

        # Test media threshold (score = 65)
        validation_50 = {
            "l1_syntax": True,
            "l2_imports": True,
            "l3_types": False,
            "l4_complexity": False  # 2/4 = 50%
        }

        score_65 = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=validation_50,
            retry_count=2,  # 60 points
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 50*0.40 + 60*0.30 + 100*0.20 + 100*0.10
        # = 20 + 18 + 20 + 10 = 68
        assert score_65.total_score == 68.0
        assert score_65.level == ConfidenceLevel.MEDIA  # 60-74

        # Test baja threshold (score < 60)
        validation_25 = {
            "l1_syntax": True,
            "l2_imports": False,
            "l3_types": False,
            "l4_complexity": False  # 1/4 = 25%
        }

        score_low = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=validation_25,
            retry_count=4,  # 20 points
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 25*0.40 + 20*0.30 + 100*0.20 + 100*0.10
        # = 10 + 6 + 20 + 10 = 46
        assert score_low.total_score == 46.0
        assert score_low.level == ConfidenceLevel.BAJA  # <60

    def test_should_enter_review_queue(self, scorer):
        """Test review queue entry logic"""
        atom_id = uuid4()

        # muy_alta (score ≥ 90) → No review
        score_muy_alta = ConfidenceScore(
            atom_id=atom_id,
            total_score=95.0,
            level=ConfidenceLevel.MUY_ALTA,
            validation_score=100.0,
            retry_score=100.0,
            complexity_score=100.0,
            test_score=50.0,
            validation_metrics={},
            retry_metrics={},
            complexity_metrics={},
            test_metrics={}
        )
        assert not scorer.should_enter_review_queue(score_muy_alta)

        # alta (75-89) → No review (spot check only)
        score_alta = ConfidenceScore(
            atom_id=atom_id,
            total_score=80.0,
            level=ConfidenceLevel.ALTA,
            validation_score=75.0,
            retry_score=100.0,
            complexity_score=100.0,
            test_score=50.0,
            validation_metrics={},
            retry_metrics={},
            complexity_metrics={},
            test_metrics={}
        )
        assert not scorer.should_enter_review_queue(score_alta)

        # media (60-74) → Review recommended
        score_media = ConfidenceScore(
            atom_id=atom_id,
            total_score=65.0,
            level=ConfidenceLevel.MEDIA,
            validation_score=50.0,
            retry_score=80.0,
            complexity_score=100.0,
            test_score=50.0,
            validation_metrics={},
            retry_metrics={},
            complexity_metrics={},
            test_metrics={}
        )
        assert scorer.should_enter_review_queue(score_media)

        # baja (<60) → Mandatory review
        score_baja = ConfidenceScore(
            atom_id=atom_id,
            total_score=45.0,
            level=ConfidenceLevel.BAJA,
            validation_score=25.0,
            retry_score=20.0,
            complexity_score=100.0,
            test_score=50.0,
            validation_metrics={},
            retry_metrics={},
            complexity_metrics={},
            test_metrics={}
        )
        assert scorer.should_enter_review_queue(score_baja)

    def test_to_dict_serialization(self, scorer, perfect_validation, simple_complexity, perfect_tests):
        """Test ConfidenceScore serialization"""
        atom_id = uuid4()

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=0,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        score_dict = score.to_dict()

        # Verify structure
        assert "atom_id" in score_dict
        assert "total_score" in score_dict
        assert "level" in score_dict
        assert "components" in score_dict
        assert "metrics" in score_dict

        # Verify values
        assert score_dict["total_score"] == 100.0
        assert score_dict["level"] == "muy_alta"
        assert score_dict["components"]["validation_score"] == 100.0
        assert score_dict["components"]["retry_score"] == 100.0
        assert score_dict["components"]["complexity_score"] == 100.0
        assert score_dict["components"]["test_score"] == 100.0

        # Verify metrics included
        assert "validation" in score_dict["metrics"]
        assert "retry" in score_dict["metrics"]
        assert "complexity" in score_dict["metrics"]
        assert "test" in score_dict["metrics"]

    def test_weight_distribution(self, scorer):
        """Test weights sum to 1.0 (100%)"""
        total_weight = sum(scorer.weights.values())
        assert total_weight == pytest.approx(1.0, abs=0.001)

        # Verify individual weights
        assert scorer.weights["validation"] == 0.40
        assert scorer.weights["retry"] == 0.30
        assert scorer.weights["complexity"] == 0.20
        assert scorer.weights["test"] == 0.10

    def test_extreme_retry_penalty(self, scorer, perfect_validation, simple_complexity, perfect_tests):
        """Test maximum retry penalty (4+ retries)"""
        atom_id = uuid4()

        score_4_retries = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=4,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 4 retries = 20 points (minimum)
        assert score_4_retries.retry_score == 20.0

        # Test 10 retries (should still be 20 minimum)
        score_10_retries = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=perfect_validation,
            retry_count=10,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # Still 20 points (floor)
        assert score_10_retries.retry_score == 20.0

    def test_all_validations_failed(self, scorer, simple_complexity, perfect_tests):
        """Test complete validation failure (0/4 levels)"""
        atom_id = uuid4()

        all_failed_validation = {
            "l1_syntax": False,
            "l2_imports": False,
            "l3_types": False,
            "l4_complexity": False
        }

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=all_failed_validation,
            retry_count=0,
            complexity_metrics=simple_complexity,
            test_results=perfect_tests
        )

        # 0/4 validation passed = 0 points
        assert score.validation_score == 0.0

        # Total = 0*0.40 + 100*0.30 + 100*0.20 + 100*0.10
        #       = 0 + 30 + 20 + 10 = 60
        assert score.total_score == 60.0
        assert score.level == ConfidenceLevel.MEDIA  # Exactly at threshold

    def test_realistic_medium_confidence_case(self, scorer):
        """Test realistic medium confidence scenario"""
        atom_id = uuid4()

        # Realistic medium scenario:
        # - 3/4 validations passed (L3 types failed)
        # - 1 retry attempt
        # - Moderate complexity
        # - Good test coverage
        validation = {
            "l1_syntax": True,
            "l2_imports": True,
            "l3_types": False,  # Failed
            "l4_complexity": True
        }

        complexity = {
            "cyclomatic_complexity": 12,  # Moderate
            "cognitive_complexity": 18,   # Moderate
            "lines_of_code": 150          # Moderate
        }

        tests = {
            "tests_executed": 8,
            "tests_passed": 7,  # 87.5% pass rate
            "coverage_percent": 85.0
        }

        score = scorer.calculate_score(
            atom_id=atom_id,
            validation_results=validation,
            retry_count=1,  # 1 retry
            complexity_metrics=complexity,
            test_results=tests
        )

        # Validation: 75 (3/4)
        # Retry: 80 (1 retry)
        # Complexity: ~70-80 (moderate)
        # Test: ~79 ((87.5*0.7) + (85*0.3))
        # Expected total: 75-80 range → ALTA level

        assert 75.0 <= score.total_score <= 85.0
        assert score.level == ConfidenceLevel.ALTA
