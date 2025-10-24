/**
 * ErrorState - Error display component
 *
 * Displays an error message with a retry button.
 * Uses red accent colors and glassmorphism styling.
 *
 * @example
 * ```tsx
 * <ErrorState
 *   error="Failed to load reviews"
 *   onRetry={handleRetry}
 * />
 * ```
 */

import React from 'react';
import { FiAlertCircle } from 'react-icons/fi';
import { GlassCard, GlassButton } from '../design-system';

export interface ErrorStateProps {
  /** Error message to display */
  error: string;
  /** Optional retry callback */
  onRetry?: () => void;
}

const ErrorState: React.FC<ErrorStateProps> = ({ error, onRetry }) => {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <GlassCard className="text-center py-12 px-8 max-w-md border-red-500/50">
        {/* Error Icon */}
        <div className="flex justify-center mb-4">
          <FiAlertCircle className="text-red-400 text-5xl" />
        </div>

        {/* Error Message */}
        <p className="text-xl text-red-400 mb-6">{error}</p>

        {/* Retry Button */}
        {onRetry && (
          <GlassButton variant="secondary" onClick={onRetry}>
            Retry
          </GlassButton>
        )}
      </GlassCard>
    </div>
  );
};

export default ErrorState;
