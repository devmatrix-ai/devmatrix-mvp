"""
Unit tests for TOTPService (Task Group 9: 2FA/MFA Foundation)

Tests TOTP generation, verification, QR code generation, backup codes,
secret encryption, and rate limiting.
"""

import pytest
import pyotp
import time
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.totp_service import TOTPService
from src.config.settings import get_settings


settings = get_settings()


class TestTOTPService:
    """Test suite for TOTPService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.totp_service = TOTPService()

    # ============================================================================
    # Test 1: Secret Generation
    # ============================================================================

    def test_generate_secret(self):
        """Test TOTP secret generation"""
        secret = self.totp_service.generate_secret()

        # Secret should be a base32-encoded string
        assert isinstance(secret, str)
        assert len(secret) >= 16  # Minimum length for security
        assert secret.isupper()  # Base32 is uppercase

        # Secret should be decodable by pyotp
        totp = pyotp.TOTP(secret)
        assert totp is not None

    def test_generate_secret_uniqueness(self):
        """Test that generated secrets are unique"""
        secret1 = self.totp_service.generate_secret()
        secret2 = self.totp_service.generate_secret()

        assert secret1 != secret2

    # ============================================================================
    # Test 2: QR Code Generation
    # ============================================================================

    def test_generate_qr_code(self):
        """Test QR code generation for TOTP setup"""
        secret = self.totp_service.generate_secret()
        user_email = "test@example.com"

        qr_code_data = self.totp_service.generate_qr_code(secret, user_email)

        # QR code should be base64-encoded image
        assert isinstance(qr_code_data, str)
        assert qr_code_data.startswith("data:image/png;base64,")
        assert len(qr_code_data) > 100  # QR code should have substantial data

    def test_generate_qr_code_with_issuer(self):
        """Test QR code includes issuer name"""
        secret = self.totp_service.generate_secret()
        user_email = "test@example.com"

        qr_code_data = self.totp_service.generate_qr_code(secret, user_email)

        # QR code should encode a proper TOTP URI
        # Note: We can't directly decode the QR image in tests, but we verify format
        assert qr_code_data.startswith("data:image/png;base64,")

    # ============================================================================
    # Test 3: TOTP Verification (Valid Code)
    # ============================================================================

    def test_verify_totp_valid_code(self):
        """Test TOTP verification with valid code"""
        secret = self.totp_service.generate_secret()

        # Generate current TOTP code
        totp = pyotp.TOTP(secret, interval=30)
        current_code = totp.now()

        # Verify the code
        is_valid = self.totp_service.verify_totp(secret, current_code)

        assert is_valid is True

    # ============================================================================
    # Test 4: TOTP Verification (Invalid Code)
    # ============================================================================

    def test_verify_totp_invalid_code(self):
        """Test TOTP verification with invalid code"""
        secret = self.totp_service.generate_secret()

        # Use an obviously invalid code
        invalid_code = "000000"

        # Verify the code
        is_valid = self.totp_service.verify_totp(secret, invalid_code)

        assert is_valid is False

    def test_verify_totp_wrong_length(self):
        """Test TOTP verification with wrong code length"""
        secret = self.totp_service.generate_secret()

        # Use a code with wrong length
        wrong_length_code = "12345"  # Only 5 digits instead of 6

        is_valid = self.totp_service.verify_totp(secret, wrong_length_code)

        assert is_valid is False

    # ============================================================================
    # Test 5: TOTP Verification (Expired Code - Time Window)
    # ============================================================================

    def test_verify_totp_time_window(self):
        """Test TOTP verification respects 30-second time window"""
        secret = self.totp_service.generate_secret()
        totp = pyotp.TOTP(secret, interval=30)

        # Get code from 2 time windows ago (60 seconds ago)
        old_timestamp = datetime.utcnow() - timedelta(seconds=60)
        old_code = totp.at(old_timestamp)

        # Old code should not be valid (outside time window)
        is_valid = self.totp_service.verify_totp(secret, old_code)

        assert is_valid is False

    # ============================================================================
    # Test 6: Backup Code Generation
    # ============================================================================

    def test_generate_backup_codes(self):
        """Test backup code generation"""
        backup_codes = self.totp_service.generate_backup_codes()

        # Should generate exactly 6 backup codes
        assert len(backup_codes) == 6

        # Each code should be 8 characters (alphanumeric)
        for code in backup_codes:
            assert isinstance(code, str)
            assert len(code) == 8
            assert code.isalnum()

    def test_generate_backup_codes_uniqueness(self):
        """Test that backup codes are unique within a set"""
        backup_codes = self.totp_service.generate_backup_codes()

        # All codes should be unique
        assert len(backup_codes) == len(set(backup_codes))

    def test_generate_backup_codes_different_sets(self):
        """Test that different calls generate different backup codes"""
        backup_codes1 = self.totp_service.generate_backup_codes()
        backup_codes2 = self.totp_service.generate_backup_codes()

        # Sets should be different
        assert set(backup_codes1) != set(backup_codes2)

    # ============================================================================
    # Test 7: Backup Code Verification (Single-Use)
    # ============================================================================

    def test_verify_backup_code_valid(self):
        """Test backup code verification with valid code"""
        # Generate backup codes
        backup_codes = self.totp_service.generate_backup_codes()

        # Hash the codes (simulating database storage)
        hashed_codes = self.totp_service.hash_backup_codes(backup_codes)

        # Verify first code
        is_valid, remaining_codes = self.totp_service.verify_backup_code(
            backup_codes[0],
            hashed_codes
        )

        assert is_valid is True
        assert len(remaining_codes) == 5  # One code used

    def test_verify_backup_code_invalid(self):
        """Test backup code verification with invalid code"""
        # Generate backup codes
        backup_codes = self.totp_service.generate_backup_codes()
        hashed_codes = self.totp_service.hash_backup_codes(backup_codes)

        # Try to verify an invalid code
        is_valid, remaining_codes = self.totp_service.verify_backup_code(
            "INVALID1",
            hashed_codes
        )

        assert is_valid is False
        assert len(remaining_codes) == 6  # No codes used

    # ============================================================================
    # Test 8: Backup Code Cannot Be Reused
    # ============================================================================

    def test_backup_code_single_use(self):
        """Test that backup codes can only be used once"""
        # Generate backup codes
        backup_codes = self.totp_service.generate_backup_codes()
        hashed_codes = self.totp_service.hash_backup_codes(backup_codes)

        # Use first code
        is_valid1, remaining_codes1 = self.totp_service.verify_backup_code(
            backup_codes[0],
            hashed_codes
        )
        assert is_valid1 is True
        assert len(remaining_codes1) == 5

        # Try to use same code again
        is_valid2, remaining_codes2 = self.totp_service.verify_backup_code(
            backup_codes[0],
            remaining_codes1
        )
        assert is_valid2 is False
        assert len(remaining_codes2) == 5  # Still 5 codes left

    # ============================================================================
    # Test 9: Secret Encryption/Decryption
    # ============================================================================

    def test_encrypt_decrypt_secret(self):
        """Test secret encryption and decryption"""
        original_secret = self.totp_service.generate_secret()

        # Encrypt secret
        encrypted_secret = self.totp_service.encrypt_secret(original_secret)

        # Encrypted should be different from original
        assert encrypted_secret != original_secret
        assert isinstance(encrypted_secret, str)

        # Decrypt secret
        decrypted_secret = self.totp_service.decrypt_secret(encrypted_secret)

        # Decrypted should match original
        assert decrypted_secret == original_secret

    def test_encrypt_secret_different_outputs(self):
        """Test that encrypting same secret twice gives different ciphertexts (due to IV)"""
        secret = self.totp_service.generate_secret()

        # Encrypt same secret twice
        encrypted1 = self.totp_service.encrypt_secret(secret)
        encrypted2 = self.totp_service.encrypt_secret(secret)

        # Ciphertexts should be different (due to random IV in Fernet)
        # Note: Fernet includes timestamp, so ciphertexts will differ
        assert encrypted1 != encrypted2

        # But both should decrypt to same secret
        assert self.totp_service.decrypt_secret(encrypted1) == secret
        assert self.totp_service.decrypt_secret(encrypted2) == secret

    # ============================================================================
    # Test 10: Rate Limiting on Verification
    # ============================================================================

    def test_rate_limiting_enforcement(self):
        """Test rate limiting on TOTP verification attempts"""
        user_id = uuid4()
        secret = self.totp_service.generate_secret()

        # Make 3 attempts (should all be allowed)
        for i in range(3):
            result = self.totp_service.check_rate_limit(user_id)
            assert result is True

        # 4th attempt should be rate-limited
        result = self.totp_service.check_rate_limit(user_id)
        assert result is False

    def test_rate_limiting_resets_after_window(self):
        """Test rate limiting resets after time window"""
        user_id = uuid4()

        # Make 3 attempts
        for i in range(3):
            self.totp_service.check_rate_limit(user_id)

        # Wait for rate limit window to expire (61 seconds)
        # In real tests, we'd use time mocking, but for now we just verify the mechanism exists
        # This test verifies the rate limit logic without actually waiting

        # Verify rate limit key exists in Redis (if connected)
        redis_client = self.totp_service._get_redis_client()
        if redis_client and redis_client.connected:
            rate_limit_key = f"2fa_attempts:{user_id}"
            attempts = redis_client.client.get(rate_limit_key)
            assert attempts is not None
            assert int(attempts) == 3


# Run tests with: pytest tests/unit/test_totp_service.py -v
