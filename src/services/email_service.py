"""
Email Service

Handles sending transactional emails via SMTP.
Task Group 3.1 - Phase 6: Authentication & Multi-tenancy

Features:
- SMTP email sending in production
- Console logging in development
- HTML email templates
- Email verification emails
- Password reset emails
- Error handling and retries
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from uuid import UUID

from src.config.constants import (
    EMAIL_ENABLED,
    EMAIL_FROM_ADDRESS,
    EMAIL_FROM_NAME,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    SMTP_USE_TLS,
    SMTP_USE_SSL,
    FRONTEND_URL,
)
from src.observability import get_logger

logger = get_logger("email_service")


class EmailService:
    """
    Service for sending transactional emails.

    Supports both production SMTP sending and development console logging.

    Usage:
        service = EmailService()

        # Send verification email
        service.send_verification_email(
            to_email="user@example.com",
            username="john_doe",
            token="550e8400-e29b-41d4-a716-446655440000"
        )

        # Send password reset email
        service.send_password_reset_email(
            to_email="user@example.com",
            username="john_doe",
            token="550e8400-e29b-41d4-a716-446655440000"
        )
    """

    def __init__(self):
        """Initialize email service with configuration."""
        self.enabled = EMAIL_ENABLED
        self.from_address = EMAIL_FROM_ADDRESS
        self.from_name = EMAIL_FROM_NAME
        self.smtp_host = SMTP_HOST
        self.smtp_port = SMTP_PORT
        self.smtp_username = SMTP_USERNAME
        self.smtp_password = SMTP_PASSWORD
        self.smtp_use_tls = SMTP_USE_TLS
        self.smtp_use_ssl = SMTP_USE_SSL
        self.frontend_url = FRONTEND_URL

        if self.enabled:
            logger.info(
                f"Email service enabled: SMTP {self.smtp_host}:{self.smtp_port} "
                f"(TLS: {self.smtp_use_tls}, SSL: {self.smtp_use_ssl})"
            )
        else:
            logger.info("Email service disabled - emails will be logged to console only")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP or log to console.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            html_body: HTML email body
            text_body: Plain text email body (optional fallback)

        Returns:
            True if email sent successfully, False otherwise
        """
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{self.from_name} <{self.from_address}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)

        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)

        # Send email or log to console
        if self.enabled:
            try:
                return self._send_smtp(to_email, msg)
            except Exception as e:
                logger.error(f"Failed to send email to {to_email}: {str(e)}")
                return False
        else:
            # Development mode: log to console
            logger.info(
                f"\n{'='*80}\n"
                f"EMAIL (Development Mode - Not Actually Sent)\n"
                f"{'='*80}\n"
                f"To: {to_email}\n"
                f"From: {msg['From']}\n"
                f"Subject: {subject}\n"
                f"{'-'*80}\n"
                f"{text_body if text_body else 'See HTML body'}\n"
                f"{'='*80}\n"
            )
            return True

    def _send_smtp(self, to_email: str, msg: MIMEMultipart) -> bool:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email
            msg: MIME message to send

        Returns:
            True if sent successfully, False otherwise

        Raises:
            Exception: If SMTP connection or sending fails
        """
        try:
            # Choose SMTP class based on SSL setting
            if self.smtp_use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)

            # Enable TLS if configured (and not using SSL)
            if self.smtp_use_tls and not self.smtp_use_ssl:
                server.starttls()

            # Login if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.sendmail(self.from_address, to_email, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email to {to_email}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending email to {to_email}: {str(e)}")
            raise

    def send_verification_email(
        self,
        to_email: str,
        username: str,
        token: UUID
    ) -> bool:
        """
        Send email verification email.

        Args:
            to_email: User's email address
            username: User's username
            token: Verification token UUID

        Returns:
            True if email sent successfully, False otherwise
        """
        verification_url = f"{self.frontend_url}/verify-email?token={token}"

        subject = "Verify your Devmatrix account"

        # Plain text version
        text_body = f"""
Hello {username},

Welcome to Devmatrix! Please verify your email address by clicking the link below:

{verification_url}

This link will expire in 24 hours.

If you didn't create a Devmatrix account, you can safely ignore this email.

Best regards,
The Devmatrix Team
        """.strip()

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Devmatrix</h1>
    </div>

    <div style="background: #ffffff; padding: 40px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Verify Your Email Address</h2>

        <p>Hello <strong>{username}</strong>,</p>

        <p>Welcome to Devmatrix! To complete your registration, please verify your email address by clicking the button below:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}"
               style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                      color: white;
                      padding: 14px 40px;
                      text-decoration: none;
                      border-radius: 5px;
                      font-weight: bold;
                      display: inline-block;">
                Verify Email Address
            </a>
        </div>

        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
        </p>

        <p style="color: #999; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
            <strong>Note:</strong> This verification link will expire in 24 hours.
        </p>

        <p style="color: #999; font-size: 13px;">
            If you didn't create a Devmatrix account, you can safely ignore this email.
        </p>
    </div>

    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
        <p>© 2024 Devmatrix. All rights reserved.</p>
    </div>
</body>
</html>
        """.strip()

        logger.info(f"Sending verification email to {to_email}")
        return self.send_email(to_email, subject, html_body, text_body)

    def send_password_reset_email(
        self,
        to_email: str,
        username: str,
        token: UUID
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: User's email address
            username: User's username
            token: Password reset token UUID

        Returns:
            True if email sent successfully, False otherwise
        """
        reset_url = f"{self.frontend_url}/reset-password?token={token}"

        subject = "Reset your Devmatrix password"

        # Plain text version
        text_body = f"""
Hello {username},

We received a request to reset your Devmatrix password. Click the link below to create a new password:

{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

Best regards,
The Devmatrix Team
        """.strip()

        # HTML version
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
        <h1 style="color: white; margin: 0; font-size: 28px;">Devmatrix</h1>
    </div>

    <div style="background: #ffffff; padding: 40px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 10px 10px;">
        <h2 style="color: #333; margin-top: 0;">Reset Your Password</h2>

        <p>Hello <strong>{username}</strong>,</p>

        <p>We received a request to reset your Devmatrix password. Click the button below to create a new password:</p>

        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                      color: white;
                      padding: 14px 40px;
                      text-decoration: none;
                      border-radius: 5px;
                      font-weight: bold;
                      display: inline-block;">
                Reset Password
            </a>
        </div>

        <p style="color: #666; font-size: 14px;">
            Or copy and paste this link into your browser:<br>
            <a href="{reset_url}" style="color: #667eea; word-break: break-all;">{reset_url}</a>
        </p>

        <p style="color: #999; font-size: 13px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
            <strong>Security Note:</strong> This password reset link will expire in 1 hour for your security.
        </p>

        <p style="color: #999; font-size: 13px;">
            If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.
        </p>
    </div>

    <div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">
        <p>© 2024 Devmatrix. All rights reserved.</p>
    </div>
</body>
</html>
        """.strip()

        logger.info(f"Sending password reset email to {to_email}")
        return self.send_email(to_email, subject, html_body, text_body)
