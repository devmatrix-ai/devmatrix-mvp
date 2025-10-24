/**
 * AISuggestionsPanel - Display AI suggestions and alternatives
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import {
  FiZap,
  FiAlertOctagon,
  FiCode,
  FiTrendingUp,
  FiCopy,
} from 'react-icons/fi';

import { GlassCard } from '../design-system/GlassCard';
import { GlassButton } from '../design-system/GlassButton';
import { StatusBadge } from '../design-system/StatusBadge';
import { CustomAlert } from './CustomAlert';
import { CustomAccordion } from './CustomAccordion';
import ConfidenceIndicator from './ConfidenceIndicator';

interface AIAnalysis {
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
}

interface AISuggestionsPanelProps {
  analysis: AIAnalysis;
  confidenceScore: number;
}

const AISuggestionsPanel: React.FC<AISuggestionsPanelProps> = ({
  analysis,
  confidenceScore,
}) => {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Handle copy alternative
  const handleCopyAlternative = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Get recommendation severity
  const getRecommendationSeverity = (): 'error' | 'warning' | 'info' | 'success' => {
    if (analysis.recommendation.includes('REJECT')) return 'error';
    if (analysis.recommendation.includes('EDIT REQUIRED')) return 'error';
    if (analysis.recommendation.includes('REVIEW CAREFULLY')) return 'warning';
    if (analysis.recommendation.includes('MINOR EDITS')) return 'info';
    return 'success';
  };

  // Get severity status for badges
  const getSeverityStatus = (severity: string): 'error' | 'warning' | 'info' | 'success' | 'default' => {
    if (severity === 'critical' || severity === 'high') return 'error';
    if (severity === 'medium') return 'warning';
    if (severity === 'low') return 'info';
    return 'default';
  };

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Confidence Score */}
      <GlassCard className="p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Confidence Score</h4>
        <ConfidenceIndicator score={confidenceScore} size="large" />
      </GlassCard>

      {/* AI Recommendation */}
      <CustomAlert
        severity={getRecommendationSeverity()}
        message={
          <div>
            <p className="font-bold text-sm mb-1">AI Recommendation</p>
            <p className="text-sm">{analysis.recommendation}</p>
          </div>
        }
      />

      {/* Issues Summary */}
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <FiAlertOctagon className="text-red-400" size={20} />
          <h4 className="text-sm font-medium text-white">
            Issues Detected ({analysis.total_issues})
          </h4>
        </div>

        <div className="flex gap-2 flex-wrap">
          {analysis.issues_by_severity.critical > 0 && (
            <StatusBadge status="error">
              {analysis.issues_by_severity.critical} Critical
            </StatusBadge>
          )}
          {analysis.issues_by_severity.high > 0 && (
            <StatusBadge status="error">
              {analysis.issues_by_severity.high} High
            </StatusBadge>
          )}
          {analysis.issues_by_severity.medium > 0 && (
            <StatusBadge status="warning">
              {analysis.issues_by_severity.medium} Medium
            </StatusBadge>
          )}
          {analysis.issues_by_severity.low > 0 && (
            <StatusBadge status="info">
              {analysis.issues_by_severity.low} Low
            </StatusBadge>
          )}
        </div>
      </GlassCard>

      {/* Issue Details */}
      {analysis.issues.length > 0 && (
        <GlassCard className="flex-1 overflow-auto">
          <div className="border-b border-white/10 p-4">
            <h4 className="text-sm font-medium text-white">Issue Details</h4>
          </div>

          <div className="divide-y divide-white/10">
            {analysis.issues.map((issue, index) => (
              <div key={index} className="p-4">
                <div className="flex items-center gap-2 mb-2">
                  <StatusBadge status={getSeverityStatus(issue.severity)}>
                    {issue.severity}
                  </StatusBadge>
                  <p className="text-sm font-medium text-white">
                    {issue.description}
                  </p>
                </div>

                <p className="text-xs text-gray-400 mb-2">
                  {issue.explanation}
                </p>

                {issue.line_number && (
                  <p className="text-xs text-gray-500 mb-1">
                    Line {issue.line_number}
                  </p>
                )}

                {issue.code_snippet && (
                  <pre className="mt-2 p-2 bg-black/30 rounded text-xs font-mono text-gray-300 overflow-x-auto">
                    {issue.code_snippet}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Alternatives */}
      {analysis.alternatives && analysis.alternatives.length > 0 && (
        <CustomAccordion
          title={`Alternative Implementations (${analysis.alternatives.length})`}
          icon={<FiCode size={20} />}
        >
          <div className="divide-y divide-white/10">
            {analysis.alternatives.map((alt, index) => (
              <div key={index} className="p-4 flex justify-between items-start gap-4">
                <div className="flex-1">
                  <p className="text-xs text-gray-400 mb-1">
                    Alternative {index + 1}
                  </p>
                  <pre className="text-sm font-mono text-gray-300 whitespace-pre-wrap">
                    {alt}
                  </pre>
                </div>
                <GlassButton
                  variant="ghost"
                  size="sm"
                  onClick={() => handleCopyAlternative(alt, index)}
                  aria-label={copiedIndex === index ? 'Copied!' : 'Copy'}
                >
                  <FiCopy size={14} />
                  <span className="ml-1 text-xs">
                    {copiedIndex === index ? 'Copied!' : 'Copy'}
                  </span>
                </GlassButton>
              </div>
            ))}
          </div>
        </CustomAccordion>
      )}

      {/* Suggestions (if any) */}
      {analysis.suggestions && Object.keys(analysis.suggestions).length > 0 && (
        <CustomAccordion
          title={`Fix Suggestions (${Object.keys(analysis.suggestions).length})`}
          icon={<FiZap size={20} className="text-purple-400" />}
        >
          <div className="divide-y divide-white/10">
            {Object.entries(analysis.suggestions).map(([issue, suggestions]: [string, any], index) => (
              <div key={index} className="p-4">
                <p className="text-sm font-medium text-white mb-2">
                  {issue}
                </p>

                {Array.isArray(suggestions) && suggestions.length > 0 && (
                  <div className="space-y-3">
                    {suggestions.map((suggestion: any, sIndex: number) => (
                      <div key={sIndex} className="pl-4 border-l-2 border-purple-500/30">
                        <p className="text-xs text-purple-400 font-medium mb-1">
                          {suggestion.suggested_fix}
                        </p>

                        <div className="mt-2 p-2 bg-black/20 rounded">
                          <p className="text-xs text-gray-400 mb-1">
                            Before: <code className="text-gray-300">{suggestion.code_before}</code>
                          </p>
                          <p className="text-xs text-emerald-400">
                            After: <code className="text-emerald-300">{suggestion.code_after}</code>
                          </p>
                        </div>

                        <p className="text-xs text-gray-400 mt-2">
                          {suggestion.explanation}
                        </p>

                        <div className="flex items-center gap-1 mt-2">
                          <FiTrendingUp size={12} className="text-gray-500" />
                          <p className="text-xs text-gray-500">
                            Quality: {(suggestion.quality_score * 100).toFixed(0)}%
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CustomAccordion>
      )}
    </div>
  );
};

export default AISuggestionsPanel;
