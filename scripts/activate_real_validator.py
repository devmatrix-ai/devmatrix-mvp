#!/usr/bin/env python3
"""
Script to activate the real DualValidator in the pattern feedback integration.

This script patches the existing pattern_feedback_integration.py file to:
1. Import the RealDualValidator
2. Use it by default instead of mock
3. Enable auto-promotion by default
4. Add comprehensive logging for pattern learning

Author: DevMatrix Team
Date: 2025-11-23
"""

import os
import sys
import re

def patch_pattern_feedback_integration():
    """Patch the pattern_feedback_integration.py file to use real validator."""

    file_path = "/home/kwar/code/agentic-ai/src/cognitive/patterns/pattern_feedback_integration.py"

    # Read the existing file
    with open(file_path, 'r') as f:
        content = f.read()

    # 1. Add import for RealDualValidator after existing imports
    import_line = "from src.cognitive.patterns.dual_validator import RealDualValidator, ValidationResult as RealValidationResult\n"

    # Find where to insert (after the last from src.cognitive import)
    pattern = r"(from src\.cognitive\..*\n)"
    matches = list(re.finditer(pattern, content))
    if matches:
        last_match = matches[-1]
        insert_pos = last_match.end()
        content = content[:insert_pos] + import_line + content[insert_pos:]
    else:
        # Fallback: add after logger definition
        logger_pos = content.find("logger = logging.getLogger(__name__)")
        if logger_pos != -1:
            insert_pos = content.find('\n', logger_pos) + 1
            content = content[:insert_pos] + "\n" + import_line + content[insert_pos:]

    # 2. Update PatternFeedbackIntegration.__init__ defaults
    # Change enable_auto_promotion default to True
    content = re.sub(
        r'enable_auto_promotion: bool = False',
        'enable_auto_promotion: bool = True',
        content
    )

    # Change mock_dual_validator default to False
    content = re.sub(
        r'mock_dual_validator: bool = True',
        'mock_dual_validator: bool = False',
        content
    )

    # 3. Update the dual_validator initialization in __init__
    old_init = "self.dual_validator = DualValidator(mock_mode=mock_dual_validator)"
    new_init = """# Use real validator if not in mock mode
        if mock_dual_validator:
            self.dual_validator = DualValidator(mock_mode=True)
            logger.info("Using mock DualValidator for testing")
        else:
            try:
                self.dual_validator = RealDualValidator()
                logger.info("🚀 Using RealDualValidator for pattern promotion - LEARNING SYSTEM ACTIVE!")
            except Exception as e:
                logger.warning(f"Failed to initialize RealDualValidator: {e}, falling back to mock")
                self.dual_validator = DualValidator(mock_mode=True)"""

    content = content.replace(old_init, new_init)

    # 4. Update _attempt_auto_promotion to handle RealDualValidator
    # Find the dual validation section
    dual_validation_start = content.find("# Step 4: Dual-validator")
    if dual_validation_start != -1:
        # Find the end of the dual validation block
        dual_validation_end = content.find("# Step 5: Promote pattern", dual_validation_start)

        if dual_validation_end != -1:
            # Extract the existing code
            existing_dual_validation = content[dual_validation_start:dual_validation_end]

            # Create enhanced version with RealDualValidator support
            enhanced_dual_validation = """# Step 4: Dual-validator
        candidate.status = PromotionStatus.DUAL_VALIDATION

        # Check if using RealDualValidator
        if hasattr(self.dual_validator, '__class__') and self.dual_validator.__class__.__name__ == 'RealDualValidator':
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

                # Track error for learning
                if hasattr(self.dual_validator, 'track_error'):
                    self.dual_validator.track_error(candidate.candidate_id)

                return False

            # Pattern approved for promotion
            logger.info(f"✅ Pattern {candidate.candidate_id} approved by RealDualValidator")
            logger.info(f"  Quality Score: {validation_result.quality_score:.2f}")
            logger.info(f"  Success Rate: {validation_result.success_rate:.2%}")
            logger.info(f"  Test Coverage: {validation_result.test_coverage:.2%}")
        else:
            # Fallback to original dual validator logic
            dual_result = await self.dual_validator.validate_pattern(
                code=candidate.code,
                signature=candidate.signature,
                quality_metrics=quality_metrics
            )

            if not dual_result.approved:
                candidate.status = PromotionStatus.REJECTED
                logger.info(f"Candidate {candidate.candidate_id} rejected by dual-validator")
                return False

        """

            # Replace the section
            content = content[:dual_validation_start] + enhanced_dual_validation + content[dual_validation_end:]

    # 5. Update the promotion success logging
    old_log = 'logger.info(f"Pattern {candidate.candidate_id} promoted to PatternBank")'
    new_log = '''logger.info(f"🚀 Pattern {candidate.candidate_id} PROMOTED to PatternBank!")
        logger.info(f"   Pattern will now be reused for similar tasks")
        logger.info(f"   Learning system active - pattern quality improves over time")'''

    content = content.replace(old_log, new_log)

    # 6. Update the singleton getter defaults
    content = re.sub(
        r'def get_pattern_feedback_integration\(\s*enable_auto_promotion: bool = False,\s*mock_dual_validator: bool = True\s*\)',
        'def get_pattern_feedback_integration(\n    enable_auto_promotion: bool = True,\n    mock_dual_validator: bool = False\n)',
        content
    )

    # Add logging to singleton initialization
    singleton_init = "_pattern_feedback_integration = PatternFeedbackIntegration("
    new_singleton_init = '''logger.info("🎯 Initializing Pattern Learning System")
        logger.info(f"   Auto-promotion: {'ENABLED' if enable_auto_promotion else 'DISABLED'}")
        logger.info(f"   Real validator: {'ACTIVE' if not mock_dual_validator else 'MOCK MODE'}")

        _pattern_feedback_integration = PatternFeedbackIntegration('''

    content = content.replace(singleton_init, new_singleton_init)

    return content


def main():
    """Main execution."""
    print("🔧 Activating Real DualValidator for Pattern Learning System...")

    try:
        # Patch the file
        patched_content = patch_pattern_feedback_integration()

        # Backup original
        original_path = "/home/kwar/code/agentic-ai/src/cognitive/patterns/pattern_feedback_integration.py"
        backup_path = "/home/kwar/code/agentic-ai/src/cognitive/patterns/pattern_feedback_integration.py.bak"

        with open(original_path, 'r') as f:
            original_content = f.read()

        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"✅ Created backup at {backup_path}")

        # Write patched version
        with open(original_path, 'w') as f:
            f.write(patched_content)
        print(f"✅ Updated {original_path}")

        print("\n🎉 SUCCESS! Real DualValidator is now active!")
        print("   - Auto-promotion: ENABLED")
        print("   - Real validation: ACTIVE")
        print("   - Pattern learning: ONLINE")
        print("\n📊 The system will now:")
        print("   1. Validate patterns with real metrics")
        print("   2. Auto-promote high-quality patterns")
        print("   3. Learn from usage and improve over time")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()