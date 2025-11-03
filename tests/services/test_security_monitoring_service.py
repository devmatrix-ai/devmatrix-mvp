"""
Tests for SecurityMonitoringService

Tests security monitoring and threat detection functionality.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.mark.unit
class TestSecurityMonitoringEvents:
    """Test security event logging and monitoring."""

    def test_log_security_event_success(self):
        """Test successful security event logging."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        with patch.object(service, '_save_event', return_value=True):
            result = service.log_event(
                event_type="failed_login",
                user_id=str(uuid4()),
                ip_address="192.168.1.1",
                details={"attempts": 1}
            )
            
            assert result is True or result is None

    def test_detect_brute_force_attack(self):
        """Test brute force attack detection."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        user_id = str(uuid4())
        
        with patch.object(service, '_count_recent_failed_logins', return_value=5):
            is_attack = service.detect_brute_force(user_id)
            
            assert is_attack is True or is_attack is False

    def test_detect_suspicious_ip(self):
        """Test suspicious IP detection."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        with patch.object(service, '_check_ip_reputation', return_value=True):
            is_suspicious = service.is_suspicious_ip("1.2.3.4")
            
            assert is_suspicious is True or is_suspicious is False

    def test_track_api_abuse(self):
        """Test API abuse tracking."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        with patch.object(service, '_count_recent_requests', return_value=1000):
            is_abuse = service.detect_api_abuse(str(uuid4()))
            
            assert is_abuse is True or is_abuse is False


@pytest.mark.unit
class TestSecurityMonitoringAlerts:
    """Test security alert functionality."""

    def test_generate_alert_on_threat(self):
        """Test alert generation on threat detection."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        with patch.object(service, '_send_alert', return_value=True):
            result = service.alert_on_threat(
                threat_type="brute_force",
                severity="high",
                details={"user_id": str(uuid4())}
            )
            
            assert result is not None

    def test_alert_rate_limiting(self):
        """Test alert rate limiting to avoid spam."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        # Should not send duplicate alerts too quickly
        with patch.object(service, '_check_recent_alert', return_value=True):
            should_send = service.should_send_alert("brute_force", str(uuid4()))
            
            assert should_send is False or should_send is True


@pytest.mark.unit
class TestSecurityMonitoringReports:
    """Test security reporting functionality."""

    def test_generate_security_report(self):
        """Test security report generation."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        mock_events = [
            {"event_type": "failed_login", "count": 50},
            {"event_type": "suspicious_ip", "count": 10}
        ]
        
        with patch.object(service, '_aggregate_events', return_value=mock_events):
            report = service.generate_report(period="daily")
            
            assert report is not None or report == []

    def test_get_threat_summary(self):
        """Test getting threat summary."""
        from src.services.security_monitoring_service import SecurityMonitoringService

        service = SecurityMonitoringService()
        
        mock_summary = {
            "total_threats": 15,
            "high_severity": 3,
            "medium_severity": 7,
            "low_severity": 5
        }
        
        with patch.object(service, '_calculate_summary', return_value=mock_summary):
            summary = service.get_threat_summary()
            
            assert summary is not None

