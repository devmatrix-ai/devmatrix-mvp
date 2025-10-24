/**
 * AISuggestionsPanel - Display AI suggestions and alternatives
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  List,
  ListItem,
  ListItemText,
  Divider,
  Alert,
  Button,
  Tooltip,
} from '@mui/material';
import {
  ExpandMore as ExpandIcon,
  Lightbulb as SuggestionIcon,
  BugReport as IssueIcon,
  Code as CodeIcon,
  TrendingUp as ScoreIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';

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

  // Get recommendation color
  const getRecommendationColor = (): 'error' | 'warning' | 'info' | 'success' => {
    if (analysis.recommendation.includes('REJECT')) return 'error';
    if (analysis.recommendation.includes('EDIT REQUIRED')) return 'error';
    if (analysis.recommendation.includes('REVIEW CAREFULLY')) return 'warning';
    if (analysis.recommendation.includes('MINOR EDITS')) return 'info';
    return 'success';
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
      {/* Confidence Score */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Confidence Score
        </Typography>
        <ConfidenceIndicator score={confidenceScore} size="large" />
      </Paper>

      {/* AI Recommendation */}
      <Alert severity={getRecommendationColor()} icon={<SuggestionIcon />}>
        <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
          AI Recommendation
        </Typography>
        <Typography variant="body2">
          {analysis.recommendation}
        </Typography>
      </Alert>

      {/* Issues Summary */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <IssueIcon color="error" />
          <Typography variant="subtitle2">
            Issues Detected ({analysis.total_issues})
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {analysis.issues_by_severity.critical > 0 && (
            <Chip
              label={`${analysis.issues_by_severity.critical} Critical`}
              size="small"
              color="error"
            />
          )}
          {analysis.issues_by_severity.high > 0 && (
            <Chip
              label={`${analysis.issues_by_severity.high} High`}
              size="small"
              color="error"
              variant="outlined"
            />
          )}
          {analysis.issues_by_severity.medium > 0 && (
            <Chip
              label={`${analysis.issues_by_severity.medium} Medium`}
              size="small"
              color="warning"
            />
          )}
          {analysis.issues_by_severity.low > 0 && (
            <Chip
              label={`${analysis.issues_by_severity.low} Low`}
              size="small"
              color="info"
            />
          )}
        </Box>
      </Paper>

      {/* Issue Details */}
      {analysis.issues.length > 0 && (
        <Paper sx={{ flex: 1, overflow: 'auto' }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="subtitle2">Issue Details</Typography>
          </Box>

          <List dense>
            {analysis.issues.map((issue, index) => (
              <React.Fragment key={index}>
                <ListItem>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          label={issue.severity}
                          size="small"
                          color={
                            issue.severity === 'critical' || issue.severity === 'high'
                              ? 'error'
                              : issue.severity === 'medium'
                              ? 'warning'
                              : 'info'
                          }
                        />
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {issue.description}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          {issue.explanation}
                        </Typography>
                        {issue.line_number && (
                          <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                            Line {issue.line_number}
                          </Typography>
                        )}
                        {issue.code_snippet && (
                          <Box
                            sx={{
                              mt: 1,
                              p: 1,
                              bgcolor: 'grey.100',
                              borderRadius: 1,
                              fontFamily: 'monospace',
                              fontSize: '0.75rem',
                            }}
                          >
                            {issue.code_snippet}
                          </Box>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < analysis.issues.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}

      {/* Alternatives */}
      {analysis.alternatives && analysis.alternatives.length > 0 && (
        <Paper>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <CodeIcon />
                <Typography variant="subtitle2">
                  Alternative Implementations ({analysis.alternatives.length})
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <List dense>
                {analysis.alternatives.map((alt, index) => (
                  <ListItem
                    key={index}
                    secondaryAction={
                      <Tooltip title={copiedIndex === index ? 'Copied!' : 'Copy'}>
                        <Button
                          size="small"
                          startIcon={<CopyIcon />}
                          onClick={() => handleCopyAlternative(alt, index)}
                        >
                          Copy
                        </Button>
                      </Tooltip>
                    }
                  >
                    <ListItemText
                      primary={
                        <Typography variant="caption" sx={{ fontFamily: 'monospace' }}>
                          Alternative {index + 1}
                        </Typography>
                      }
                      secondary={
                        <Typography
                          variant="body2"
                          sx={{
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'monospace',
                            fontSize: '0.8rem',
                          }}
                        >
                          {alt}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}

      {/* Suggestions (if any) */}
      {analysis.suggestions && Object.keys(analysis.suggestions).length > 0 && (
        <Paper>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandIcon />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SuggestionIcon color="primary" />
                <Typography variant="subtitle2">
                  Fix Suggestions ({Object.keys(analysis.suggestions).length})
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <List dense>
                {Object.entries(analysis.suggestions).map(([issue, suggestions]: [string, any], index) => (
                  <ListItem key={index}>
                    <ListItemText
                      primary={
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          {issue}
                        </Typography>
                      }
                      secondary={
                        Array.isArray(suggestions) && suggestions.length > 0 && (
                          <Box sx={{ mt: 1 }}>
                            {suggestions.map((suggestion: any, sIndex: number) => (
                              <Box key={sIndex} sx={{ mb: 2 }}>
                                <Typography variant="caption" color="primary">
                                  {suggestion.suggested_fix}
                                </Typography>
                                <Box
                                  sx={{
                                    mt: 0.5,
                                    p: 1,
                                    bgcolor: 'grey.50',
                                    borderRadius: 1,
                                  }}
                                >
                                  <Typography variant="caption" display="block" color="text.secondary">
                                    Before: <code>{suggestion.code_before}</code>
                                  </Typography>
                                  <Typography variant="caption" display="block" color="success.main">
                                    After: <code>{suggestion.code_after}</code>
                                  </Typography>
                                </Box>
                                <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                                  {suggestion.explanation}
                                </Typography>
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.5 }}>
                                  <ScoreIcon sx={{ fontSize: 14 }} />
                                  <Typography variant="caption">
                                    Quality: {(suggestion.quality_score * 100).toFixed(0)}%
                                  </Typography>
                                </Box>
                              </Box>
                            ))}
                          </Box>
                        )
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </AccordionDetails>
          </Accordion>
        </Paper>
      )}
    </Box>
  );
};

export default AISuggestionsPanel;
