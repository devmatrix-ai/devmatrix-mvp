/**
 * LoadingState - Loading indicator component
 *
 * Displays a centered loading spinner with an optional message.
 * Uses glassmorphism styling and purple accent animation.
 *
 * @example
 * ```tsx
 * <LoadingState message="Loading reviews..." />
 * ```
 */

import React from 'react';
import { GlassCard } from '../design-system';

export interface LoadingStateProps {
  /** Optional loading message */
  message?: string;
}

const LoadingState: React.FC<LoadingStateProps> = ({ message = 'Loading...' }) => {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <GlassCard className="text-center py-12 px-8">
        {/* Spinner */}
        <div className="flex justify-center mb-4">
          <div
            className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"
            role="status"
            aria-label="Loading"
          />
        </div>

        {/* Message */}
        <p className="text-gray-300 text-lg">{message}</p>
      </GlassCard>
    </div>
  );
};

export default LoadingState;
