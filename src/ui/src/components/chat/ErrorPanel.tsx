/**
 * ErrorPanel - Display error state during MasterPlan generation
 *
 * Shows error message and provides retry functionality
 */

import React from 'react';

interface ErrorPanelProps {
  error?: {
    message: string;
    code?: string;
    details?: Record<string, any>;
  };
  onRetry?: () => void;
  isRetrying?: boolean;
}

const ErrorPanel: React.FC<ErrorPanelProps> = ({
  error,
  onRetry,
  isRetrying = false,
}) => {
  return (
    <div className="space-y-4">
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
        <div className="flex items-start gap-4">
          <div className="text-3xl">❌</div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-400 mb-2">Generation Failed</h3>
            <p className="text-sm text-gray-300 mb-4">
              {error?.message || 'An unexpected error occurred during MasterPlan generation.'}
            </p>
            {error?.code && (
              <div className="text-xs text-gray-400 mb-4">
                Error Code: <code className="bg-black/30 px-2 py-1 rounded">{error.code}</code>
              </div>
            )}
            {error?.details && Object.keys(error.details).length > 0 && (
              <div className="bg-black/30 rounded p-3 mb-4 max-h-32 overflow-auto">
                <pre className="text-xs text-gray-400 whitespace-pre-wrap">
                  {JSON.stringify(error.details, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>

      {onRetry && (
        <button
          onClick={onRetry}
          disabled={isRetrying}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white font-medium py-2 px-4 rounded-lg transition-colors"
        >
          {isRetrying ? 'Retrying...' : 'Retry Generation'}
        </button>
      )}
    </div>
  );
};

export default ErrorPanel;
