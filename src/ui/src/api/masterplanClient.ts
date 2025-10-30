/**
 * masterplanClient - API client for MasterPlan status recovery
 *
 * Provides functions to fetch current generation status from backend API
 * for page refresh recovery and status polling.
 *
 * @example
 * ```tsx
 * try {
 *   const status = await fetchMasterPlanStatus('mp_xxx');
 *   console.log('Current phase:', status.current_phase);
 *   console.log('Progress:', status.progress_percentage);
 * } catch (error) {
 *   console.error('Failed to fetch status:', error);
 * }
 * ```
 */

import type { MasterPlanStatusResponse } from '../types/masterplan';

/**
 * Base API URL (can be configured via environment variable)
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || '/api/v1';

/**
 * Fetch current MasterPlan generation status
 *
 * @param masterplanId - MasterPlan ID (e.g., 'mp_xxx')
 * @returns Promise resolving to status response
 * @throws Error if request fails or masterplan not found
 */
export async function fetchMasterPlanStatus(
  masterplanId: string
): Promise<MasterPlanStatusResponse> {
  if (!masterplanId) {
    throw new Error('MasterPlan ID is required');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/masterplans/${masterplanId}/status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // Authorization header will be added by middleware/interceptor
        // or retrieved from auth context
      },
      credentials: 'include', // Include cookies for authentication
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new Error(`MasterPlan not found: ${masterplanId}`);
      }

      if (response.status === 401 || response.status === 403) {
        throw new Error('Unauthorized - please log in');
      }

      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    const data: MasterPlanStatusResponse = await response.json();

    // Validate response structure
    if (!data.masterplan_id || !data.current_phase || !data.stats) {
      throw new Error('Invalid API response structure');
    }

    return data;
  } catch (error) {
    // Log error for debugging
    console.error('Failed to fetch MasterPlan status:', error);

    // Re-throw with more context
    if (error instanceof Error) {
      throw error;
    }

    throw new Error('Unknown error fetching MasterPlan status');
  }
}

/**
 * Poll MasterPlan status at regular intervals until complete
 *
 * @param masterplanId - MasterPlan ID to poll
 * @param onUpdate - Callback invoked on each status update
 * @param intervalMs - Polling interval in milliseconds (default: 2000ms)
 * @returns Function to stop polling
 *
 * @example
 * ```tsx
 * const stopPolling = pollMasterPlanStatus(
 *   'mp_xxx',
 *   (status) => {
 *     console.log('Progress:', status.progress_percentage);
 *   },
 *   2000
 * );
 *
 * // Stop polling when component unmounts
 * return () => stopPolling();
 * ```
 */
export function pollMasterPlanStatus(
  masterplanId: string,
  onUpdate: (status: MasterPlanStatusResponse) => void,
  intervalMs: number = 2000
): () => void {
  let intervalId: ReturnType<typeof setInterval> | null = null;
  let isPolling = true;

  const poll = async () => {
    if (!isPolling) return;

    try {
      const status = await fetchMasterPlanStatus(masterplanId);
      onUpdate(status);

      // Stop polling if complete or error
      if (status.is_complete || status.is_error) {
        stopPolling();
      }
    } catch (error) {
      console.error('Polling error:', error);
      // Continue polling on transient errors
      // Parent component can handle persistent errors
    }
  };

  const stopPolling = () => {
    isPolling = false;
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  };

  // Start polling
  intervalId = setInterval(poll, intervalMs);

  // Initial fetch
  poll();

  // Return stop function
  return stopPolling;
}

/**
 * Check if MasterPlan API endpoint is available
 *
 * @returns Promise resolving to true if endpoint is available
 */
export async function checkMasterPlanApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
    });

    return response.ok;
  } catch (error) {
    console.error('API health check failed:', error);
    return false;
  }
}
