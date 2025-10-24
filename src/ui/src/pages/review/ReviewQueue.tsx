/**
 * ReviewQueue Page - Human review interface
 *
 * Displays review queue with filtering, sorting, and review actions.
 *
 * Author: DevMatrix Team
 * Date: 2025-10-24
 */

import React, { useState, useEffect } from 'react';
import { PageHeader, SearchBar, FilterButton, GlassCard, GlassButton } from '../../components/design-system';
import ReviewCard from '../../components/review/ReviewCard';
import ReviewModal from '../../components/review/ReviewModal';
import LoadingState from '../../components/review/LoadingState';
import EmptyState from '../../components/review/EmptyState';
import ErrorState from '../../components/review/ErrorState';

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
  const [orderBy] = useState<'priority' | 'confidence_score' | 'created_at'>('priority');
  const [order] = useState<'asc' | 'desc'>('desc');

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

  // Handle close modal
  const handleCloseModal = () => {
    setDialogOpen(false);
    setSelectedReview(null);
  };

  // Handle review action completed
  const handleActionComplete = () => {
    fetchReviewQueue(); // Refresh queue
  };


  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <PageHeader
          emoji="🔍"
          title="Review Queue"
          subtitle="Low-confidence atoms flagged for human review"
          className="mb-8"
        />

        {/* Filters */}
        <GlassCard className="mb-6">
          <div className="flex flex-col md:flex-row gap-4 items-center">
            {/* Search Bar */}
            <div className="w-full md:w-96">
              <SearchBar
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by description, file, or ID..."
              />
            </div>

            {/* Status Filter Buttons */}
            <div className="flex gap-2 flex-wrap">
              <FilterButton
                active={statusFilter === 'all'}
                onClick={() => setStatusFilter('all')}
              >
                All
              </FilterButton>
              <FilterButton
                active={statusFilter === 'pending'}
                onClick={() => setStatusFilter('pending')}
              >
                Pending
              </FilterButton>
              <FilterButton
                active={statusFilter === 'in_review'}
                onClick={() => setStatusFilter('in_review')}
              >
                In Review
              </FilterButton>
              <FilterButton
                active={statusFilter === 'approved'}
                onClick={() => setStatusFilter('approved')}
              >
                Approved
              </FilterButton>
              <FilterButton
                active={statusFilter === 'rejected'}
                onClick={() => setStatusFilter('rejected')}
              >
                Rejected
              </FilterButton>
            </div>

            {/* Refresh Button */}
            <GlassButton
              variant="secondary"
              size="sm"
              onClick={fetchReviewQueue}
            >
              Refresh
            </GlassButton>

            {/* Total Count */}
            <div className="text-gray-400 text-sm ml-auto whitespace-nowrap">
              {filteredReviews.length} items
            </div>
          </div>
        </GlassCard>

        {/* Loading State */}
        {loading && <LoadingState message="Loading reviews..." />}

        {/* Error State */}
        {error && <ErrorState error={error} onRetry={fetchReviewQueue} />}

        {/* Review Cards Grid */}
        {!loading && !error && filteredReviews.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredReviews.map((review) => (
              <ReviewCard
                key={review.review_id}
                review={review}
                onClick={() => handleViewReview(review)}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && filteredReviews.length === 0 && (
          <EmptyState
            icon="📭"
            message={
              statusFilter === 'pending'
                ? 'All atoms have been reviewed!'
                : 'No reviews found. Try changing the filters.'
            }
          />
        )}

        {/* Review Detail Modal */}
        <ReviewModal
          review={selectedReview}
          open={dialogOpen}
          onClose={handleCloseModal}
          onActionComplete={handleActionComplete}
        />
      </div>
    </div>
  );
};

export default ReviewQueue;
