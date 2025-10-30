"""
TOTP Service for 2FA/MFA (Task Group 9: Phase 2)

Implements Time-based One-Time Password (TOTP) functionality for two-factor authentication.
Compatible with Google Authenticator, Authy, 1Password, and other TOTP-compatible apps.

Features:
- TOTP secret generation (RFC 6238 compliant)
- QR code generation for easy enrollment
- 6-digit codes with 30-second time window
- 6 single-use backup codes per user
- Encrypted secret storage at rest (Fernet symmetric encryption)
- Rate limiting: max 3 2FA verification attempts per minute
"""

import pyotp
import qrcode
import io
import base64
import secrets
import bcrypt
from typing import List, Tuple, Optional
from uuid import UUID
from cryptography.fernet import Fernet

from src.config.settings import get_settings
from src.state.redis_manager import RedisManager
from src.observability import get_logger

logger = get_logger("totp_service")
settings = get_settings()

# Global Redis manager instance for rate limiting
_redis_manager: Optional[RedisManager] = None


def get_redis_client() -> Optional[RedisManager]:
    """
    Get Redis client for rate limiting.

    Returns:
        RedisManager instance or None if Redis unavailable
    """
    global _redis_manager

    if _redis_manager is None:
        try:
            _redis_manager = RedisManager(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=0,
                enable_fallback=True
            )
        except Exception as e:
            logger.warning(f"Redis unavailable for 2FA rate limiting: {str(e)}")
            return None

    return _redis_manager


class TOTPService:
    """
    TOTP Service for 2FA/MFA functionality.

    Usage:
        totp_service = TOTPService()

        # Generate secret and QR code for enrollment
        secret = totp_service.generate_secret()
        qr_code = totp_service.generate_qr_code(secret, user_email)

        # Verify TOTP code
        is_valid = totp_service.verify_totp(secret, code)

        # Generate backup codes
        backup_codes = totp_service.generate_backup_codes()
        hashed_codes = totp_service.hash_backup_codes(backup_codes)

        # Verify backup code
        is_valid, remaining_codes = totp_service.verify_backup_code(code, hashed_codes)

        # Encrypt/decrypt secret
        encrypted = totp_service.encrypt_secret(secret)
        decrypted = totp_service.decrypt_secret(encrypted)
    """

    def __init__(self):
        """Initialize TOTP service"""
        self.issuer_name = settings.TOTP_ISSUER_NAME
        self.digits = settings.TOTP_DIGITS
        self.interval = settings.TOTP_INTERVAL

        # Initialize Fernet encryption
        self._init_encryption_key()

    def _init_encryption_key(self):
        """
        Initialize Fernet encryption key for TOTP secrets.

        Uses TOTP_ENCRYPTION_KEY from settings, or generates a temporary key if not configured.
        """
        encryption_key = settings.TOTP_ENCRYPTION_KEY

        if encryption_key:
            # Use configured encryption key
            try:
                self.fernet = Fernet(encryption_key.encode())
                logger.info("TOTP encryption key loaded from settings")
            except Exception as e:
                logger.error(f"Invalid TOTP_ENCRYPTION_KEY: {str(e)}")
                raise ValueError(
                    "Invalid TOTP_ENCRYPTION_KEY. Generate a valid key with: "
                    "python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        else:
            # Generate temporary key (NOT recommended for production)
            logger.warning(
                "TOTP_ENCRYPTION_KEY not configured. Generating temporary key. "
                "WARNING: TOTP secrets will not be decryptable after server restart. "
                "Set TOTP_ENCRYPTION_KEY in environment for production."
            )
            self.fernet = Fernet(Fernet.generate_key())

    def generate_secret(self) -> str:
        """
        Generate a random TOTP secret (base32-encoded).

        Returns:
            str: Base32-encoded secret compatible with TOTP apps
        """
        secret = pyotp.random_base32()
        logger.debug("Generated new TOTP secret")
        return secret

    def generate_qr_code(self, secret: str, user_email: str) -> str:
        """
        Generate QR code for TOTP enrollment.

        Args:
            secret: Base32-encoded TOTP secret
            user_email: User's email address (displayed in authenticator app)

        Returns:
            str: Base64-encoded PNG image with data URI prefix (data:image/png;base64,...)
        """
        try:
            # Create TOTP provisioning URI
            totp = pyotp.TOTP(secret, interval=self.interval, digits=self.digits)
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name=self.issuer_name
            )

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            logger.debug(f"Generated QR code for user: {user_email}")

            # Return data URI
            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.error(f"Failed to generate QR code: {str(e)}", exc_info=True)
            raise ValueError(f"QR code generation failed: {str(e)}")

    def verify_totp(self, secret: str, code: str) -> bool:
        """
        Verify TOTP code against secret.

        Args:
            secret: Base32-encoded TOTP secret
            code: 6-digit TOTP code from authenticator app

        Returns:
            bool: True if code is valid, False otherwise
        """
        try:
            # Validate code format
            if not code or len(code) != self.digits:
                logger.debug(f"Invalid TOTP code length: {len(code) if code else 0}")
                return False

            # Create TOTP instance
            totp = pyotp.TOTP(secret, interval=self.interval, digits=self.digits)

            # Verify code (allows 1 time window before/after for clock drift)
            is_valid = totp.verify(code, valid_window=1)

            if is_valid:
                logger.debug("TOTP code verified successfully")
            else:
                logger.debug("TOTP code verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"TOTP verification error: {str(e)}", exc_info=True)
            return False

    def generate_backup_codes(self, count: int = 6) -> List[str]:
        """
        Generate backup codes for 2FA recovery.

        Args:
            count: Number of backup codes to generate (default: 6)

        Returns:
            List[str]: List of 8-character alphanumeric backup codes
        """
        backup_codes = []

        for _ in range(count):
            # Generate 8-character alphanumeric code
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(8))
            backup_codes.append(code)

        logger.debug(f"Generated {count} backup codes")
        return backup_codes

    def hash_backup_codes(self, backup_codes: List[str]) -> List[str]:
        """
        Hash backup codes for secure storage.

        Args:
            backup_codes: List of plain-text backup codes

        Returns:
            List[str]: List of bcrypt-hashed backup codes
        """
        hashed_codes = []

        for code in backup_codes:
            # Hash with bcrypt
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(code.encode('utf-8'), salt)
            hashed_codes.append(hashed.decode('utf-8'))

        logger.debug(f"Hashed {len(backup_codes)} backup codes")
        return hashed_codes

    def verify_backup_code(
        self,
        code: str,
        hashed_codes: List[str]
    ) -> Tuple[bool, List[str]]:
        """
        Verify backup code and remove it from available codes (single-use).

        Args:
            code: Plain-text backup code to verify
            hashed_codes: List of bcrypt-hashed backup codes

        Returns:
            Tuple[bool, List[str]]: (is_valid, remaining_hashed_codes)
        """
        try:
            # Check each hashed code
            for i, hashed_code in enumerate(hashed_codes):
                if bcrypt.checkpw(code.encode('utf-8'), hashed_code.encode('utf-8')):
                    # Code is valid - remove it from list (single-use)
                    remaining_codes = hashed_codes[:i] + hashed_codes[i+1:]
                    logger.debug("Backup code verified and consumed")
                    return True, remaining_codes

            # Code not found
            logger.debug("Backup code verification failed: code not found")
            return False, hashed_codes

        except Exception as e:
            logger.error(f"Backup code verification error: {str(e)}", exc_info=True)
            return False, hashed_codes

    def encrypt_secret(self, secret: str) -> str:
        """
        Encrypt TOTP secret for storage at rest.

        Args:
            secret: Plain-text TOTP secret (base32-encoded)

        Returns:
            str: Encrypted secret (Fernet ciphertext)
        """
        try:
            encrypted = self.fernet.encrypt(secret.encode())
            encrypted_str = encrypted.decode()
            logger.debug("TOTP secret encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error(f"Secret encryption failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to encrypt TOTP secret: {str(e)}")

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """
        Decrypt TOTP secret from storage.

        Args:
            encrypted_secret: Encrypted TOTP secret (Fernet ciphertext)

        Returns:
            str: Plain-text TOTP secret (base32-encoded)
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_secret.encode())
            decrypted_str = decrypted.decode()
            logger.debug("TOTP secret decrypted successfully")
            return decrypted_str
        except Exception as e:
            logger.error(f"Secret decryption failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to decrypt TOTP secret: {str(e)}")

    def check_rate_limit(self, user_id: UUID) -> bool:
        """
        Check if user has exceeded 2FA verification rate limit.

        Rate limit: 3 attempts per minute per user.

        Args:
            user_id: User UUID

        Returns:
            bool: True if allowed, False if rate limited
        """
        redis_client = get_redis_client()

        if not redis_client or not redis_client.connected:
            # Redis unavailable - allow attempt (fail open for availability)
            logger.warning("Redis unavailable for 2FA rate limiting - allowing attempt")
            return True

        try:
            rate_limit_key = f"2fa_attempts:{user_id}"

            # Get current attempt count
            attempts = redis_client.client.get(rate_limit_key)
            current_attempts = int(attempts) if attempts else 0

            # Check rate limit (max 3 attempts per minute)
            if current_attempts >= 3:
                logger.warning(f"2FA rate limit exceeded for user {user_id}")
                return False

            # Increment attempt count
            if current_attempts == 0:
                # First attempt - set TTL of 60 seconds
                redis_client.client.setex(rate_limit_key, 60, 1)
            else:
                # Increment existing count
                redis_client.client.incr(rate_limit_key)

            logger.debug(f"2FA attempt {current_attempts + 1}/3 for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}", exc_info=True)
            # Fail open for availability
            return True

    def _get_redis_client(self) -> Optional[RedisManager]:
        """
        Get Redis client for testing.

        Returns:
            RedisManager instance or None
        """
        return get_redis_client()
