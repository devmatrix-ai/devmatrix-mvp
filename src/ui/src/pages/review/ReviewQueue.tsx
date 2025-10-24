/**
 * ReviewQueue Page - Human review interface
 *
 * Displays review queue with filtering, sorting, and review actions.
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  Button,
  Chip,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Alert,
  Grid,
} from '@mui/material';
import {
  CheckCircle as ApproveIcon,
  Cancel as RejectIcon,
  Edit as EditIcon,
  Refresh as RegenerateIcon,
  Visibility as ViewIcon,
} from '@mui/icons-material';

import CodeDiffViewer from '../../components/review/CodeDiffViewer';
import AISuggestionsPanel from '../../components/review/AISuggestionsPanel';
import ReviewActions from '../../components/review/ReviewActions';
import ConfidenceIndicator from '../../components/review/ConfidenceIndicator';

interface ReviewItem {
  review_id: string;
  atom_id: string;
  atom: {
    description: string;
    code: string;
    language: string;
    file_path: string;
    complexity: number;
    status: string;
  };
  confidence_score: number;
  priority: number;
  status: string;
  assigned_to: string | null;
  ai_analysis: {
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
  };
  reviewer_feedback: string | null;
  created_at: string;
  updated_at: string;
}

const ReviewQueue: React.FC = () => {
  // State
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('pending');
  const [searchQuery, setSearchQuery] = useState('');

  // Sorting
  const [orderBy, setOrderBy] = useState<'priority' | 'confidence_score' | 'created_at'>('priority');
  const [order, setOrder] = useState<'asc' | 'desc'>('desc');

  // Fetch review queue
  useEffect(() => {
    fetchReviewQueue();
  }, [statusFilter]);

  const fetchReviewQueue = async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (statusFilter && statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      params.append('limit', '50');

      const response = await fetch(`/api/v2/review/queue?${params}`);

      if (!response.ok) {
        throw new Error('Failed to fetch review queue');
      }

      const data = await response.json();
      setReviews(data.queue || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  // Handle sorting
  const handleSort = (property: 'priority' | 'confidence_score' | 'created_at') => {
    const isAsc = orderBy === property && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(property);
  };

  // Sort reviews
  const sortedReviews = React.useMemo(() => {
    return [...reviews].sort((a, b) => {
      const aValue = a[orderBy];
      const bValue = b[orderBy];

      if (order === 'asc') {
        return aValue < bValue ? -1 : 1;
      } else {
        return aValue > bValue ? -1 : 1;
      }
    });
  }, [reviews, orderBy, order]);

  // Filter reviews by search
  const filteredReviews = React.useMemo(() => {
    if (!searchQuery) return sortedReviews;

    const query = searchQuery.toLowerCase();
    return sortedReviews.filter(review =>
      review.atom.description.toLowerCase().includes(query) ||
      review.atom.file_path.toLowerCase().includes(query) ||
      review.atom_id.toLowerCase().includes(query)
    );
  }, [sortedReviews, searchQuery]);

  // Handle view review
  const handleViewReview = (review: ReviewItem) => {
    setSelectedReview(review);
    setDialogOpen(true);
  };

  // Handle review action completed
  const handleActionComplete = () => {
    setDialogOpen(false);
    setSelectedReview(null);
    fetchReviewQueue(); // Refresh queue
  };

  // Get status color
  const getStatusColor = (status: string): 'default' | 'primary' | 'success' | 'error' | 'warning' => {
    switch (status) {
      case 'pending': return 'warning';
      case 'in_review': return 'primary';
      case 'approved': return 'success';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  // Get severity color
  const getSeverityColor = (severity: string): 'default' | 'error' | 'warning' | 'info' => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Review Queue
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Low-confidence atoms flagged for human review
        </Typography>
      </Box>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 3 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth
              label="Search"
              variant="outlined"
              size="small"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by description, file, or ID..."
            />
          </Grid>

          <Grid size={{ xs: 12, md: 3 }}>
            <FormControl fullWidth size="small">
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="all">All</MenuItem>
                <MenuItem value="pending">Pending</MenuItem>
                <MenuItem value="in_review">In Review</MenuItem>
                <MenuItem value="approved">Approved</MenuItem>
                <MenuItem value="rejected">Rejected</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid size={{ xs: 12, md: 3 }}>
            <Button
              variant="outlined"
              onClick={fetchReviewQueue}
              fullWidth
            >
              Refresh Queue
            </Button>
          </Grid>

          <Grid size={{ xs: 12, md: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Total: {filteredReviews.length} items
            </Typography>
          </Grid>
        </Grid>
      </Paper>

      {/* Loading State */}
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Review Queue Table */}
      {!loading && !error && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'priority'}
                    direction={orderBy === 'priority' ? order : 'asc'}
                    onClick={() => handleSort('priority')}
                  >
                    Priority
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={orderBy === 'confidence_score'}
                    direction={orderBy === 'confidence_score' ? order : 'asc'}
                    onClick={() => handleSort('confidence_score')}
                  >
                    Confidence
                  </TableSortLabel>
                </TableCell>
                <TableCell>Description</TableCell>
                <TableCell>File</TableCell>
                <TableCell>Issues</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Recommendation</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredReviews.map((review) => (
                <TableRow key={review.review_id} hover>
                  <TableCell>
                    <Chip
                      label={review.priority}
                      size="small"
                      color={review.priority >= 75 ? 'error' : review.priority >= 50 ? 'warning' : 'default'}
                    />
                  </TableCell>
                  <TableCell>
                    <ConfidenceIndicator score={review.confidence_score} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {review.atom.description}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Complexity: {review.atom.complexity.toFixed(1)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.85rem' }}>
                      {review.atom.file_path}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {review.ai_analysis.issues_by_severity.critical > 0 && (
                        <Chip
                          label={`${review.ai_analysis.issues_by_severity.critical} Critical`}
                          size="small"
                          color="error"
                        />
                      )}
                      {review.ai_analysis.issues_by_severity.high > 0 && (
                        <Chip
                          label={`${review.ai_analysis.issues_by_severity.high} High`}
                          size="small"
                          color="error"
                          variant="outlined"
                        />
                      )}
                      {review.ai_analysis.issues_by_severity.medium > 0 && (
                        <Chip
                          label={`${review.ai_analysis.issues_by_severity.medium} Medium`}
                          size="small"
                          color="warning"
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={review.status}
                      size="small"
                      color={getStatusColor(review.status)}
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                      {review.ai_analysis.recommendation}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      startIcon={<ViewIcon />}
                      onClick={() => handleViewReview(review)}
                    >
                      Review
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Empty State */}
      {!loading && !error && filteredReviews.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.secondary">
            No reviews found
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {statusFilter === 'pending'
              ? 'All atoms have been reviewed!'
              : 'Try changing the filters'}
          </Typography>
        </Paper>
      )}

      {/* Review Detail Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedReview && (
          <>
            <DialogTitle>
              Review: {selectedReview.atom.description}
              <Typography variant="caption" display="block" color="text.secondary">
                {selectedReview.atom.file_path}
              </Typography>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={2}>
                {/* Code View */}
                <Grid size={{ xs: 12, md: 8 }}>
                  <CodeDiffViewer
                    code={selectedReview.atom.code}
                    language={selectedReview.atom.language}
                    issues={selectedReview.ai_analysis.issues}
                  />
                </Grid>

                {/* AI Suggestions Panel */}
                <Grid size={{ xs: 12, md: 4 }}>
                  <AISuggestionsPanel
                    analysis={selectedReview.ai_analysis}
                    confidenceScore={selectedReview.confidence_score}
                  />
                </Grid>

                {/* Review Actions */}
                <Grid size={{ xs: 12 }}>
                  <ReviewActions
                    reviewId={selectedReview.review_id}
                    atomId={selectedReview.atom_id}
                    currentCode={selectedReview.atom.code}
                    onActionComplete={handleActionComplete}
                  />
                </Grid>
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDialogOpen(false)}>
                Close
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
};

export default ReviewQueue;
