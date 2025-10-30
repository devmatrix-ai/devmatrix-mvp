/**
 * masterplanStorage - sessionStorage utilities for state persistence
 *
 * Provides functions to store, retrieve, and clear MasterPlan session data
 * for page refresh recovery with 5-minute expiry.
 *
 * @example
 * ```tsx
 * // Store session
 * storeMasterPlanSession({
 *   masterplan_id: 'mp_xxx',
 *   started_at: '2025-10-30T12:00:00Z',
 *   current_phase: 'parsing',
 *   progress_percentage: 65
 * });
 *
 * // Retrieve session
 * const session = getMasterPlanSession();
 * if (session) {
 *   console.log('Resuming from:', session.masterplan_id);
 * }
 *
 * // Clear session
 * clearMasterPlanSession();
 * ```
 */

import type { MasterPlanSession } from '../types/masterplan';

/**
 * sessionStorage key for MasterPlan session data
 */
const STORAGE_KEY = 'masterplan_session';

/**
 * Session expiry duration (5 minutes in milliseconds)
 */
const SESSION_EXPIRY_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Store MasterPlan session data in sessionStorage
 *
 * @param data - Session data to store
 * @throws Error if sessionStorage is not available
 */
export function storeMasterPlanSession(data: Omit<MasterPlanSession, '_timestamp'>): void {
  try {
    const sessionData: MasterPlanSession = {
      ...data,
      _timestamp: Date.now(),
    };

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(sessionData));
  } catch (error) {
    console.error('Failed to store MasterPlan session:', error);
    // Don't throw - graceful degradation if sessionStorage unavailable
  }
}

/**
 * Retrieve MasterPlan session data from sessionStorage
 *
 * Returns null if:
 * - No session data exists
 * - Session data is invalid
 * - Session data has expired (>5 minutes old)
 * - sessionStorage is not available
 *
 * @returns Session data or null
 */
export function getMasterPlanSession(): MasterPlanSession | null {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);

    if (!stored) {
      return null;
    }

    const sessionData: MasterPlanSession = JSON.parse(stored);

    // Validate required fields
    if (
      !sessionData.masterplan_id ||
      !sessionData.started_at ||
      !sessionData.current_phase ||
      sessionData.progress_percentage === undefined ||
      !sessionData._timestamp
    ) {
      console.warn('Invalid MasterPlan session data - clearing');
      clearMasterPlanSession();
      return null;
    }

    // Check expiry (5 minutes)
    const now = Date.now();
    const age = now - sessionData._timestamp;

    if (age > SESSION_EXPIRY_MS) {
      console.warn('MasterPlan session expired - clearing');
      clearMasterPlanSession();
      return null;
    }

    return sessionData;
  } catch (error) {
    console.error('Failed to retrieve MasterPlan session:', error);
    clearMasterPlanSession();
    return null;
  }
}

/**
 * Clear MasterPlan session data from sessionStorage
 */
export function clearMasterPlanSession(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear MasterPlan session:', error);
    // Don't throw - best effort cleanup
  }
}

/**
 * Check if a valid session exists
 *
 * @returns true if valid session exists, false otherwise
 */
export function hasMasterPlanSession(): boolean {
  return getMasterPlanSession() !== null;
}

/**
 * Update progress percentage in existing session
 *
 * @param percentage - New progress percentage (0-100)
 */
export function updateSessionProgress(percentage: number): void {
  const session = getMasterPlanSession();

  if (session) {
    storeMasterPlanSession({
      ...session,
      progress_percentage: Math.min(100, Math.max(0, percentage)),
    });
  }
}

/**
 * Update current phase in existing session
 *
 * @param phase - New phase name
 */
export function updateSessionPhase(phase: string): void {
  const session = getMasterPlanSession();

  if (session) {
    storeMasterPlanSession({
      ...session,
      current_phase: phase,
    });
  }
}
