/**
 * ErrorPanel - Display errors with diagnostics and retry mechanism
 *
 * Shows generation errors with:
 * - Error message and code
 * - Expandable details section
 * - Stack trace (debugging)
 * - Retry button with loading state
 *
 * @example
 * ```tsx
 * <ErrorPanel
 *   error={{
 *     message: 'Generation failed',
 *     code: 'LLM_API_ERROR',
 *     details: { status: 503 },
 *     stackTrace: '...'
 *   }}
 *   onRetry={handleRetry}
 *   isRetrying={false}
 * />
 * ```
 */

import React, { useState } from 'react';
import { FiAlertTriangle, FiChevronDown, FiChevronUp, FiRefreshCw } from 'react-icons/fi';
import { GlassCard, GlassButton } from '../design-system';
import { useTranslation } from '../../i18n';
import type { ErrorPanelProps } from '../../types/masterplan';

/**
 * ErrorPanel component
 */
const ErrorPanel: React.FC<ErrorPanelProps> = ({
  error,
  onRetry,
  isRetrying,
}) => {
  const { t } = useTranslation();
  const [detailsExpanded, setDetailsExpanded] = useState(false);
  const [stackExpanded, setStackExpanded] = useState(false);

  return (
    <GlassCard className="border-red-500/50 bg-red-900/10">
      {/* Error Header */}
      <div className="flex items-start gap-4">
        <div className="flex-shrink-0">
          <FiAlertTriangle className="text-red-500" size={32} />
        </div>
        <div className="flex-1">
          <h3 className="text-xl font-bold text-red-400 mb-2">
            {t('masterplan.errors.title')}
          </h3>
          <p className="text-white font-semibold mb-1">
            {error.message}
          </p>
          <p className="text-sm text-gray-400">
            {t('masterplan.errors.code')}: <span className="font-mono text-gray-300">{error.code}</span>
          </p>
        </div>
      </div>

      {/* Error Details - Expandable */}
      {error.details && Object.keys(error.details).length > 0 && (
        <div className="mt-4">
          <button
            className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors"
            onClick={() => setDetailsExpanded(!detailsExpanded)}
            aria-expanded={detailsExpanded}
            aria-controls="error-details"
          >
            <span className="font-semibold">{t('masterplan.errors.details')}</span>
            {detailsExpanded ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
          </button>

          {detailsExpanded && (
            <div
              id="error-details"
              className="mt-3 bg-black/30 rounded-lg p-4 max-h-48 overflow-auto"
            >
              <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                {JSON.stringify(error.details, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Stack Trace - Expandable (debugging) */}
      {error.stackTrace && (
        <div className="mt-4">
          <button
            className="flex items-center gap-2 text-gray-300 hover:text-white transition-colors"
            onClick={() => setStackExpanded(!stackExpanded)}
            aria-expanded={stackExpanded}
            aria-controls="error-stack"
          >
            <span className="font-semibold">{t('masterplan.errors.stackTrace')}</span>
            {stackExpanded ? <FiChevronUp size={18} /> : <FiChevronDown size={18} />}
          </button>

          {stackExpanded && (
            <div
              id="error-stack"
              className="mt-3 bg-black/30 rounded-lg p-4 max-h-64 overflow-auto"
            >
              <pre className="text-xs text-gray-400 font-mono whitespace-pre-wrap">
                {error.stackTrace}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Retry Button */}
      <div className="mt-6 flex items-center justify-end gap-3">
        <GlassButton
          variant="primary"
          onClick={onRetry}
          disabled={isRetrying}
          aria-label={t('masterplan.accessibility.retryButton')}
        >
          <FiRefreshCw className={`mr-2 ${isRetrying ? 'animate-spin' : ''}`} />
          {isRetrying ? t('masterplan.errors.retryingMessage') : t('masterplan.buttons.retry')}
        </GlassButton>
      </div>

      {/* Retrying Message */}
      {isRetrying && (
        <div
          className="mt-4 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center"
          role="status"
          aria-live="polite"
        >
          <p className="text-blue-400 text-sm">
            {t('masterplan.errors.retryingMessage')}
          </p>
        </div>
      )}
    </GlassCard>
  );
};

export default ErrorPanel;
