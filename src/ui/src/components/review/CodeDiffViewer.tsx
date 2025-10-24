/**
 * CodeDiffViewer - Code viewer with Monaco Editor syntax highlighting
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import { FiCopy } from 'react-icons/fi';
import Editor from '@monaco-editor/react';

import { GlassCard } from '../design-system/GlassCard';
import { GlassButton } from '../design-system/GlassButton';
import { StatusBadge } from '../design-system/StatusBadge';
import { CustomAlert } from './CustomAlert';
import { cn } from '../design-system/utils';

interface Issue {
  type: string;
  severity: string;
  description: string;
  line_number: number | null;
  code_snippet: string | null;
  explanation: string;
}

interface CodeDiffViewerProps {
  code: string;
  language: string;
  issues: Issue[];
  originalCode?: string; // For diff view
}

const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({
  code,
  language,
  issues,
  originalCode,
}) => {
  const [activeTab, setActiveTab] = useState<'current' | 'diff'>(
    originalCode ? 'diff' : 'current'
  );
  const [copiedShown, setCopiedShown] = useState(false);

  // Handle copy code
  const handleCopyCode = () => {
    navigator.clipboard.writeText(code);
    setCopiedShown(true);
    setTimeout(() => setCopiedShown(false), 2000);
  };

  // Get line numbers with issues
  const getIssueLines = (): Map<number, Issue[]> => {
    const lineMap = new Map<number, Issue[]>();

    issues.forEach(issue => {
      if (issue.line_number !== null) {
        const existing = lineMap.get(issue.line_number) || [];
        lineMap.set(issue.line_number, [...existing, issue]);
      }
    });

    return lineMap;
  };

  const issueLines = getIssueLines();

  // Get severity type for CustomAlert
  const getSeverityType = (severity: string): 'error' | 'warning' | 'info' | 'success' => {
    switch (severity) {
      case 'critical':
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'info';
      default:
        return 'info';
    }
  };

  // Map language to Monaco language ID
  const getMonacoLanguage = (lang: string): string => {
    const langMap: Record<string, string> = {
      'python': 'python',
      'javascript': 'javascript',
      'typescript': 'typescript',
      'jsx': 'javascript',
      'tsx': 'typescript',
      'json': 'json',
      'html': 'html',
      'css': 'css',
      'sql': 'sql',
      'java': 'java',
      'go': 'go',
      'rust': 'rust',
      'cpp': 'cpp',
      'c': 'c',
    };
    return langMap[lang.toLowerCase()] || 'plaintext';
  };

  return (
    <GlassCard className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-white/10 p-4">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-bold text-white">Code Review</h3>
          <div className="flex items-center gap-2">
            {/* Copy Button */}
            <GlassButton
              variant="ghost"
              size="sm"
              onClick={handleCopyCode}
              aria-label={copiedShown ? 'Copied!' : 'Copy code'}
            >
              <FiCopy size={16} />
              <span className="ml-2 text-xs">
                {copiedShown ? 'Copied!' : 'Copy'}
              </span>
            </GlassButton>

            {/* Issues Badge */}
            <StatusBadge status={issues.length > 0 ? 'error' : 'success'}>
              {issues.length} issues
            </StatusBadge>

            {/* Language Badge */}
            <StatusBadge status="default">{language}</StatusBadge>
          </div>
        </div>

        {/* Custom Tabs (if diff view) */}
        {originalCode && (
          <div className="flex gap-2 mt-4">
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium rounded-t-lg transition-all',
                activeTab === 'current'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/10'
              )}
              onClick={() => setActiveTab('current')}
              aria-label="Current Code"
            >
              Current Code
            </button>
            <button
              className={cn(
                'px-4 py-2 text-sm font-medium rounded-t-lg transition-all',
                activeTab === 'diff'
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/10'
              )}
              onClick={() => setActiveTab('diff')}
              aria-label="Diff View"
            >
              Diff View
            </button>
          </div>
        )}
      </div>

      {/* Monaco Editor Section - KEEP UNCHANGED */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'current' ? (
          <div className="h-full">
            <Editor
              height="100%"
              language={getMonacoLanguage(language)}
              value={code}
              theme="vs-dark"
              options={{
                readOnly: true,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                renderLineHighlight: 'all',
                automaticLayout: true,
              }}
            />
          </div>
        ) : (
          <div className="flex h-full">
            {/* Original */}
            <div className="flex-1 border-r border-white/10">
              <div className="bg-red-500/20 border-b border-white/10 px-4 py-2">
                <span className="text-xs text-red-200 font-medium">Original</span>
              </div>
              <Editor
                height="calc(100% - 32px)"
                language={getMonacoLanguage(language)}
                value={originalCode || ''}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 14,
                  lineNumbers: 'on',
                }}
              />
            </div>
            {/* Modified */}
            <div className="flex-1">
              <div className="bg-emerald-500/20 border-b border-white/10 px-4 py-2">
                <span className="text-xs text-emerald-200 font-medium">Modified</span>
              </div>
              <Editor
                height="calc(100% - 32px)"
                language={getMonacoLanguage(language)}
                value={code}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  scrollBeyondLastLine: false,
                  fontSize: 14,
                  lineNumbers: 'on',
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Issues List */}
      {issues.length > 0 && (
        <div className="border-t border-white/10 p-4 max-h-[200px] overflow-auto">
          <h4 className="text-sm font-medium text-white mb-3">
            Issues Found ({issues.length})
          </h4>
          <div className="space-y-2">
            {Array.from(issueLines.entries()).map(([lineNum, lineIssues]) => (
              <div key={lineNum}>
                {lineIssues.map((issue, idx) => (
                  <CustomAlert
                    key={idx}
                    severity={getSeverityType(issue.severity)}
                    message={
                      <div>
                        <p className="font-medium text-sm">
                          Line {lineNum}: {issue.description}
                        </p>
                        <p className="text-xs mt-1 opacity-80">
                          {issue.explanation}
                        </p>
                      </div>
                    }
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Issues Summary Footer */}
      {issues.length > 0 && (
        <div className="border-t border-white/10 px-4 py-2 bg-white/5">
          <p className="text-xs text-gray-400">
            {issues.filter(i => i.severity === 'critical' || i.severity === 'high').length} critical/high •{' '}
            {issues.filter(i => i.severity === 'medium').length} medium •{' '}
            {issues.filter(i => i.severity === 'low').length} low
          </p>
        </div>
      )}
    </GlassCard>
  );
};

export default CodeDiffViewer;
