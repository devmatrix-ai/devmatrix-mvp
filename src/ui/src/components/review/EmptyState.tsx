/**
 * EmptyState - Empty state component
 *
 * Displays a centered message when no results are found.
 * Shows an icon, message, and optional action button.
 *
 * @example
 * ```tsx
 * <EmptyState
 *   icon="📭"
 *   message="No reviews found"
 *   action={{
 *     label: "Refresh",
 *     onClick: handleRefresh
 *   }}
 * />
 * ```
 */

import React from 'react';
import { GlassCard, GlassButton } from '../design-system';

export interface EmptyStateProps {
  /** Message to display */
  message: string;
  /** Optional emoji or icon */
  icon?: string;
  /** Optional action button */
  action?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyState: React.FC<EmptyStateProps> = ({
  message,
  icon = '📭',
  action,
}) => {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <GlassCard className="text-center py-12 px-8 max-w-md">
        {/* Icon */}
        <div className="text-5xl mb-4">{icon}</div>

        {/* Message */}
        <p className="text-xl text-gray-300 mb-6">{message}</p>

        {/* Action Button */}
        {action && (
          <GlassButton
            variant="secondary"
            onClick={action.onClick}
          >
            {action.label}
          </GlassButton>
        )}
      </GlassCard>
    </div>
  );
};

export default EmptyState;
