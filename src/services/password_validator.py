"""
Password Validator Service

Implements NIST-compliant password validation with:
- Minimum 12 characters, maximum 128 characters
- Common password rejection (top 10,000)
- Email/username substring rejection
- zxcvbn entropy scoring (weak/fair/good/strong)

Part of Phase 2 - Task Group 2: Password Complexity Requirements
"""

import os
from typing import Dict, Any, List, Optional
from zxcvbn import zxcvbn

from src.observability import get_logger

logger = get_logger("password_validator")


class PasswordValidator:
    """
    NIST-compliant password validator.

    Usage:
        validator = PasswordValidator()
        result = validator.validate(
            password="MySecureP@ssw0rd2025",
            user_inputs=["user@example.com", "john"]
        )

        if result["valid"]:
            print(f"Password strength: {result['feedback']}")
        else:
            print(f"Errors: {result['errors']}")
    """

    def __init__(self):
        """Initialize password validator and load common passwords list"""
        self.common_passwords = self._load_common_passwords()
        logger.info(f"PasswordValidator initialized with {len(self.common_passwords)} common passwords")

    def _load_common_passwords(self) -> set:
        """
        Load common passwords from file into a set for fast lookup.

        Returns:
            set: Set of common passwords (lowercase)
        """
        common_passwords = set()

        # Determine the path to the common passwords file
        # Relative to this file's location
        current_dir = os.path.dirname(os.path.abspath(__file__))
        passwords_file = os.path.join(current_dir, "..", "data", "common-passwords.txt")

        try:
            with open(passwords_file, "r", encoding="utf-8") as f:
                for line in f:
                    password = line.strip().lower()
                    if password:  # Skip empty lines
                        common_passwords.add(password)

            logger.info(f"Loaded {len(common_passwords)} common passwords from {passwords_file}")

        except FileNotFoundError:
            logger.warning(
                f"Common passwords file not found: {passwords_file}. "
                "Common password check will be skipped."
            )
        except Exception as e:
            logger.error(
                f"Error loading common passwords file: {str(e)}. "
                "Common password check will be skipped.",
                exc_info=True
            )

        return common_passwords

    def validate(self, password: str, user_inputs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Validate password strength and complexity.

        Args:
            password: Password to validate
            user_inputs: List of user-specific inputs (email, username, etc.) to check against

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,           # True if password passes all checks
                "score": int,            # zxcvbn score 0-4 (0=weak, 4=strong)
                "feedback": str,         # Human-readable strength: weak/fair/good/strong
                "errors": list[str]      # List of validation errors
            }
        """
        errors = []
        user_inputs = user_inputs or []

        # ========================================
        # Check 1: Minimum Length (12 characters)
        # ========================================
        if len(password) < 12:
            errors.append("Password must be at least 12 characters")

        # ========================================
        # Check 2: Maximum Length (128 characters)
        # ========================================
        if len(password) > 128:
            errors.append("Password must be no more than 128 characters")

        # ========================================
        # Check 3: Common Password Rejection
        # ========================================
        if password.lower() in self.common_passwords:
            errors.append("Password is too common")

        # ========================================
        # Check 4: Email/Username Substring Rejection
        # ========================================
        for user_input in user_inputs:
            if user_input and user_input.lower() in password.lower():
                errors.append(f"Password cannot contain '{user_input}'")

        # ========================================
        # Check 5: zxcvbn Entropy Scoring
        # ========================================
        # Only run zxcvbn if password has minimum length (to avoid IndexError on empty passwords)
        score = 0
        zxcvbn_warning = ""

        if len(password) > 0:
            try:
                result = zxcvbn(password, user_inputs=user_inputs or [])
                score = result['score']

                # Get feedback from zxcvbn
                zxcvbn_warning = result.get('feedback', {}).get('warning', '')
                zxcvbn_suggestions = result.get('feedback', {}).get('suggestions', [])

                # If password is weak (score < 3) and short (< 16 chars), add warning
                if score < 3 and len(password) < 16:
                    if zxcvbn_warning:
                        errors.append(zxcvbn_warning)
                    elif score < 2:
                        errors.append("Password is too weak")
            except Exception as e:
                # If zxcvbn fails, default to score 0
                logger.warning(f"zxcvbn evaluation failed: {str(e)}")
                score = 0

        # Convert score to human-readable feedback
        feedback = self._get_feedback(score)

        # ========================================
        # Return Validation Result
        # ========================================
        return {
            "valid": len(errors) == 0,
            "score": score,
            "feedback": feedback,
            "errors": errors
        }

    def _get_feedback(self, score: int) -> str:
        """
        Convert zxcvbn score to human-readable feedback.

        Args:
            score: zxcvbn score (0-4)

        Returns:
            Feedback string: weak/fair/good/strong
        """
        feedback_map = {
            0: "weak",
            1: "weak",
            2: "fair",
            3: "good",
            4: "strong"
        }
        return feedback_map.get(score, "unknown")
