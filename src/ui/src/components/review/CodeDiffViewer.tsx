/**
 * CodeDiffViewer - Code viewer with Monaco Editor syntax highlighting
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Chip,
  Tooltip,
  IconButton,
  Alert,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import Editor from '@monaco-editor/react';

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

  // Get severity icon
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
      case 'high':
        return <ErrorIcon sx={{ fontSize: 16, color: '#f44336' }} />;
      case 'medium':
        return <WarningIcon sx={{ fontSize: 16, color: '#ff9800' }} />;
      case 'low':
        return <InfoIcon sx={{ fontSize: 16, color: '#2196f3' }} />;
      default:
        return <InfoIcon sx={{ fontSize: 16 }} />;
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
    <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Code Review</Typography>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Tooltip title={copiedShown ? 'Copied!' : 'Copy code'}>
              <IconButton size="small" onClick={handleCopyCode}>
                <CopyIcon />
              </IconButton>
            </Tooltip>
            <Chip
              label={`${issues.length} issues`}
              size="small"
              color={issues.length > 0 ? 'error' : 'success'}
            />
            <Chip
              label={language}
              size="small"
              variant="outlined"
            />
          </Box>
        </Box>

        {/* Tabs for diff view */}
        {originalCode && (
          <Tabs
            value={activeTab}
            onChange={(_, value) => setActiveTab(value)}
            sx={{ mt: 1 }}
          >
            <Tab label="Current Code" value="current" />
            <Tab label="Diff View" value="diff" />
          </Tabs>
        )}
      </Box>

      {/* Code content */}
      <Box sx={{ flex: 1, overflow: 'auto', position: 'relative' }}>
        {activeTab === 'current' ? (
          <Box sx={{ height: '100%' }}>
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
          </Box>
        ) : (
          <Box sx={{ display: 'flex', height: '100%' }}>
            <Box sx={{ flex: 1, borderRight: 1, borderColor: 'divider' }}>
              <Typography variant="caption" sx={{ p: 1, display: 'block', bgcolor: 'error.light', color: 'white' }}>
                Original
              </Typography>
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
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" sx={{ p: 1, display: 'block', bgcolor: 'success.light', color: 'white' }}>
                Modified
              </Typography>
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
            </Box>
          </Box>
        )}
      </Box>

      {/* Issues list below editor */}
      {issues.length > 0 && (
        <Box sx={{ borderTop: 1, borderColor: 'divider', p: 2, maxHeight: '200px', overflow: 'auto' }}>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Issues Found ({issues.length})
          </Typography>
          {Array.from(issueLines.entries()).map(([lineNum, lineIssues]) => (
            <Box key={lineNum} sx={{ mb: 1 }}>
              {lineIssues.map((issue, idx) => (
                <Alert
                  key={idx}
                  severity={
                    issue.severity === 'critical' || issue.severity === 'high'
                      ? 'error'
                      : issue.severity === 'medium'
                      ? 'warning'
                      : 'info'
                  }
                  icon={getSeverityIcon(issue.severity)}
                  sx={{ mb: 0.5 }}
                >
                  <Box>
                    <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
                      Line {lineNum}: {issue.description}
                    </Typography>
                    <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                      {issue.explanation}
                    </Typography>
                  </Box>
                </Alert>
              ))}
            </Box>
          ))}
        </Box>
      )}

      {/* Issue summary */}
      {issues.length > 0 && (
        <Box sx={{ borderTop: 1, borderColor: 'divider', p: 1, bgcolor: 'grey.100' }}>
          <Typography variant="caption" color="text.secondary">
            {issues.filter(i => i.severity === 'critical' || i.severity === 'high').length} critical/high •{' '}
            {issues.filter(i => i.severity === 'medium').length} medium •{' '}
            {issues.filter(i => i.severity === 'low').length} low
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

export default CodeDiffViewer;
