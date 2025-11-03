"""
Tests for SharingService

Tests conversation sharing and collaboration functionality.

Author: DevMatrix Team
Date: 2025-11-03
"""

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from datetime import datetime


@pytest.mark.unit
class TestSharingServiceShare:
    """Test conversation sharing functionality."""

    def test_share_conversation_success(self):
        """Test successful conversation sharing."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        conv_id = uuid4()
        
        with patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_find_user_by_email', return_value=uuid4()), \
             patch.object(service, '_create_share', return_value=MagicMock()):
            
            result = service.share_conversation(
                conversation_id=conv_id,
                shared_with_email="recipient@example.com",
                permission_level="view",
                shared_by_user_id=uuid4()
            )
            
            assert result is not None

    def test_share_conversation_not_owner(self):
        """Test sharing when not the owner."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_check_ownership', return_value=False):
            with pytest.raises(PermissionError, match="owner"):
                service.share_conversation(
                    conversation_id=uuid4(),
                    shared_with_email="user@example.com",
                    permission_level="view",
                    shared_by_user_id=uuid4()
                )

    def test_share_conversation_recipient_not_found(self):
        """Test sharing with non-existent recipient."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_find_user_by_email', return_value=None):
            
            with pytest.raises(ValueError, match="not found|User"):
                service.share_conversation(
                    conversation_id=uuid4(),
                    shared_with_email="nonexistent@example.com",
                    permission_level="view",
                    shared_by_user_id=uuid4()
                )

    def test_share_conversation_already_shared(self):
        """Test sharing conversation already shared with user."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_find_user_by_email', return_value=uuid4()), \
             patch.object(service, '_check_existing_share', return_value=True):
            
            with pytest.raises(ValueError, match="already shared"):
                service.share_conversation(
                    conversation_id=uuid4(),
                    shared_with_email="user@example.com",
                    permission_level="view",
                    shared_by_user_id=uuid4()
                )

    def test_share_invalid_permission_level(self):
        """Test sharing with invalid permission level."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_find_user_by_email', return_value=uuid4()), \
             patch.object(service, '_validate_permission', side_effect=ValueError("Invalid permission")):
            
            with pytest.raises(ValueError, match="permission"):
                service.share_conversation(
                    conversation_id=uuid4(),
                    shared_with_email="user@example.com",
                    permission_level="invalid",
                    shared_by_user_id=uuid4()
                )


@pytest.mark.unit
class TestSharingServiceList:
    """Test listing shares functionality."""

    def test_list_conversation_shares_success(self):
        """Test successful listing of shares."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        mock_shares = [
            MagicMock(share_id=uuid4(), permission_level="view"),
            MagicMock(share_id=uuid4(), permission_level="edit")
        ]
        
        with patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_get_shares', return_value=mock_shares):
            
            shares = service.list_conversation_shares(uuid4(), uuid4())
            
            assert len(shares) == 2

    def test_list_shares_not_owner(self):
        """Test listing shares when not owner."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_check_ownership', return_value=False):
            with pytest.raises(PermissionError):
                service.list_conversation_shares(uuid4(), uuid4())

    def test_list_shared_with_user(self):
        """Test listing conversations shared with user."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        mock_shared = [
            {
                "conversation": MagicMock(),
                "permission_level": "view",
                "shared_at": datetime.now(),
                "shared_by": uuid4()
            }
        ]
        
        with patch.object(service, '_get_shared_with_user', return_value=mock_shared):
            result = service.list_shared_with_user(uuid4())
            
            assert len(result) == 1


@pytest.mark.unit
class TestSharingServiceUpdate:
    """Test updating share permissions."""

    def test_update_share_permission_success(self):
        """Test successful permission update."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        mock_share = MagicMock()
        mock_share.permission_level = "view"
        
        with patch.object(service, '_get_share', return_value=mock_share), \
             patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_update_permission', return_value=mock_share):
            
            result = service.update_share_permission(
                share_id=uuid4(),
                new_permission_level="edit",
                user_id=uuid4()
            )
            
            assert result is not None

    def test_update_share_not_found(self):
        """Test updating non-existent share."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_get_share', return_value=None):
            with pytest.raises(ValueError, match="not found"):
                service.update_share_permission(uuid4(), "edit", uuid4())


@pytest.mark.unit
class TestSharingServiceRevoke:
    """Test revoking shares."""

    def test_revoke_share_success(self):
        """Test successful share revocation."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_get_share', return_value=MagicMock()), \
             patch.object(service, '_check_ownership', return_value=True), \
             patch.object(service, '_delete_share', return_value=True):
            
            result = service.revoke_share(uuid4(), uuid4())
            
            assert result is True or result is None

    def test_revoke_share_not_owner(self):
        """Test revoking share when not owner."""
        from src.services.sharing_service import SharingService

        service = SharingService()
        
        with patch.object(service, '_get_share', return_value=MagicMock()), \
             patch.object(service, '_check_ownership', return_value=False):
            
            with pytest.raises(PermissionError):
                service.revoke_share(uuid4(), uuid4())

