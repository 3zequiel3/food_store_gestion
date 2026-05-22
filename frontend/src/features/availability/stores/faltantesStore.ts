/**
 * Zustand store for the admin navbar Faltantes badge.
 *
 * Tracks the count of unacknowledged ingredient_unavailable_reported events.
 * The count is incremented by the WS listener in the admin layout.
 * The count resets when the admin opens the Faltantes view.
 */
import { create } from 'zustand';

interface FaltantesState {
  /** Number of unacknowledged shortage reports since the last view open. */
  pendingCount: number;
  /** Increment counter (called on each ingredient_unavailable_reported WS event). */
  increment: () => void;
  /** Reset to 0 (called when the admin opens the Faltantes view). */
  reset: () => void;
  /** Set to a specific count (sync with the REST list length on open). */
  setCount: (n: number) => void;
}

export const useFaltantesStore = create<FaltantesState>((set) => ({
  pendingCount: 0,
  increment: () => set((s) => ({ pendingCount: s.pendingCount + 1 })),
  reset: () => set({ pendingCount: 0 }),
  setCount: (n) => set({ pendingCount: n }),
}));
