/**
 * ReviewActions - Review action buttons (approve, reject, edit, regenerate)
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Edit as EditIcon,
  Refresh as RegenerateIcon,
} from '@mui/icons-material';

interface ReviewActionsProps {
  reviewId: string;
  atomId: string;
  currentCode: string;
  onActionComplete: () => void;
}

const ReviewActions: React.FC<ReviewActionsProps> = ({
  reviewId,
  atomId,
  currentCode,
  onActionComplete,
}) => {
  // State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Dialog states
  const [rejectDialogOpen, setRejectDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);

  // Form states
  const [rejectFeedback, setRejectFeedback] = useState('');
  const [editedCode, setEditedCode] = useState(currentCode);
  const [editFeedback, setEditFeedback] = useState('');
  const [regenerateFeedback, setRegenerateFeedback] = useState('');

  // Get current user ID (from auth context)
  const getCurrentUserId = (): string => {
    // TODO: Get from auth context
    return 'reviewer-001';
  };

  // Handle approve
  const handleApprove = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v2/review/approve?review_id=${reviewId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: getCurrentUserId(),
          feedback: 'Approved - code meets quality standards',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to approve atom');
      }

      setSuccess('Atom approved successfully!');
      setTimeout(() => onActionComplete(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Handle reject
  const handleReject = async () => {
    if (!rejectFeedback.trim()) {
      setError('Feedback is required for rejection');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v2/review/reject?review_id=${reviewId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: getCurrentUserId(),
          feedback: rejectFeedback,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to reject atom');
      }

      setSuccess('Atom rejected - marked for regeneration');
      setRejectDialogOpen(false);
      setTimeout(() => onActionComplete(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Handle edit
  const handleEdit = async () => {
    if (!editedCode.trim()) {
      setError('Code cannot be empty');
      return;
    }

    if (editedCode === currentCode) {
      setError('No changes detected');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v2/review/edit?review_id=${reviewId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: getCurrentUserId(),
          new_code: editedCode,
          feedback: editFeedback || 'Code manually edited by reviewer',
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to edit atom');
      }

      setSuccess('Code updated successfully!');
      setEditDialogOpen(false);
      setTimeout(() => onActionComplete(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Handle regenerate
  const handleRegenerate = async () => {
    if (!regenerateFeedback.trim()) {
      setError('Feedback is required for regeneration');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v2/review/regenerate?review_id=${reviewId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_id: getCurrentUserId(),
          feedback: regenerateFeedback,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to request regeneration');
      }

      setSuccess('Regeneration requested - atom will be regenerated with your feedback');
      setRegenerateDialogOpen(false);
      setTimeout(() => onActionComplete(), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <Button
          variant="contained"
          color="success"
          startIcon={<ApproveIcon />}
          onClick={handleApprove}
          disabled={loading}
        >
          Approve
        </Button>

        <Button
          variant="outlined"
          color="error"
          startIcon={<RejectIcon />}
          onClick={() => setRejectDialogOpen(true)}
          disabled={loading}
        >
          Reject
        </Button>

        <Button
          variant="outlined"
          color="primary"
          startIcon={<EditIcon />}
          onClick={() => setEditDialogOpen(true)}
          disabled={loading}
        >
          Edit Code
        </Button>

        <Button
          variant="outlined"
          color="warning"
          startIcon={<RegenerateIcon />}
          onClick={() => setRegenerateDialogOpen(true)}
          disabled={loading}
        >
          Regenerate
        </Button>
      </Box>

      {/* Status Messages */}
      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={20} />
          <Alert severity="info">Processing...</Alert>
        </Box>
      )}

      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Reject Dialog */}
      <Dialog open={rejectDialogOpen} onClose={() => setRejectDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Reject Atom</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Rejection Feedback (Required)"
            placeholder="Explain why this code is being rejected..."
            value={rejectFeedback}
            onChange={(e) => setRejectFeedback(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRejectDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleReject} variant="contained" color="error" disabled={loading}>
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Edit Code</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            multiline
            rows={15}
            label="Code"
            value={editedCode}
            onChange={(e) => setEditedCode(e.target.value)}
            sx={{ mt: 2, fontFamily: 'monospace' }}
            InputProps={{
              style: { fontFamily: 'monospace', fontSize: '0.9rem' },
            }}
          />
          <TextField
            fullWidth
            multiline
            rows={2}
            label="Edit Notes (Optional)"
            placeholder="Describe the changes made..."
            value={editFeedback}
            onChange={(e) => setEditFeedback(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleEdit} variant="contained" color="primary" disabled={loading}>
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Regenerate Dialog */}
      <Dialog open={regenerateDialogOpen} onClose={() => setRegenerateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Request Regeneration</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            The AI will regenerate this code using your feedback as instructions.
          </Alert>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Regeneration Instructions (Required)"
            placeholder="What should be changed in the regenerated code?"
            value={regenerateFeedback}
            onChange={(e) => setRegenerateFeedback(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRegenerate} variant="contained" color="warning" disabled={loading}>
            Request Regeneration
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReviewActions;
