/**
 * ReviewActions - Review action buttons (approve, reject, edit, regenerate)
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import { GlassButton } from '../design-system/GlassButton';
import { GlassInput } from '../design-system/GlassInput';
import { GlassCard } from '../design-system/GlassCard';
import { CustomAlert } from './CustomAlert';
import LoadingState from './LoadingState';
import {
  FiCheckCircle,
  FiXCircle,
  FiEdit2,
  FiRefreshCw,
  FiX,
} from 'react-icons/fi';

interface ReviewActionsProps {
  reviewId: string;
  atomId: string;
  currentCode: string;
  onActionComplete: () => void;
}

const ReviewActions: React.FC<ReviewActionsProps> = ({
  reviewId,
  atomId: _atomId,
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
    <div>
      {/* Action Buttons */}
      <div className="flex gap-2 mb-4">
        <GlassButton variant="primary" onClick={handleApprove} disabled={loading}>
          <FiCheckCircle className="inline mr-2" size={16} />
          Approve
        </GlassButton>

        <GlassButton variant="ghost" onClick={() => setRejectDialogOpen(true)} disabled={loading}>
          <FiXCircle className="inline mr-2 text-red-400" size={16} />
          Reject
        </GlassButton>

        <GlassButton variant="ghost" onClick={() => setEditDialogOpen(true)} disabled={loading}>
          <FiEdit2 className="inline mr-2" size={16} />
          Edit Code
        </GlassButton>

        <GlassButton variant="ghost" onClick={() => setRegenerateDialogOpen(true)} disabled={loading}>
          <FiRefreshCw className="inline mr-2 text-amber-400" size={16} />
          Regenerate
        </GlassButton>
      </div>

      {/* Status Messages */}
      {loading && <LoadingState message="Processing..." />}

      {error && (
        <div className="mb-4">
          <CustomAlert severity="error" message={error} onClose={() => setError(null)} />
        </div>
      )}

      {success && (
        <div className="mb-4">
          <CustomAlert severity="success" message={success} onClose={() => setSuccess(null)} />
        </div>
      )}

      {/* Reject Dialog */}
      {rejectDialogOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setRejectDialogOpen(false)}
        >
          <div className="w-full max-w-md" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <GlassCard>
            {/* Header */}
            <div className="border-b border-white/10 p-4 flex justify-between items-center">
              <h3 className="text-lg font-bold text-white">Reject Atom</h3>
              <button
                onClick={() => setRejectDialogOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <FiX size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4">
              <GlassInput
                multiline
                rows={4}
                placeholder="Explain why this code is being rejected..."
                value={rejectFeedback}
                onChange={(e) => setRejectFeedback(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="border-t border-white/10 p-4 flex justify-end gap-2">
              <GlassButton variant="ghost" onClick={() => setRejectDialogOpen(false)}>
                Cancel
              </GlassButton>
              <GlassButton variant="primary" onClick={handleReject} disabled={loading}>
                Reject
              </GlassButton>
            </div>
          </GlassCard>
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      {editDialogOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setEditDialogOpen(false)}
        >
          <div className="w-full max-w-2xl" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <GlassCard>
            {/* Header */}
            <div className="border-b border-white/10 p-4 flex justify-between items-center">
              <h3 className="text-lg font-bold text-white">Edit Code</h3>
              <button
                onClick={() => setEditDialogOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <FiX size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              <GlassInput
                multiline
                rows={15}
                placeholder="Code..."
                value={editedCode}
                onChange={(e) => setEditedCode(e.target.value)}
                className="font-mono text-sm"
              />
              <GlassInput
                multiline
                rows={2}
                placeholder="Describe the changes made... (optional)"
                value={editFeedback}
                onChange={(e) => setEditFeedback(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="border-t border-white/10 p-4 flex justify-end gap-2">
              <GlassButton variant="ghost" onClick={() => setEditDialogOpen(false)}>
                Cancel
              </GlassButton>
              <GlassButton variant="primary" onClick={handleEdit} disabled={loading}>
                Save Changes
              </GlassButton>
            </div>
          </GlassCard>
          </div>
        </div>
      )}

      {/* Regenerate Dialog */}
      {regenerateDialogOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setRegenerateDialogOpen(false)}
        >
          <div className="w-full max-w-md" onClick={(e: React.MouseEvent) => e.stopPropagation()}>
          <GlassCard>
            {/* Header */}
            <div className="border-b border-white/10 p-4 flex justify-between items-center">
              <h3 className="text-lg font-bold text-white">Request Regeneration</h3>
              <button
                onClick={() => setRegenerateDialogOpen(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <FiX size={20} />
              </button>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              <CustomAlert
                severity="info"
                message="The AI will regenerate this code using your feedback as instructions."
              />
              <GlassInput
                multiline
                rows={4}
                placeholder="What should be changed in the regenerated code?"
                value={regenerateFeedback}
                onChange={(e) => setRegenerateFeedback(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="border-t border-white/10 p-4 flex justify-end gap-2">
              <GlassButton variant="ghost" onClick={() => setRegenerateDialogOpen(false)}>
                Cancel
              </GlassButton>
              <GlassButton variant="primary" onClick={handleRegenerate} disabled={loading}>
                Request Regeneration
              </GlassButton>
            </div>
          </GlassCard>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReviewActions;
