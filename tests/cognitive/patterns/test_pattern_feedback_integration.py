"""
Tests for Pattern Feedback Integration - Complete Pattern Promotion Pipeline.

Comprehensive test suite covering:
- Quality evaluation storage
- Pattern analysis and scoring
- Auto-promotion pipeline
- DAG synchronization
- Lineage tracking

Spec Reference: Task 5.5 - Pattern Feedback Integration End-to-End Tests
Target Coverage: >90%
"""

import uuid
import pytest
from datetime import datetime
from typing import Dict, Any

from src.cognitive.patterns.pattern_feedback_integration import (
    PatternFeedbackIntegration,
    QualityEvaluator,
    PatternAnalyzer,
    DualValidator,
    AdaptiveThresholdManager,
    PatternLineageTracker,
    PromotionStatus,
    ExecutionMetrics,
    ValidationMetrics,
    QualityMetrics,
    PatternCandidate,
    DomainThreshold,
    get_pattern_feedback_integration,
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature
from src.services.validation_strategies import (
    ValidationResult,
    ValidationError,
    ValidationSeverity,
)


# Test fixtures
@pytest.fixture
def sample_signature():
    """Sample semantic task signature."""
    return SemanticTaskSignature(
        purpose="hash_password",
        intent="Hash user password with bcrypt for secure storage",
        domain="auth",
        inputs={"password": "str"},
        outputs={"hashed": "str"}
    )


@pytest.fixture
def sample_code_good():
    """Sample high-quality code."""
    return '''
def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()
'''


@pytest.fixture
def sample_code_bad():
    """Sample low-quality code with issues."""
    return '''
def hp(p):
    # TODO: implement
    pass
'''


@pytest.fixture
def sample_validation_result_good():
    """Sample validation result (passing)."""
    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        rules_applied=["syntax", "type_hints", "loc_limit", "placeholders"],
        metadata={"type_coverage": 1.0}
    )


@pytest.fixture
def sample_validation_result_bad():
    """Sample validation result (failing)."""
    return ValidationResult(
        is_valid=False,
        errors=[
            ValidationError(
                rule="placeholder_detection",
                severity=ValidationSeverity.ERROR,
                message="TODO comment found"
            ),
            ValidationError(
                rule="type_annotation",
                severity=ValidationSeverity.ERROR,
                message="Missing type hints"
            )
        ],
        warnings=[],
        rules_applied=["syntax", "type_hints", "placeholders"],
        metadata={"type_coverage": 0.0}
    )


# Task 5.1: Quality Evaluation Storage Layer Tests
class TestQualityEvaluator:
    """Test quality evaluation and storage."""

    def test_store_candidate(self, sample_signature):
        """Test candidate storage with metadata."""
        evaluator = QualityEvaluator()

        candidate_id = evaluator.store_candidate(
            code="def test(): pass",
            signature=sample_signature,
            task_id=uuid.uuid4(),
            metadata={"source": "test"}
        )

        assert candidate_id is not None
        assert isinstance(candidate_id, str)

        candidate = evaluator.get_candidate(candidate_id)
        assert candidate is not None
        assert candidate.code == "def test(): pass"
        assert candidate.signature == sample_signature

    def test_track_execution_results(self, sample_signature):
        """Test execution result tracking."""
        evaluator = QualityEvaluator()

        candidate_id = evaluator.store_candidate(
            code="def test(): pass",
            signature=sample_signature,
            task_id=uuid.uuid4()
        )

        evaluator.track_execution_results(
            candidate_id=candidate_id,
            test_passed=95,
            test_total=100,
            coverage_lines_covered=190,
            coverage_lines_total=200,
            execution_time_ms=150.0,
            memory_usage_mb=50.0
        )

        candidate = evaluator.get_candidate(candidate_id)
        assert candidate.execution_metrics is not None
        assert candidate.execution_metrics.test_passed == 95
        assert candidate.execution_metrics.test_total == 100
        assert candidate.execution_metrics.coverage_lines_covered == 190
        assert candidate.execution_metrics.execution_time_ms == 150.0

    def test_track_validation_results(self, sample_signature, sample_validation_result_good):
        """Test validation result tracking."""
        evaluator = QualityEvaluator()

        candidate_id = evaluator.store_candidate(
            code="def test(): pass",
            signature=sample_signature,
            task_id=uuid.uuid4()
        )

        evaluator.track_validation_results(
            candidate_id=candidate_id,
            validation_result=sample_validation_result_good
        )

        candidate = evaluator.get_candidate(candidate_id)
        assert candidate.validation_metrics is not None
        assert candidate.validation_metrics.syntax_valid is True
        assert candidate.validation_metrics.rules_total == 4

    def test_calculate_quality_metrics(self, sample_signature):
        """Test quality metrics calculation."""
        evaluator = QualityEvaluator()

        candidate_id = evaluator.store_candidate(
            code="def test(): pass",
            signature=sample_signature,
            task_id=uuid.uuid4()
        )

        # Add execution metrics
        evaluator.track_execution_results(
            candidate_id=candidate_id,
            test_passed=95,
            test_total=100,
            coverage_lines_covered=190,
            coverage_lines_total=200,
            execution_time_ms=100.0
        )

        metrics = evaluator.calculate_quality_metrics(candidate_id)

        assert metrics.success_rate == 0.95
        assert metrics.test_coverage == 0.95
        assert metrics.overall_quality > 0.0

    def test_domain_thresholds(self):
        """Test domain-specific thresholds."""
        evaluator = QualityEvaluator()

        auth_threshold = evaluator.get_threshold('auth')
        assert auth_threshold.promotion_score == 0.90  # Stricter

        ui_threshold = evaluator.get_threshold('ui')
        assert ui_threshold.promotion_score == 0.75  # More lenient

        default_threshold = evaluator.get_threshold('unknown_domain')
        assert default_threshold.promotion_score == 0.80  # Default

    def test_batch_store(self, sample_signature):
        """Test batch candidate storage."""
        evaluator = QualityEvaluator()

        candidates = [
            ("code1", sample_signature, uuid.uuid4()),
            ("code2", sample_signature, uuid.uuid4()),
            ("code3", sample_signature, uuid.uuid4()),
        ]

        candidate_ids = evaluator.batch_store(candidates)

        assert len(candidate_ids) == 3
        for candidate_id in candidate_ids:
            assert evaluator.get_candidate(candidate_id) is not None


# Task 5.2: Pattern Analysis and Scoring Tests
class TestPatternAnalyzer:
    """Test pattern analysis and scoring."""

    def test_score_reusability_high(self):
        """Test reusability scoring for high-quality code."""
        analyzer = PatternAnalyzer()

        code = '''
def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
'''

        score = analyzer.score_reusability(code)
        assert score > 0.8  # High reusability

    def test_score_reusability_low(self):
        """Test reusability scoring for low-quality code."""
        analyzer = PatternAnalyzer()

        code = '''
def process():
    val1 = "hardcoded_string_value"
    val2 = "another_hardcoded_value"
    val3 = "yet_another_magic_string"
    return 123456789
'''

        score = analyzer.score_reusability(code)
        assert score <= 0.9  # Lower or equal reusability due to hardcoded values

    def test_analyze_security_safe(self):
        """Test security analysis for safe code."""
        analyzer = PatternAnalyzer()

        code = '''
def validate_input(data: str) -> str:
    """Sanitize input data."""
    return data.strip()
'''

        score = analyzer.analyze_security(code)
        assert score >= 1.0  # No security issues

    def test_analyze_security_unsafe(self):
        """Test security analysis for unsafe code."""
        analyzer = PatternAnalyzer()

        code = '''
def login():
    password = "hardcoded_password_123"
    eval(user_input)
'''

        score = analyzer.analyze_security(code)
        assert score < 0.5  # Multiple security issues

    def test_analyze_code_quality_good(self):
        """Test code quality analysis for good code."""
        analyzer = PatternAnalyzer()

        code = '''
def calculate_total(items: list) -> float:
    """Calculate total price."""
    try:
        # Calculate sum
        return sum(item.price for item in items)
    except Exception as e:
        logger.error(f"Error: {e}")
        return 0.0
'''

        score = analyzer.analyze_code_quality(code)
        assert score > 0.9  # High quality

    def test_analyze_code_quality_bad(self):
        """Test code quality analysis for bad code."""
        analyzer = PatternAnalyzer()

        code = '''
def a(x):
                        if True:
                            if True:
                                if True:
                                    return x
'''

        score = analyzer.analyze_code_quality(code)
        assert score < 0.9  # Deep nesting, short name

    def test_calculate_promotion_score(self, sample_signature):
        """Test composite promotion score calculation."""
        analyzer = PatternAnalyzer()

        quality_metrics = QualityMetrics(
            success_rate=0.95,
            test_coverage=0.95,
            validation_score=1.0,
            performance_score=0.9,
            overall_quality=0.94
        )

        candidate = PatternCandidate(
            candidate_id=str(uuid.uuid4()),
            code="def test(): pass",
            signature=sample_signature,
            task_id=uuid.uuid4()
        )

        score, breakdown = analyzer.calculate_promotion_score(
            candidate=candidate,
            quality_metrics=quality_metrics,
            reusability=0.9,
            security=1.0,
            code_quality=0.95
        )

        assert 0.0 <= score <= 1.0
        assert 'quality' in breakdown
        assert 'reusability' in breakdown
        assert 'security' in breakdown
        assert 'code_quality' in breakdown
        assert score > 0.85  # Should be high for good metrics


# Task 5.3: Auto-Promotion Pipeline Tests
class TestDualValidator:
    """Test dual-validator (Claude + GPT-4)."""

    def test_mock_validate_high_quality(self, sample_signature):
        """Test mock validation with high quality metrics."""
        validator = DualValidator(mock_mode=True)

        quality_metrics = QualityMetrics(
            success_rate=0.95,
            test_coverage=0.95,
            validation_score=1.0,
            performance_score=0.9,
            overall_quality=0.94
        )

        result = validator.validate_pattern(
            code="def test(): pass",
            signature=sample_signature,
            quality_metrics=quality_metrics
        )

        assert result.claude_score > 0.9
        assert result.gpt4_score > 0.9
        assert result.agreement is True
        assert result.approved is True

    def test_mock_validate_low_quality(self, sample_signature):
        """Test mock validation with low quality metrics."""
        validator = DualValidator(mock_mode=True)

        quality_metrics = QualityMetrics(
            success_rate=0.5,
            test_coverage=0.6,
            validation_score=0.7,
            performance_score=0.5,
            overall_quality=0.58
        )

        result = validator.validate_pattern(
            code="def test(): pass",
            signature=sample_signature,
            quality_metrics=quality_metrics
        )

        assert result.approved is False  # Low quality should not be approved


class TestAdaptiveThresholdManager:
    """Test adaptive threshold management."""

    def test_track_promotion(self):
        """Test promotion tracking."""
        manager = AdaptiveThresholdManager()

        manager.track_promotion("auth", success=True)
        manager.track_promotion("auth", success=True)
        manager.track_promotion("auth", success=False)

        history = manager.get_domain_history("auth")
        assert len(history) == 3
        assert history == [True, True, False]

    def test_get_adjusted_threshold_insufficient_data(self):
        """Test threshold adjustment with insufficient data."""
        manager = AdaptiveThresholdManager()

        # Less than 10 samples
        for i in range(5):
            manager.track_promotion("auth", success=True)

        threshold = manager.get_adjusted_threshold("auth", 0.80)
        assert threshold == 0.80  # No adjustment with <10 samples

    def test_get_adjusted_threshold_high_success(self):
        """Test threshold adjustment with high success rate."""
        manager = AdaptiveThresholdManager()

        # 95% success rate
        for i in range(20):
            manager.track_promotion("auth", success=(i < 19))

        threshold = manager.get_adjusted_threshold("auth", 0.80)
        assert threshold < 0.80  # Should be more lenient

    def test_get_adjusted_threshold_low_success(self):
        """Test threshold adjustment with low success rate."""
        manager = AdaptiveThresholdManager()

        # 60% success rate
        for i in range(20):
            manager.track_promotion("auth", success=(i < 12))

        threshold = manager.get_adjusted_threshold("auth", 0.80)
        assert threshold > 0.80  # Should be stricter


class TestPatternLineageTracker:
    """Test pattern lineage tracking."""

    def test_track_improvement(self):
        """Test improvement tracking."""
        tracker = PatternLineageTracker()

        ancestor_id = "pattern-v1"
        new_id = "pattern-v2"

        tracker.track_improvement(
            new_candidate_id=new_id,
            ancestor_id=ancestor_id,
            improvement_delta=0.15,
            changes="Improved error handling"
        )

        lineage = tracker.get_lineage(ancestor_id)
        assert new_id in lineage

        history = tracker.get_improvement_history(new_id)
        assert history is not None
        assert history['ancestor_id'] == ancestor_id
        assert history['delta'] == 0.15

    def test_get_lineage_empty(self):
        """Test lineage for non-existent pattern."""
        tracker = PatternLineageTracker()

        lineage = tracker.get_lineage("non-existent")
        assert lineage == []


# Task 5.4: DAG Integration Tests
class TestPatternFeedbackIntegration:
    """Test complete pattern feedback integration."""

    def test_register_successful_generation_basic(
        self,
        sample_signature,
        sample_code_good
    ):
        """Test basic pattern registration."""
        integration = PatternFeedbackIntegration(enable_auto_promotion=False)

        candidate_id = integration.register_successful_generation(
            code=sample_code_good,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata={}
        )

        assert candidate_id is not None
        status = integration.get_candidate_status(candidate_id)
        assert status == PromotionStatus.PENDING

    def test_register_with_test_results(
        self,
        sample_signature,
        sample_code_good
    ):
        """Test registration with test results."""
        integration = PatternFeedbackIntegration(enable_auto_promotion=False)

        metadata = {
            'test_results': {
                'passed': 95,
                'total': 100,
                'coverage_covered': 190,
                'coverage_total': 200,
                'execution_time_ms': 100.0
            }
        }

        candidate_id = integration.register_successful_generation(
            code=sample_code_good,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        candidate = integration.quality_evaluator.get_candidate(candidate_id)
        assert candidate.execution_metrics is not None
        assert candidate.execution_metrics.test_passed == 95

    def test_register_with_validation_results(
        self,
        sample_signature,
        sample_code_good,
        sample_validation_result_good
    ):
        """Test registration with validation results."""
        integration = PatternFeedbackIntegration(enable_auto_promotion=False)

        metadata = {
            'validation_result': sample_validation_result_good
        }

        candidate_id = integration.register_successful_generation(
            code=sample_code_good,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        candidate = integration.quality_evaluator.get_candidate(candidate_id)
        assert candidate.validation_metrics is not None
        assert candidate.validation_metrics.syntax_valid is True

    def test_auto_promotion_high_quality(
        self,
        sample_signature,
        sample_code_good,
        sample_validation_result_good
    ):
        """Test auto-promotion with high-quality pattern."""
        integration = PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=True
        )

        metadata = {
            'test_results': {
                'passed': 100,
                'total': 100,
                'coverage_covered': 200,
                'coverage_total': 200,
                'execution_time_ms': 80.0
            },
            'validation_result': sample_validation_result_good
        }

        candidate_id = integration.register_successful_generation(
            code=sample_code_good,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        status = integration.get_candidate_status(candidate_id)
        assert status == PromotionStatus.PROMOTED  # Should be promoted

        score = integration.get_candidate_score(candidate_id)
        assert score is not None
        assert score > 0.80

    def test_auto_promotion_low_quality(
        self,
        sample_signature,
        sample_code_bad,
        sample_validation_result_bad
    ):
        """Test auto-promotion rejection for low-quality pattern."""
        integration = PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=True
        )

        metadata = {
            'test_results': {
                'passed': 50,
                'total': 100,
                'coverage_covered': 100,
                'coverage_total': 200,
                'execution_time_ms': 200.0
            },
            'validation_result': sample_validation_result_bad
        }

        candidate_id = integration.register_successful_generation(
            code=sample_code_bad,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        status = integration.get_candidate_status(candidate_id)
        assert status == PromotionStatus.REJECTED  # Should be rejected

    def test_sync_to_dag_promoted_pattern(
        self,
        sample_signature,
        sample_code_good,
        sample_validation_result_good
    ):
        """Test DAG synchronization for promoted pattern."""
        integration = PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=True
        )

        metadata = {
            'test_results': {
                'passed': 100,
                'total': 100,
                'coverage_covered': 200,
                'coverage_total': 200,
                'execution_time_ms': 80.0
            },
            'validation_result': sample_validation_result_good
        }

        candidate_id = integration.register_successful_generation(
            code=sample_code_good,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        # Wait for promotion
        status = integration.get_candidate_status(candidate_id)
        assert status == PromotionStatus.PROMOTED

        # Sync to DAG
        synced = integration.sync_to_dag(candidate_id)
        assert synced is True

    def test_sync_to_dag_non_promoted_pattern(
        self,
        sample_signature,
        sample_code_bad
    ):
        """Test DAG synchronization for non-promoted pattern."""
        integration = PatternFeedbackIntegration(enable_auto_promotion=False)

        candidate_id = integration.register_successful_generation(
            code=sample_code_bad,
            signature=sample_signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata={}
        )

        # Attempt sync (should fail)
        synced = integration.sync_to_dag(candidate_id)
        assert synced is False

    def test_get_pattern_feedback_integration_singleton(self):
        """Test singleton pattern."""
        integration1 = get_pattern_feedback_integration()
        integration2 = get_pattern_feedback_integration()

        assert integration1 is integration2  # Same instance
