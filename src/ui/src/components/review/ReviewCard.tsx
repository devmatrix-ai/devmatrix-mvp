/**
 * ReviewCard - Individual review item card for review queue
 *
 * Displays review information in a card grid layout with glassmorphism styling.
 * Shows priority, confidence, description, file, issues, status, recommendation, and action button.
 *
 * @example
 * ```tsx
 * <ReviewCard
 *   review={reviewItem}
 *   onClick={() => handleOpenReview(reviewItem)}
 * />
 * ```
 */

import React from 'react';
import { GlassCard, GlassButton, StatusBadge } from '../design-system';
import ConfidenceIndicator from './ConfidenceIndicator';

export interface ReviewCardProps {
  /** Review item data */
  review: {
    review_id: string;
    atom_id: string;
    atom: {
      description: string;
      file_path: string;
    };
    confidence_score: number;
    priority: number;
    status: string;
    ai_analysis: {
      issues_by_severity: {
        critical: number;
        high: number;
        medium: number;
        low: number;
      };
      recommendation: string;
    };
  };
  /** Click handler to open review detail */
  onClick: () => void;
  /** Additional CSS classes */
  className?: string;
}

const ReviewCard: React.FC<ReviewCardProps> = ({ review, onClick, className }) => {
  const { atom, confidence_score, priority, status, ai_analysis } = review;
  const { issues_by_severity, recommendation } = ai_analysis;

  // Determine priority badge status
  const getPriorityStatus = (priorityScore: number): 'error' | 'warning' | 'default' => {
    if (priorityScore >= 75) return 'error';
    if (priorityScore >= 50) return 'warning';
    return 'default';
  };

  // Determine review status badge
  const getStatusVariant = (reviewStatus: string): 'success' | 'warning' | 'info' | 'default' => {
    switch (reviewStatus.toLowerCase()) {
      case 'approved':
        return 'success';
      case 'pending':
        return 'warning';
      case 'in_review':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <div onClick={onClick} className="cursor-pointer">
      <GlassCard hover className={`transition-all ${className || ''}`}>
      {/* Top: Priority + Confidence */}
      <div className="flex items-center justify-between mb-4">
        <StatusBadge status={getPriorityStatus(priority)}>
          Priority {priority}
        </StatusBadge>
        <ConfidenceIndicator score={confidence_score} showLabel={false} size="small" />
      </div>

      {/* Description */}
      <h3 className="text-lg font-medium text-white mb-2 line-clamp-2">
        {atom.description}
      </h3>

      {/* File Path */}
      <p className="text-sm text-gray-400 font-mono mb-4 truncate">
        {atom.file_path}
      </p>

      {/* Issues Summary */}
      <div className="flex gap-2 flex-wrap mb-4">
        {issues_by_severity.critical > 0 && (
          <StatusBadge status="error">
            {issues_by_severity.critical} Critical
          </StatusBadge>
        )}
        {issues_by_severity.high > 0 && (
          <StatusBadge status="error">
            {issues_by_severity.high} High
          </StatusBadge>
        )}
        {issues_by_severity.medium > 0 && (
          <StatusBadge status="warning">
            {issues_by_severity.medium} Medium
          </StatusBadge>
        )}
        {issues_by_severity.low > 0 && (
          <StatusBadge status="info">
            {issues_by_severity.low} Low
          </StatusBadge>
        )}
      </div>

      {/* Status */}
      <div className="mb-3">
        <StatusBadge status={getStatusVariant(status)}>
          Status: {status.toUpperCase()}
        </StatusBadge>
      </div>

      {/* Recommendation */}
      <p className="text-sm font-semibold text-purple-300 mb-4 line-clamp-2">
        Recommendation: {recommendation}
      </p>

      {/* Action Button */}
      <div className="flex justify-end">
        <GlassButton
          variant="primary"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
        >
          View Review →
        </GlassButton>
      </div>
      </GlassCard>
    </div>
  );
};

export default ReviewCard;
