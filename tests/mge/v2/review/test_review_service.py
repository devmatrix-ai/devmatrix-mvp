"""
Tests for ReviewService

Verifies review workflow orchestration (approve, reject, edit, regenerate).
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

from src.mge.v2.review.review_service import ReviewService, ReviewDecision, ReviewResult
from src.mge.v2.review.review_queue_manager import ReviewStatus
from src.models.atomic_unit import AtomicUnit


@pytest.fixture
def db_session():
    """Mock database session"""
    session = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    return session


@pytest.fixture
def review_service(db_session):
    """Create ReviewService instance"""
    return ReviewService(db_session)


@pytest.fixture
def mock_atom(db_session):
    """Create mock AtomicUnit"""
    atom = MagicMock(spec=AtomicUnit)
    atom.id = uuid4()
    atom.masterplan_id = uuid4()
    atom.phase_number = 3
    atom.code = "def hello(): return 'world'"
    atom.status = "generated"
    atom.retry_count = 0
    atom.validation_l1 = False
    atom.validation_l2 = True
    atom.validation_l3 = True
    atom.validation_l4 = True
    
    # Mock query to return this atom
    db_session.query.return_value.filter.return_value.first.return_value = atom
    
    return atom


class TestReviewService:
    """Test ReviewService functionality"""

    @pytest.mark.asyncio
    async def test_approve_workflow(self, review_service, mock_atom, db_session):
        """Test approve workflow"""
        # Add atom to queue first
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        
        # Mock update_status to return review item
        mock_review_item = MagicMock()
        review_service.queue_manager.update_status = MagicMock(return_value=mock_review_item)
        review_service.queue_manager.remove_from_queue = MagicMock(return_value=True)
        
        # Approve
        result = await review_service.approve(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            notes="Looks good"
        )
        
        assert result.success is True
        assert mock_atom.review_status == "approved"
        assert mock_atom.reviewed_by == "reviewer@example.com"
        assert "approved successfully" in result.message

    @pytest.mark.asyncio
    async def test_approve_atom_not_found(self, review_service, db_session):
        """Test approve with non-existent atom"""
        # Mock query to return None
        db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = await review_service.approve(
            atom_id=uuid4(),
            reviewer="reviewer@example.com"
        )
        
        assert result.success is False
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_reject_workflow(self, review_service, mock_atom):
        """Test reject workflow with AI suggestions"""
        # Add to queue
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        
        # Mock update_status
        review_service.queue_manager.update_status = MagicMock(return_value=MagicMock())
        
        # Reject
        result = await review_service.reject(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            feedback="Fix syntax errors",
            provide_suggestions=True
        )
        
        assert result.success is True
        assert mock_atom.review_status == "rejected"
        assert mock_atom.review_feedback == "Fix syntax errors"
        assert result.ai_suggestions is not None  # Should include AI suggestions

    @pytest.mark.asyncio
    async def test_reject_without_suggestions(self, review_service, mock_atom):
        """Test reject workflow without AI suggestions"""
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        review_service.queue_manager.update_status = MagicMock(return_value=MagicMock())
        
        result = await review_service.reject(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            feedback="Fix errors",
            provide_suggestions=False
        )
        
        assert result.success is True
        assert len(result.ai_suggestions) == 0

    @pytest.mark.asyncio
    async def test_edit_workflow(self, review_service, mock_atom):
        """Test manual code edit workflow"""
        # Add to queue
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        review_service.queue_manager.update_status = MagicMock(return_value=MagicMock())
        review_service.queue_manager.remove_from_queue = MagicMock(return_value=True)
        
        original_code = mock_atom.code
        new_code = "def hello():\n    return 'world'"
        
        # Edit code
        result = await review_service.edit(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            new_code=new_code,
            edit_notes="Fixed indentation"
        )
        
        assert result.success is True
        assert mock_atom.code == new_code
        assert mock_atom.edited_by == "reviewer@example.com"
        assert mock_atom.edit_notes == "Fixed indentation"
        assert result.new_confidence_score is not None

    @pytest.mark.asyncio
    async def test_regenerate_workflow(self, review_service, mock_atom):
        """Test regeneration request workflow"""
        # Add to queue
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        review_service.queue_manager.update_status = MagicMock(return_value=MagicMock())
        
        # Regenerate
        result = await review_service.regenerate(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            feedback="Use list comprehension instead of loop"
        )
        
        assert result.success is True
        assert mock_atom.status == "pending_regeneration"
        assert mock_atom.review_feedback == "Use list comprehension instead of loop"
        assert mock_atom.retry_count == 1
        assert result.ai_suggestions is not None

    @pytest.mark.asyncio
    async def test_regenerate_max_retries_exceeded(self, review_service, mock_atom):
        """Test regeneration with max retries exceeded"""
        mock_atom.retry_count = 3
        
        review_service.queue_manager.add_to_queue(
            mock_atom,
            MagicMock(total_score=45.0),
            None
        )
        
        result = await review_service.regenerate(
            atom_id=mock_atom.id,
            reviewer="reviewer@example.com",
            feedback="Try again",
            max_retries=3
        )
        
        assert result.success is False
        assert "Maximum retries" in result.message

    def test_review_decision_creation(self):
        """Test ReviewDecision dataclass"""
        atom_id = uuid4()
        
        decision = ReviewDecision(
            atom_id=atom_id,
            decision="approve",
            reviewer="alice@example.com",
            feedback="Good work"
        )
        
        assert decision.atom_id == atom_id
        assert decision.decision == "approve"
        assert decision.reviewer == "alice@example.com"
        assert decision.feedback == "Good work"
        assert decision.timestamp is not None

    def test_review_decision_to_dict(self):
        """Test ReviewDecision serialization"""
        decision = ReviewDecision(
            atom_id=uuid4(),
            decision="reject",
            reviewer="bob@example.com",
            feedback="Needs work",
            code_changes="fixed version"
        )
        
        decision_dict = decision.to_dict()
        
        assert "atom_id" in decision_dict
        assert decision_dict["decision"] == "reject"
        assert decision_dict["reviewer"] == "bob@example.com"
        assert decision_dict["feedback"] == "Needs work"
        assert decision_dict["code_changes"] == "fixed version"

    def test_review_result_creation(self):
        """Test ReviewResult dataclass"""
        result = ReviewResult(
            success=True,
            message="Operation successful"
        )
        
        assert result.success is True
        assert result.message == "Operation successful"
        assert result.updated_atom is None
        assert result.new_confidence_score is None

    def test_review_result_to_dict(self):
        """Test ReviewResult serialization"""
        result = ReviewResult(
            success=True,
            message="Test message",
            ai_suggestions=[]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["message"] == "Test message"
        assert "updated_atom_id" in result_dict
        assert "ai_suggestions" in result_dict
