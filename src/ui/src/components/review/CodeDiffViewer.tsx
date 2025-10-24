/**
 * CodeDiffViewer - Code viewer with syntax highlighting and issue markers
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
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

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
  const [copiedshown, setCopiedShown] = useState(false);

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

  // Custom line number renderer with issue markers
  const lineProps = (lineNumber: number) => {
    const lineIssues = issueLines.get(lineNumber);

    if (!lineIssues || lineIssues.length === 0) {
      return {};
    }

    return {
      style: {
        backgroundColor: lineIssues.some(i => i.severity === 'critical' || i.severity === 'high')
          ? 'rgba(244, 67, 54, 0.1)'
          : lineIssues.some(i => i.severity === 'medium')
          ? 'rgba(255, 152, 0, 0.1)'
          : 'rgba(33, 150, 243, 0.1)',
        borderLeft: lineIssues.some(i => i.severity === 'critical' || i.severity === 'high')
          ? '3px solid #f44336'
          : lineIssues.some(i => i.severity === 'medium')
          ? '3px solid #ff9800'
          : '3px solid #2196f3',
      },
    };
  };

  // Render code with syntax highlighting
  const renderCode = (codeContent: string) => {
    const lines = codeContent.split('\n');

    return (
      <Box sx={{ position: 'relative' }}>
        {/* Copy button */}
        <Box sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1 }}>
          <Tooltip title={copiedshown ? 'Copied!' : 'Copy code'}>
            <IconButton
              size="small"
              onClick={handleCopyCode}
              sx={{
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                '&:hover': { bgcolor: 'rgba(255, 255, 255, 0.2)' },
              }}
            >
              <CopyIcon sx={{ fontSize: 18, color: 'white' }} />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Syntax highlighted code */}
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          showLineNumbers
          wrapLines
          lineProps={lineProps}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            fontSize: '0.9rem',
          }}
        >
          {codeContent}
        </SyntaxHighlighter>

        {/* Issue markers */}
        {Array.from(issueLines.entries()).map(([lineNum, lineIssues]) => (
          <Box
            key={lineNum}
            sx={{
              position: 'absolute',
              left: 0,
              top: `${(lineNum - 1) * 21}px`, // Approximate line height
              width: '100%',
              pointerEvents: 'none',
            }}
          >
            <Box sx={{ display: 'flex', gap: 0.5, ml: 1, pointerEvents: 'auto' }}>
              {lineIssues.map((issue, idx) => (
                <Tooltip
                  key={idx}
                  title={
                    <Box>
                      <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
                        {issue.description}
                      </Typography>
                      <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                        {issue.explanation}
                      </Typography>
                    </Box>
                  }
                  arrow
                >
                  <Chip
                    icon={getSeverityIcon(issue.severity)}
                    label={issue.type}
                    size="small"
                    sx={{
                      height: 16,
                      fontSize: '0.65rem',
                      cursor: 'pointer',
                    }}
                  />
                </Tooltip>
              ))}
            </Box>
          </Box>
        ))}
      </Box>
    );
  };

  return (
    <Paper sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', p: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6">Code Review</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
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
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {activeTab === 'current' ? (
          renderCode(code)
        ) : (
          <Box sx={{ display: 'flex', height: '100%' }}>
            <Box sx={{ flex: 1, borderRight: 1, borderColor: 'divider' }}>
              <Typography variant="caption" sx={{ p: 1, display: 'block', bgcolor: 'error.light' }}>
                Original
              </Typography>
              {renderCode(originalCode || '')}
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" sx={{ p: 1, display: 'block', bgcolor: 'success.light' }}>
                Modified
              </Typography>
              {renderCode(code)}
            </Box>
          </Box>
        )}
      </Box>

      {/* Issue summary */}
      {issues.length > 0 && (
        <Box sx={{ borderTop: 1, borderColor: 'divider', p: 2 }}>
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
