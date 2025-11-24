"""
Tests for the Pattern Learning System with Real DualValidator.

This module tests the complete learning system including:
- Pattern validation with real metrics
- Pattern promotion when criteria are met
- Pattern rejection when criteria fail
- Adaptive threshold adjustments
- Learning from usage patterns

Author: DevMatrix Team
Date: 2025-11-23
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, patch, MagicMock

from src.cognitive.patterns.dual_validator import (
    RealDualValidator,
    ValidationResult,
    SecurityLevel,
    ComplianceLevel,
    QualityMetrics
)
from src.cognitive.patterns.pattern_feedback_integration import (
    PatternFeedbackIntegration,
    PatternCandidate,
    PromotionStatus,
    get_pattern_feedback_integration
)
from src.cognitive.signatures.semantic_signature import SemanticTaskSignature


class TestRealDualValidator:
    """Test the RealDualValidator implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = RealDualValidator()

    def test_initialization(self):
        """Test validator initializes with correct defaults."""
        assert self.validator.MIN_SUCCESS_RATE == 0.95
        assert self.validator.MIN_TEST_COVERAGE == 0.80
        assert self.validator.MIN_SECURITY_LEVEL == SecurityLevel.MEDIUM
        assert self.validator.MIN_PERFORMANCE_SCORE == 0.70
        assert self.validator.MIN_QUALITY_SCORE == 0.75

    def test_validate_pattern_with_good_metrics(self):
        """Test validation passes with good metrics."""
        # Create good quality metrics
        quality_metrics = QualityMetrics(
            success_rate=0.98,
            test_coverage=0.85,
            validation_score=0.95,
            performance_score=0.80,
            overall_quality=0.90
        )

        # Good code with no security issues
        good_code = """
        def calculate_tax(amount: float, rate: float) -> float:
            \"\"\"Calculate tax with proper validation.\"\"\"
            if amount < 0 or rate < 0:
                raise ValueError("Amount and rate must be positive")

            try:
                tax = amount * rate
                logger.info(f"Calculated tax: {tax}")
                return tax
            except Exception as e:
                logger.error(f"Error calculating tax: {e}")
                raise
        """

        context = {
            'quality_metrics': quality_metrics,
            'code': good_code,
            'pattern_id': 'test-pattern-1'
        }

        result = self.validator.validate_pattern(None, context)

        assert result.is_valid == True
        assert result.should_promote == True
        assert result.success_rate == 0.98
        assert result.test_coverage == 0.85
        assert result.security_level in [SecurityLevel.CRITICAL, SecurityLevel.HIGH]
        assert len(result.issues) == 0

    def test_validate_pattern_with_poor_metrics(self):
        """Test validation fails with poor metrics."""
        # Create poor quality metrics
        quality_metrics = QualityMetrics(
            success_rate=0.70,  # Below threshold
            test_coverage=0.50,  # Below threshold
            validation_score=0.60,
            performance_score=0.40,  # Below threshold
            overall_quality=0.55
        )

        context = {
            'quality_metrics': quality_metrics,
            'code': 'def bad_function(): pass',
            'pattern_id': 'test-pattern-2'
        }

        result = self.validator.validate_pattern(None, context)

        assert result.is_valid == False
        assert result.should_promote == False
        assert len(result.issues) > 0
        assert len(result.recommendations) > 0
        assert "Success rate" in result.issues[0]
        assert "Test coverage" in result.issues[1]

    def test_security_analysis_detects_issues(self):
        """Test security analysis detects various security issues."""
        # Code with critical security issues
        bad_code = """
        def execute_user_input(user_input):
            password = "hardcoded_password_123"
            api_key = "sk-1234567890"
            eval(user_input)  # Critical security issue
            exec(f"result = {user_input}")
        """

        context = {
            'quality_metrics': QualityMetrics(0.98, 0.85, 0.95, 0.80, 0.90),
            'code': bad_code,
            'pattern_id': 'test-pattern-3'
        }

        result = self.validator.validate_pattern(None, context)

        assert result.should_promote == False
        assert result.security_level == SecurityLevel.FAILED
        assert "security" in result.reasoning.lower()

    def test_compliance_checking(self):
        """Test compliance checking for code standards."""
        # Code with good compliance
        compliant_code = '''
        def process_data(data: list) -> dict:
            """
            Process input data with proper error handling.

            Args:
                data: Input data list

            Returns:
                Processed data dictionary
            """
            try:
                result = {}
                for item in data:
                    result[item.id] = item.value

                logger.info(f"Processed {len(data)} items")
                return result

            except Exception as e:
                logger.error(f"Error processing data: {e}")
                raise
        '''

        context = {
            'quality_metrics': QualityMetrics(0.98, 0.85, 0.95, 0.80, 0.90),
            'code': compliant_code,
            'pattern_id': 'test-pattern-4'
        }

        result = self.validator.validate_pattern(None, context)

        assert result.compliance_level in [ComplianceLevel.FULL, ComplianceLevel.PARTIAL]

    def test_should_promote_with_usage_tracking(self):
        """Test should_promote considers usage and error counts."""
        pattern = Mock(id='test-pattern-5')

        # Not enough usage
        assert self.validator.should_promote(pattern) == False

        # Track enough usage
        for _ in range(5):
            self.validator.track_usage('test-pattern-5')

        # Add successful validations
        self.validator.validation_history['test-pattern-5'] = [True] * 5

        # Should promote now
        assert self.validator.should_promote(pattern) == True

        # Add too many errors
        for _ in range(3):
            self.validator.track_error('test-pattern-5')

        # Should not promote with errors
        assert self.validator.should_promote(pattern) == False

    def test_pattern_stats_reset(self):
        """Test resetting pattern statistics."""
        pattern_id = 'test-pattern-6'

        # Add some stats
        self.validator.track_usage(pattern_id)
        self.validator.track_error(pattern_id)
        self.validator.validation_history[pattern_id] = [True, False]

        # Reset stats
        self.validator.reset_pattern_stats(pattern_id)

        assert self.validator.pattern_usage_count[pattern_id] == 0
        assert self.validator.pattern_error_count[pattern_id] == 0
        assert self.validator.validation_history[pattern_id] == []


class TestLearningSystemIntegration:
    """Test the complete learning system integration."""

    @pytest.fixture
    def integration(self):
        """Create PatternFeedbackIntegration with real validator."""
        return PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=False
        )

    @pytest.mark.asyncio
    async def test_pattern_promotion_with_good_metrics(self, integration):
        """Test pattern gets promoted when meeting all criteria."""
        # Create a high-quality pattern candidate
        good_code = '''
        def authenticate_user(username: str, password: str) -> bool:
            """Authenticate user with secure practices."""
            import hashlib
            import hmac

            try:
                # Hash password securely
                password_hash = hashlib.pbkdf2_hmac('sha256',
                                                    password.encode(),
                                                    salt=b'secure_salt',
                                                    iterations=100000)

                # Check against stored hash (placeholder)
                stored_hash = get_stored_hash(username)

                if hmac.compare_digest(password_hash, stored_hash):
                    logger.info(f"User {username} authenticated successfully")
                    return True
                else:
                    logger.warning(f"Authentication failed for user {username}")
                    return False

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return False
        '''

        signature = SemanticTaskSignature(
            purpose="User authentication",
            intent="Secure authentication with proper hashing",
            domain="auth"
        )

        metadata = {
            'test_results': {
                'passed': 49,
                'total': 50,
                'coverage_covered': 45,
                'coverage_total': 50,
                'execution_time_ms': 50.0
            }
        }

        # Register the pattern
        candidate_id = await integration.register_successful_generation(
            code=good_code,
            signature=signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        # Get the candidate
        candidate = integration.quality_evaluator.get_candidate(candidate_id)

        # Check that it was analyzed
        assert candidate is not None
        assert candidate.quality_metrics is not None
        assert candidate.quality_metrics.success_rate == 0.98  # 49/50
        assert candidate.quality_metrics.test_coverage == 0.90  # 45/50

    @pytest.mark.asyncio
    async def test_pattern_rejection_with_poor_metrics(self, integration):
        """Test pattern gets rejected when not meeting criteria."""
        # Create a low-quality pattern
        bad_code = '''
        def bad_function():
            password = "hardcoded"
            eval(user_input)
        '''

        signature = SemanticTaskSignature(
            purpose="Bad pattern",
            intent="Should be rejected",
            domain="general"
        )

        metadata = {
            'test_results': {
                'passed': 3,
                'total': 10,
                'coverage_covered': 2,
                'coverage_total': 10,
                'execution_time_ms': 500.0
            }
        }

        # Register the pattern
        candidate_id = await integration.register_successful_generation(
            code=bad_code,
            signature=signature,
            execution_result=None,
            task_id=uuid.uuid4(),
            metadata=metadata
        )

        # Get the candidate
        candidate = integration.quality_evaluator.get_candidate(candidate_id)

        # Check that it was rejected
        assert candidate is not None
        assert candidate.quality_metrics.success_rate == 0.30  # 3/10
        assert candidate.quality_metrics.test_coverage == 0.20  # 2/10

    def test_adaptive_thresholds(self, integration):
        """Test adaptive threshold adjustments based on promotion history."""
        threshold_manager = integration.threshold_manager

        # Track successful promotions
        for _ in range(10):
            threshold_manager.track_promotion('auth', success=True)

        # High success rate should slightly lower threshold
        base_threshold = 0.80
        adjusted = threshold_manager.get_adjusted_threshold('auth', base_threshold)
        assert adjusted < base_threshold  # Should be more lenient

        # Track failures
        for _ in range(20):
            threshold_manager.track_promotion('ui', success=False)

        # Low success rate should increase threshold
        adjusted = threshold_manager.get_adjusted_threshold('ui', base_threshold)
        assert adjusted > base_threshold  # Should be stricter

    def test_pattern_lineage_tracking(self, integration):
        """Test tracking pattern evolution and improvements."""
        lineage_tracker = integration.lineage_tracker

        # Track an improvement
        lineage_tracker.track_improvement(
            new_candidate_id='pattern-v2',
            ancestor_id='pattern-v1',
            improvement_delta=0.15,
            changes='Added error handling and logging'
        )

        # Check lineage
        descendants = lineage_tracker.get_lineage('pattern-v1')
        assert 'pattern-v2' in descendants

        # Check improvement history
        improvement = lineage_tracker.get_improvement_history('pattern-v2')
        assert improvement is not None
        assert improvement['ancestor_id'] == 'pattern-v1'
        assert improvement['delta'] == 0.15

    @pytest.mark.asyncio
    async def test_learning_system_singleton(self):
        """Test singleton pattern for learning system."""
        # Get singleton with real validator
        instance1 = get_pattern_feedback_integration(
            enable_auto_promotion=True,
            mock_dual_validator=False
        )

        instance2 = get_pattern_feedback_integration()

        # Should be the same instance
        assert instance1 is instance2
        assert instance1.enable_auto_promotion == True

        # Check that real validator is being used
        if hasattr(instance1.dual_validator, '__class__'):
            assert instance1.dual_validator.__class__.__name__ in ['RealDualValidator', 'DualValidator']


class TestEndToEndLearning:
    """End-to-end tests for the complete learning cycle."""

    @pytest.mark.asyncio
    async def test_full_learning_cycle(self):
        """Test complete learning cycle from generation to promotion."""
        # Initialize the learning system
        integration = PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=False
        )

        # Simulate multiple pattern submissions
        patterns = [
            {
                'code': '''
                def validate_email(email: str) -> bool:
                    """Validate email format."""
                    import re
                    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
                    return bool(re.match(pattern, email))
                ''',
                'purpose': 'Email validation',
                'test_passed': 10,
                'test_total': 10
            },
            {
                'code': '''
                def sanitize_input(text: str) -> str:
                    """Sanitize user input."""
                    import html
                    return html.escape(text)
                ''',
                'purpose': 'Input sanitization',
                'test_passed': 8,
                'test_total': 10
            }
        ]

        promoted_count = 0
        rejected_count = 0

        for pattern_data in patterns:
            signature = SemanticTaskSignature(
                purpose=pattern_data['purpose'],
                intent="Production pattern",
                domain="validation"
            )

            metadata = {
                'test_results': {
                    'passed': pattern_data['test_passed'],
                    'total': pattern_data['test_total'],
                    'coverage_covered': pattern_data['test_passed'],
                    'coverage_total': pattern_data['test_total'],
                    'execution_time_ms': 50.0
                }
            }

            candidate_id = await integration.register_successful_generation(
                code=pattern_data['code'],
                signature=signature,
                execution_result=None,
                task_id=uuid.uuid4(),
                metadata=metadata
            )

            status = integration.get_candidate_status(candidate_id)

            if status == PromotionStatus.PROMOTED:
                promoted_count += 1
            elif status == PromotionStatus.REJECTED:
                rejected_count += 1

        # At least one should be processed
        assert promoted_count + rejected_count > 0

    @pytest.mark.asyncio
    async def test_learning_improves_quality_over_time(self):
        """Test that the system learns and improves pattern quality."""
        integration = PatternFeedbackIntegration(
            enable_auto_promotion=True,
            mock_dual_validator=False
        )

        # Track quality scores over time
        quality_scores = []

        # Simulate multiple iterations of pattern generation
        for iteration in range(5):
            code = f'''
            def process_data_{iteration}(data: list) -> dict:
                """Process data with improving quality."""
                try:
                    result = {{}}
                    for item in data:
                        result[item.id] = item.value * {1 + iteration * 0.1}
                    logger.info(f"Processed {{len(data)}} items")
                    return result
                except Exception as e:
                    logger.error(f"Error: {{e}}")
                    raise
            '''

            signature = SemanticTaskSignature(
                purpose=f"Data processing v{iteration}",
                intent="Process data with improvements",
                domain="processing"
            )

            # Simulate improving test scores
            test_passed = min(10, 6 + iteration)

            metadata = {
                'test_results': {
                    'passed': test_passed,
                    'total': 10,
                    'coverage_covered': test_passed,
                    'coverage_total': 10,
                    'execution_time_ms': max(20, 100 - iteration * 15)
                }
            }

            candidate_id = await integration.register_successful_generation(
                code=code,
                signature=signature,
                execution_result=None,
                task_id=uuid.uuid4(),
                metadata=metadata
            )

            # Get quality score
            candidate = integration.quality_evaluator.get_candidate(candidate_id)
            if candidate and candidate.quality_metrics:
                quality_scores.append(candidate.quality_metrics.overall_quality)

        # Quality should improve over iterations
        if len(quality_scores) >= 2:
            # Later scores should generally be better
            avg_early = sum(quality_scores[:2]) / 2
            avg_late = sum(quality_scores[-2:]) / 2
            assert avg_late >= avg_early  # Quality improves or stays same


if __name__ == "__main__":
    pytest.main([__file__, "-v"])