/**
 * useMasterPlanProgress Hook Tests
 *
 * Tests for:
 * - Event processing (all 12 WebSocket events)
 * - State updates
 * - Elapsed time calculation
 * - sessionStorage persistence
 * - Error handling
 * - Retry mechanism
 * - Status recovery from API
 * - Phase status generation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useMasterPlanProgress } from '../useMasterPlanProgress';
import type { MasterPlanProgressEvent } from '../../types/masterplan';
import * as storage from '../../utils/masterplanStorage';
import * as client from '../../api/masterplanClient';

// Mock storage utilities
vi.mock('../../utils/masterplanStorage', () => ({
  storeMasterPlanSession: vi.fn(),
  getMasterPlanSession: vi.fn(),
  clearMasterPlanSession: vi.fn(),
}));

// Mock API client
vi.mock('../../api/masterplanClient', () => ({
  fetchMasterPlanStatus: vi.fn(),
}));

describe('useMasterPlanProgress', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    // Mock getMasterPlanSession to return null by default
    vi.mocked(storage.getMasterPlanSession).mockReturnValue(null);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Initial State', () => {
    it('returns initial state when no event is provided', () => {
      const { result } = renderHook(() => useMasterPlanProgress(null));

      expect(result.current.state.tokensReceived).toBe(0);
      expect(result.current.state.percentage).toBe(0);
      expect(result.current.state.currentPhase).toBe('');
      expect(result.current.state.isComplete).toBe(false);
      expect(result.current.sessionId).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });

    it('initializes phases with correct structure', () => {
      const { result } = renderHook(() => useMasterPlanProgress(null));

      expect(result.current.phases).toHaveLength(4);
      expect(result.current.phases[0].name).toBe('discovery');
      expect(result.current.phases[1].name).toBe('parsing');
      expect(result.current.phases[2].name).toBe('validation');
      expect(result.current.phases[3].name).toBe('saving');
    });
  });

  describe('Discovery Phase Events', () => {
    it('processes discovery_generation_start event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_generation_start',
        data: {
          estimated_tokens: 10000,
          estimated_duration_seconds: 120,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.currentPhase).toBe('discovery');
      expect(result.current.state.estimatedTotalTokens).toBe(10000);
      expect(result.current.state.estimatedDurationSeconds).toBe(120);
      expect(result.current.state.startTime).toBeInstanceOf(Date);
    });

    it('processes discovery_tokens_progress event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {
          tokens_received: 5000,
          estimated_total: 10000,
          percentage: 50,
          current_phase: 'discovery',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.tokensReceived).toBe(5000);
      expect(result.current.state.estimatedTotalTokens).toBe(10000);
      // Discovery is capped at 48%
      expect(result.current.state.percentage).toBe(48);
      expect(result.current.state.currentPhase).toBe('discovery');
    });

    it('processes discovery_entity_discovered event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_entity_discovered',
        data: {
          bounded_contexts: 3,
          aggregates: 7,
          entities: 25,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.boundedContexts).toBe(3);
      expect(result.current.state.aggregates).toBe(7);
      expect(result.current.state.entities).toBe(25);
    });

    it('processes discovery_parsing_complete event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_parsing_complete',
        data: {
          total_bounded_contexts: 5,
          total_aggregates: 12,
          total_entities: 45,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isParsing).toBe(false);
      expect(result.current.state.percentage).toBe(48);
      expect(result.current.state.boundedContexts).toBe(5);
      expect(result.current.state.aggregates).toBe(12);
      expect(result.current.state.entities).toBe(45);
    });

    it('processes discovery_saving_start event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_saving_start',
        data: {},
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isSaving).toBe(true);
    });

    it('processes discovery_generation_complete event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_generation_complete',
        data: {
          cost: 0.15,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isSaving).toBe(false);
      expect(result.current.state.percentage).toBe(50);
      expect(result.current.state.cost).toBe(0.15);
    });
  });

  describe('MasterPlan Phase Events', () => {
    it('processes masterplan_generation_start event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_generation_start',
        data: {
          masterplan_id: 'mp-123',
          estimated_tokens: 7000,
          estimated_duration_seconds: 80,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.currentPhase).toBe('parsing');
      expect(result.current.state.percentage).toBe(50);
      expect(result.current.sessionId).toBe('mp-123');

      // Should store session
      expect(storage.storeMasterPlanSession).toHaveBeenCalledWith(
        expect.objectContaining({
          masterplan_id: 'mp-123',
          current_phase: 'parsing',
          progress_percentage: 50,
        })
      );
    });

    it('processes masterplan_tokens_progress event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          tokens_received: 3500,
          percentage: 50, // 50% of masterplan phase
          current_phase: 'parsing',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      // Maps 0-100% to 50-92.5% range
      // 50% = 50 + (50/100 * 42.5) = 50 + 21.25 = 71.25, rounded to 71
      expect(result.current.state.percentage).toBe(71);
      expect(result.current.state.currentPhase).toBe('parsing');
    });

    it('processes masterplan_entity_discovered event for phases', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_entity_discovered',
        data: {
          type: 'phase',
          count: 1,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.phasesFound).toBe(1);
    });

    it('processes masterplan_entity_discovered event for milestones', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_entity_discovered',
        data: {
          type: 'milestone',
          count: 5,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.milestonesFound).toBe(5);
    });

    it('processes masterplan_entity_discovered event for tasks', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_entity_discovered',
        data: {
          type: 'task',
          count: 30,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.tasksFound).toBe(30);
    });

    it('processes masterplan_parsing_complete event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_parsing_complete',
        data: {
          total_phases: 3,
          total_milestones: 17,
          total_tasks: 120,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isParsing).toBe(false);
      expect(result.current.state.percentage).toBe(93);
      expect(result.current.state.phasesFound).toBe(3);
      expect(result.current.state.milestonesFound).toBe(17);
      expect(result.current.state.tasksFound).toBe(120);
    });

    it('processes masterplan_validation_start event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_validation_start',
        data: {},
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isValidating).toBe(true);
      expect(result.current.state.currentPhase).toBe('validation');
      expect(result.current.state.percentage).toBe(95);
    });

    it('processes masterplan_saving_start event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_saving_start',
        data: {},
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isValidating).toBe(false);
      expect(result.current.state.isSaving).toBe(true);
      expect(result.current.state.currentPhase).toBe('saving');
      expect(result.current.state.percentage).toBe(97);
    });

    it('processes masterplan_generation_complete event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {
          total_cost: 0.45,
          total_phases: 3,
          total_milestones: 17,
          total_tasks: 120,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.isSaving).toBe(false);
      expect(result.current.state.isComplete).toBe(true);
      expect(result.current.state.percentage).toBe(100);
      expect(result.current.state.currentPhase).toBe('complete');
      expect(result.current.state.cost).toBe(0.45);

      // Should clear session storage
      expect(storage.clearMasterPlanSession).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    it('processes generation_error event', () => {
      const event: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'LLM API timeout',
          code: 'LLM_API_TIMEOUT',
          details: { status: 503 },
          source: 'generation',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.error).toBeDefined();
      expect(result.current.state.error?.message).toBe('LLM API timeout');
      expect(result.current.state.error?.code).toBe('LLM_API_TIMEOUT');
      expect(result.current.state.error?.details).toEqual({ status: 503 });

      // Should clear session storage on error
      expect(storage.clearMasterPlanSession).toHaveBeenCalled();
    });

    it('clears error when clearError is called', () => {
      const event: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'Test error',
          code: 'TEST_ERROR',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      expect(result.current.state.error).toBeDefined();

      act(() => {
        result.current.clearError();
      });

      expect(result.current.state.error).toBeUndefined();
    });
  });

  describe('Elapsed Time Calculation', () => {
    it('calculates elapsed time automatically', async () => {
      const startEvent: MasterPlanProgressEvent = {
        event: 'discovery_generation_start',
        data: {
          estimated_tokens: 10000,
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(startEvent));

      expect(result.current.state.elapsedSeconds).toBe(0);

      // Advance timers by 3 seconds
      act(() => {
        vi.advanceTimersByTime(3000);
      });

      await waitFor(() => {
        expect(result.current.state.elapsedSeconds).toBe(3);
      });

      // Advance another 2 seconds
      act(() => {
        vi.advanceTimersByTime(2000);
      });

      await waitFor(() => {
        expect(result.current.state.elapsedSeconds).toBe(5);
      });
    });

    it('stops timer when generation is complete', async () => {
      const startEvent: MasterPlanProgressEvent = {
        event: 'discovery_generation_start',
        data: {},
      };

      const { result, rerender } = renderHook(
        ({ event }) => useMasterPlanProgress(event),
        { initialProps: { event: startEvent } }
      );

      // Advance timer
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      await waitFor(() => {
        expect(result.current.state.elapsedSeconds).toBe(5);
      });

      // Complete generation
      const completeEvent: MasterPlanProgressEvent = {
        event: 'masterplan_generation_complete',
        data: {},
      };

      rerender({ event: completeEvent });

      // Advance timer more - should not increase elapsed time
      act(() => {
        vi.advanceTimersByTime(5000);
      });

      // Elapsed time should still be 5
      expect(result.current.state.elapsedSeconds).toBe(5);
    });
  });

  describe('Session Storage Persistence', () => {
    it('recovers state from sessionStorage on mount', async () => {
      const storedSession = {
        masterplan_id: 'mp-123',
        started_at: new Date().toISOString(),
        current_phase: 'parsing',
        progress_percentage: 65,
      };

      vi.mocked(storage.getMasterPlanSession).mockReturnValue(storedSession);

      const mockStatus = {
        masterplan_id: 'mp-123',
        is_complete: false,
        current_phase: 'parsing',
        progress_percentage: 65,
        stats: {
          tokens_used: 8500,
          estimated_tokens: 15000,
          cost: 0.25,
          duration_seconds: 75,
          entities: {
            bounded_contexts: 5,
            aggregates: 12,
            entities: 45,
            phases: 3,
            milestones: 17,
            tasks: 120,
          },
        },
      };

      vi.mocked(client.fetchMasterPlanStatus).mockResolvedValue(mockStatus);

      const { result } = renderHook(() => useMasterPlanProgress(null));

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // State should be recovered
      expect(result.current.sessionId).toBe('mp-123');
      expect(result.current.state.currentPhase).toBe('parsing');
      expect(result.current.state.percentage).toBe(65);
      expect(result.current.state.tokensReceived).toBe(8500);
      expect(result.current.state.phasesFound).toBe(3);
    });

    it('clears stale session on API error', async () => {
      const storedSession = {
        masterplan_id: 'mp-invalid',
        started_at: new Date().toISOString(),
        current_phase: 'parsing',
        progress_percentage: 50,
      };

      vi.mocked(storage.getMasterPlanSession).mockReturnValue(storedSession);
      vi.mocked(client.fetchMasterPlanStatus).mockRejectedValue(new Error('Not found'));

      const { result } = renderHook(() => useMasterPlanProgress(null));

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should clear stale session
      expect(storage.clearMasterPlanSession).toHaveBeenCalled();
      expect(result.current.sessionId).toBeNull();
    });
  });

  describe('Phase Status Generation', () => {
    it('marks current phase as in_progress', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_tokens_progress',
        data: {
          current_phase: 'parsing',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      const parsingPhase = result.current.phases.find((p) => p.name === 'parsing');
      expect(parsingPhase?.status).toBe('in_progress');
    });

    it('marks previous phases as completed', () => {
      const event: MasterPlanProgressEvent = {
        event: 'masterplan_validation_start',
        data: {},
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      const discoveryPhase = result.current.phases.find((p) => p.name === 'discovery');
      const parsingPhase = result.current.phases.find((p) => p.name === 'parsing');
      const validationPhase = result.current.phases.find((p) => p.name === 'validation');

      expect(discoveryPhase?.status).toBe('completed');
      expect(parsingPhase?.status).toBe('completed');
      expect(validationPhase?.status).toBe('in_progress');
    });

    it('marks future phases as pending', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {
          current_phase: 'discovery',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      const parsingPhase = result.current.phases.find((p) => p.name === 'parsing');
      const validationPhase = result.current.phases.find((p) => p.name === 'validation');
      const savingPhase = result.current.phases.find((p) => p.name === 'saving');

      expect(parsingPhase?.status).toBe('pending');
      expect(validationPhase?.status).toBe('pending');
      expect(savingPhase?.status).toBe('pending');
    });
  });

  describe('Retry Mechanism', () => {
    it('resets state when handleRetry is called', async () => {
      const errorEvent: MasterPlanProgressEvent = {
        event: 'generation_error',
        data: {
          message: 'Test error',
          code: 'TEST_ERROR',
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(errorEvent));

      expect(result.current.state.error).toBeDefined();

      await act(async () => {
        await result.current.handleRetry();
      });

      // State should be reset
      expect(result.current.state.error).toBeUndefined();
      expect(result.current.state.tokensReceived).toBe(0);
      expect(result.current.state.percentage).toBe(0);
      expect(result.current.state.isComplete).toBe(false);

      // Session should be cleared
      expect(storage.clearMasterPlanSession).toHaveBeenCalled();
      expect(result.current.sessionId).toBeNull();
    });
  });

  describe('Edge Cases', () => {
    it('handles event without data gracefully', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {},
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      // Should not crash, values should default to 0
      expect(result.current.state.tokensReceived).toBe(0);
      expect(result.current.state.percentage).toBe(0);
    });

    it('handles rapid event updates', () => {
      const { result, rerender } = renderHook(
        ({ event }) => useMasterPlanProgress(event),
        {
          initialProps: {
            event: {
              event: 'discovery_tokens_progress',
              data: { tokens_received: 1000 },
            } as MasterPlanProgressEvent,
          },
        }
      );

      expect(result.current.state.tokensReceived).toBe(1000);

      // Rapid updates
      for (let i = 2000; i <= 10000; i += 1000) {
        rerender({
          event: {
            event: 'discovery_tokens_progress',
            data: { tokens_received: i },
          } as MasterPlanProgressEvent,
        });
      }

      expect(result.current.state.tokensReceived).toBe(10000);
    });

    it('handles percentage over 100%', () => {
      const event: MasterPlanProgressEvent = {
        event: 'discovery_tokens_progress',
        data: {
          percentage: 150, // Invalid percentage
        },
      };

      const { result } = renderHook(() => useMasterPlanProgress(event));

      // Should cap at 48% for discovery
      expect(result.current.state.percentage).toBe(48);
    });
  });
});
