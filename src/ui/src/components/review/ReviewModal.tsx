/**
 * ReviewModal - Full-screen modal for review detail
 *
 * Displays code diff viewer, AI suggestions panel, and review actions
 * in a responsive two-column layout (desktop) or stacked layout (mobile).
 *
 * @example
 * ```tsx
 * <ReviewModal
 *   review={selectedReview}
 *   open={modalOpen}
 *   onClose={() => setModalOpen(false)}
 *   onActionComplete={() => refreshReviews()}
 * />
 * ```
 */

import React, { useEffect, useCallback } from 'react';
import { FiX } from 'react-icons/fi';
import { GlassCard, GlassButton } from '../design-system';
import CodeDiffViewer from './CodeDiffViewer';
import AISuggestionsPanel from './AISuggestionsPanel';
import ReviewActions from './ReviewActions';

export interface ReviewModalProps {
  /** Review item to display (null when closed) */
  review: {
    review_id: string;
    atom_id: string;
    confidence_score: number;
    atom: {
      description: string;
      code: string;
      language: string;
      file_path: string;
    };
    ai_analysis: {
      total_issues: number;
      issues_by_severity: {
        critical: number;
        high: number;
        medium: number;
        low: number;
      };
      issues: Array<{
        type: string;
        severity: string;
        description: string;
        line_number: number | null;
        code_snippet: string | null;
        explanation: string;
      }>;
      suggestions: any;
      alternatives: string[];
      recommendation: string;
    };
  } | null;
  /** Whether modal is open */
  open: boolean;
  /** Close handler */
  onClose: () => void;
  /** Callback after review action is completed */
  onActionComplete: () => void;
}

const ReviewModal: React.FC<ReviewModalProps> = ({
  review,
  open,
  onClose,
  onActionComplete,
}) => {
  // Handle escape key
  const handleEscapeKey = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape' && open) {
        onClose();
      }
    },
    [open, onClose]
  );

  // Setup keyboard listeners
  useEffect(() => {
    if (open) {
      document.addEventListener('keydown', handleEscapeKey);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'unset';
    };
  }, [open, handleEscapeKey]);

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!open || !review) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-modal-title"
    >
      <GlassCard className="w-11/12 md:w-5/6 lg:w-4/5 xl:w-3/4 max-w-7xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <h2 id="review-modal-title" className="text-2xl font-bold text-white">
            Review: {review.atom.description}
          </h2>
          <GlassButton
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close modal"
          >
            <FiX size={24} />
          </GlassButton>
        </div>

        {/* Body - Two-column layout */}
        <div className="flex-1 overflow-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full">
            {/* Code Diff Viewer - 2 columns on desktop */}
            <div className="lg:col-span-2 min-h-[400px]">
              <CodeDiffViewer
                code={review.atom.code}
                language={review.atom.language}
                issues={review.ai_analysis.issues}
              />
            </div>

            {/* AI Suggestions Panel - 1 column on desktop */}
            <div className="lg:col-span-1 min-h-[400px]">
              <AISuggestionsPanel
                analysis={review.ai_analysis}
                confidenceScore={review.confidence_score}
              />
            </div>
          </div>
        </div>

        {/* Footer - Actions */}
        <div className="p-6 border-t border-white/10">
          <ReviewActions
            reviewId={review.review_id}
            atomId={review.atom_id}
            currentCode={review.atom.code}
            onActionComplete={() => {
              onActionComplete();
              onClose();
            }}
          />
        </div>
      </GlassCard>
    </div>
  );
};

export default ReviewModal;
