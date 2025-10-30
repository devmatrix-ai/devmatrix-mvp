/**
 * Type definitions for MasterPlan visibility improvements
 *
 * These types support the real-time progress tracking, error handling,
 * and state persistence for MasterPlan generation workflows.
 */

/**
 * Phase names for MasterPlan generation workflow
 */
export type PhaseName = 'discovery' | 'parsing' | 'validation' | 'saving';

/**
 * Phase status indicators
 */
export type PhaseStatusType = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * Error source types for error categorization
 */
export type ErrorSource = 'validation' | 'database' | 'llm' | 'websocket' | 'unknown';

/**
 * Complete progress state for MasterPlan generation
 */
export interface ProgressState {
  /** Tokens received from LLM so far */
  tokensReceived: number;
  /** Estimated total tokens for complete generation */
  estimatedTotalTokens: number;
  /** Progress percentage (0-100) */
  percentage: number;
  /** Current phase being executed */
  currentPhase: string;
  /** Number of phases discovered/created */
  phasesFound: number;
  /** Number of milestones discovered/created */
  milestonesFound: number;
  /** Number of tasks discovered/created */
  tasksFound: number;
  /** Generation start time (null if not started) */
  startTime: Date | null;
  /** Elapsed seconds since start */
  elapsedSeconds: number;
  /** Estimated total duration in seconds */
  estimatedDurationSeconds: number;
  /** Currently parsing entities */
  isParsing: boolean;
  /** Currently validating dependencies */
  isValidating: boolean;
  /** Currently saving to database */
  isSaving: boolean;
  /** Generation complete */
  isComplete: boolean;
  /** Error information (if generation failed) */
  error?: ErrorInfo;
  /** Generation cost in USD */
  cost: number;
  /** Bounded contexts count */
  boundedContexts: number;
  /** Aggregates count */
  aggregates: number;
  /** Entities count */
  entities: number;
}

/**
 * Phase status with timing information
 */
export interface PhaseStatus {
  /** Phase identifier */
  name: PhaseName;
  /** Current status */
  status: PhaseStatusType;
  /** Duration in seconds (when complete) */
  duration?: number;
  /** Phase start timestamp */
  startTime?: Date;
  /** Phase end timestamp */
  endTime?: Date;
  /** Phase icon (emoji or icon name) */
  icon: string;
  /** Human-readable phase label (translation key) */
  label: string;
}

/**
 * Error information with diagnostics
 */
export interface ErrorInfo {
  /** User-friendly error message */
  message: string;
  /** Error code for categorization */
  code: string;
  /** Additional error details (optional) */
  details?: Record<string, any>;
  /** Stack trace for debugging (optional) */
  stackTrace?: string;
  /** Error timestamp */
  timestamp: Date;
  /** Error source category */
  source: ErrorSource;
}

/**
 * Entity counts for DDD model
 */
export interface EntityCounts {
  /** Number of bounded contexts */
  boundedContexts: number;
  /** Number of aggregates */
  aggregates: number;
  /** Number of entities */
  entities: number;
}

/**
 * Phase/milestone/task counts
 */
export interface PhaseCounts {
  /** Number of phases */
  phases: number;
  /** Number of milestones */
  milestones: number;
  /** Number of tasks */
  tasks: number;
}

/**
 * Session storage schema for state persistence
 */
export interface MasterPlanSession {
  /** MasterPlan ID (e.g., mp_xxx) */
  masterplan_id: string;
  /** Session start timestamp (ISO8601) */
  started_at: string;
  /** Current phase being executed */
  current_phase: string;
  /** Progress percentage (0-100) */
  progress_percentage: number;
  /** Internal timestamp for validation (epoch ms) */
  _timestamp: number;
}

/**
 * API response for MasterPlan status recovery
 */
export interface MasterPlanStatusResponse {
  /** MasterPlan ID */
  masterplan_id: string;
  /** Current phase */
  current_phase: string;
  /** Progress percentage (0-100) */
  progress_percentage: number;
  /** Session start timestamp (ISO8601) */
  started_at: string;
  /** Statistics object */
  stats: {
    /** Tokens used so far */
    tokens_used: number;
    /** Estimated total tokens */
    estimated_tokens: number;
    /** Generation cost in USD */
    cost: number;
    /** Elapsed duration in seconds */
    duration_seconds: number;
    /** Entity counts */
    entities: {
      bounded_contexts: number;
      aggregates: number;
      entities: number;
      phases: number;
      milestones: number;
      tasks: number;
    };
  };
  /** Generation complete flag */
  is_complete: boolean;
  /** Error flag */
  is_error: boolean;
}

/**
 * WebSocket event types for MasterPlan generation
 */
export type MasterPlanEventType =
  | 'discovery_generation_start'
  | 'discovery_tokens_progress'
  | 'discovery_entity_discovered'
  | 'discovery_parsing_complete'
  | 'discovery_saving_start'
  | 'discovery_generation_complete'
  | 'masterplan_generation_start'
  | 'masterplan_tokens_progress'
  | 'masterplan_entity_discovered'
  | 'masterplan_parsing_complete'
  | 'masterplan_validation_start'
  | 'masterplan_saving_start'
  | 'masterplan_generation_complete'
  | 'generation_error';

/**
 * WebSocket event payload structure
 */
export interface MasterPlanProgressEvent {
  /** Event type identifier */
  event: MasterPlanEventType;
  /** Event data payload (varies by event type) */
  data: Record<string, any>;
  /** Event timestamp (optional) */
  timestamp?: string;
}

/**
 * Props for MasterPlanProgressModal component
 */
export interface MasterPlanProgressModalProps {
  /** Current progress event (null when no generation active) */
  event: { event: string; data: Record<string, any> } | null;
  /** Whether modal is open */
  open: boolean;
  /** Close handler callback */
  onClose: () => void;
  /** MasterPlan ID for status recovery (optional) */
  masterplanId?: string;
}

/**
 * Props for ProgressTimeline component
 */
export interface ProgressTimelineProps {
  /** Array of phase statuses */
  phases: PhaseStatus[];
  /** Current active phase */
  currentPhase: string;
  /** Enable animated indicators (default: true) */
  animateActive?: boolean;
}

/**
 * Props for ProgressMetrics component
 */
export interface ProgressMetricsProps {
  /** Tokens used so far */
  tokensUsed: number;
  /** Estimated total tokens */
  estimatedTokens: number;
  /** Generation cost in USD */
  cost: number;
  /** Elapsed duration in seconds */
  duration: number;
  /** Estimated total duration in seconds */
  estimatedDuration: number;
  /** Entity counts */
  entities: {
    boundedContexts: number;
    aggregates: number;
    entities: number;
    phases: number;
    milestones: number;
    tasks: number;
  };
  /** Generation complete flag */
  isComplete: boolean;
}

/**
 * Props for PhaseIndicator component
 */
export interface PhaseIndicatorProps {
  /** Phase status object */
  phase: PhaseStatus;
  /** Whether this phase is currently active */
  isActive: boolean;
  /** Show duration when phase is complete (default: true) */
  showDuration?: boolean;
}

/**
 * Props for ErrorPanel component
 */
export interface ErrorPanelProps {
  /** Error information object */
  error: {
    message: string;
    code: string;
    details?: Record<string, any>;
    stackTrace?: string;
  };
  /** Retry callback handler */
  onRetry: () => void;
  /** Loading state during retry */
  isRetrying: boolean;
}

/**
 * Props for FinalSummary component
 */
export interface FinalSummaryProps {
  /** Final statistics */
  stats: {
    totalTokens: number;
    totalCost: number;
    totalDuration: number;
    entities: EntityCounts;
    phases: PhaseCounts;
  };
  /** Detected architecture style (optional) */
  architectureStyle?: string;
  /** Detected tech stack (optional) */
  techStack?: string[];
  /** View details callback */
  onViewDetails: () => void;
  /** Start execution callback */
  onStartExecution: () => void;
  /** Export callback (optional, Phase 2) */
  onExport?: () => void;
}

/**
 * Props for InlineProgressHeader component
 */
export interface InlineProgressHeaderProps {
  /** Current progress event (null when no generation active) */
  event: { event: string; data: Record<string, any> } | null;
  /** Click handler to open detailed modal */
  onClick: () => void;
}

/**
 * Return type for useMasterPlanProgress hook
 */
export interface UseMasterPlanProgressResult {
  /** Current progress state */
  state: ProgressState;
  /** Active session ID (masterplan_id) */
  sessionId: string | null;
  /** Phase timeline statuses */
  phases: PhaseStatus[];
  /** Retry generation handler */
  handleRetry: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
  /** Loading state */
  isLoading: boolean;
}
