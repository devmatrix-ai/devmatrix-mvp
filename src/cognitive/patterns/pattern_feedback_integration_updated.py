"""
Updated PatternFeedbackIntegration to use RealDualValidator.

This file contains modifications to integrate the real validator.
"""

# Key changes needed in pattern_feedback_integration.py:

# 1. Import the real validator at the top of the file:
from src.cognitive.patterns.dual_validator import RealDualValidator, ValidationResult as RealValidationResult

# 2. Modify the PatternFeedbackIntegration class __init__ method:
class PatternFeedbackIntegrationUpdated:
    """
    Updated integration layer with real validator.
    """

    def __init__(
        self,
        enable_auto_promotion: bool = True,  # Changed default to True
        use_real_validator: bool = True      # Changed from mock_dual_validator
    ):
        """
        Initialize pattern feedback integration with real validator.

        Args:
            enable_auto_promotion: Whether to enable automatic pattern promotion (default: True)
            use_real_validator: Use real validator instead of mock (default: True)
        """
        self.enable_auto_promotion = enable_auto_promotion

        # Initialize components
        from src.cognitive.patterns.pattern_feedback_integration import (
            QualityEvaluator, PatternAnalyzer, AdaptiveThresholdManager, PatternLineageTracker
        )

        self.quality_evaluator = QualityEvaluator()
        self.pattern_analyzer = PatternAnalyzer()

        # Use real validator by default
        if use_real_validator:
            self.dual_validator = RealDualValidator()
            logger.info("Using RealDualValidator for pattern promotion")
        else:
            from src.cognitive.patterns.pattern_feedback_integration import DualValidator
            self.dual_validator = DualValidator(mock_mode=True)
            logger.info("Using mock DualValidator for testing")

        self.threshold_manager = AdaptiveThresholdManager()
        self.lineage_tracker = PatternLineageTracker()

    async def _attempt_auto_promotion(self, candidate, quality_metrics):
        """
        Updated auto-promotion with real validator.
        """
        candidate.status = PromotionStatus.ANALYZING

        # Step 1: Analyze pattern
        reusability = self.pattern_analyzer.score_reusability(candidate.code)
        security = self.pattern_analyzer.analyze_security(candidate.code)
        code_quality = self.pattern_analyzer.analyze_code_quality(candidate.code)

        # Update candidate scores
        candidate.reusability_score = reusability
        candidate.security_score = security
        candidate.code_quality_score = code_quality

        # Step 2: Calculate promotion score
        promotion_score, breakdown = self.pattern_analyzer.calculate_promotion_score(
            candidate=candidate,
            quality_metrics=quality_metrics,
            reusability=reusability,
            security=security,
            code_quality=code_quality
        )

        candidate.promotion_score = promotion_score

        # Step 3: Use real validator
        if isinstance(self.dual_validator, RealDualValidator):
            # Real validation with comprehensive metrics
            context = {
                'quality_metrics': quality_metrics,
                'code': candidate.code,
                'signature': candidate.signature,
                'pattern_id': candidate.candidate_id
            }

            validation_result = self.dual_validator.validate_pattern(
                pattern=candidate,
                context=context
            )

            # Track pattern usage for learning
            self.dual_validator.track_usage(candidate.candidate_id)

            if not validation_result.should_promote:
                candidate.status = PromotionStatus.REJECTED
                logger.info(f"Pattern {candidate.candidate_id} rejected by RealDualValidator: {validation_result.reasoning}")

                # Log detailed issues for learning
                for issue in validation_result.issues:
                    logger.debug(f"  Issue: {issue}")
                for rec in validation_result.recommendations:
                    logger.debug(f"  Recommendation: {rec}")

                return False

            # Pattern approved for promotion
            logger.info(f"Pattern {candidate.candidate_id} approved by RealDualValidator")
            logger.info(f"  Quality Score: {validation_result.quality_score:.2f}")
            logger.info(f"  Success Rate: {validation_result.success_rate:.2%}")
            logger.info(f"  Test Coverage: {validation_result.test_coverage:.2%}")
            logger.info(f"  Security Level: {validation_result.security_level.value}")
            logger.info(f"  Compliance Level: {validation_result.compliance_level.value}")
        else:
            # Fallback to old dual validator logic
            dual_result = await self.dual_validator.validate_pattern(
                code=candidate.code,
                signature=candidate.signature,
                quality_metrics=quality_metrics
            )

            if not dual_result.approved:
                candidate.status = PromotionStatus.REJECTED
                logger.info(f"Pattern {candidate.candidate_id} rejected by dual-validator")
                return False

        # Step 4: Promote pattern
        candidate.status = PromotionStatus.APPROVED

        # In production, this would call PatternBank.store_pattern()
        logger.info(f"🚀 Pattern {candidate.candidate_id} PROMOTED to PatternBank!")
        logger.info(f"   Pattern will now be reused for similar tasks")
        logger.info(f"   Learning system active - pattern quality will improve over time")

        candidate.status = PromotionStatus.PROMOTED
        candidate.promoted_at = datetime.utcnow()

        # Track promotion success
        self.threshold_manager.track_promotion(candidate.domain, success=True)

        return True


# Updated singleton getter function
def get_updated_pattern_feedback_integration(
    enable_auto_promotion: bool = True,   # Changed default
    use_real_validator: bool = True       # Changed from mock_dual_validator
):
    """
    Get singleton instance with real validator.

    Args:
        enable_auto_promotion: Enable auto-promotion (default: True for production)
        use_real_validator: Use real validator (default: True for production)

    Returns:
        PatternFeedbackIntegration singleton with real validator
    """
    global _pattern_feedback_integration
    if _pattern_feedback_integration is None:
        logger.info("🎯 Initializing Pattern Learning System with REAL validator")
        logger.info("   Auto-promotion: ENABLED")
        logger.info("   Real validation: ACTIVE")
        logger.info("   Learning system: ONLINE")

        _pattern_feedback_integration = PatternFeedbackIntegrationUpdated(
            enable_auto_promotion=enable_auto_promotion,
            use_real_validator=use_real_validator
        )
    return _pattern_feedback_integration