/**
 * Tests — useUrgencyTimer hook.
 *
 * Verifica los niveles de urgencia según RN-CO07:
 * - < 10 min → normal (verde)
 * - 10–20 min → warning (naranja)
 * - > 20 min → critical (rojo)
 *
 * Usa fake timers para avanzar el tiempo y verificar la recalculación cada 15s.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useUrgencyTimer } from '../hooks/useUrgencyTimer';

describe('useUrgencyTimer', () => {
  let currentTime: number;
  const BASE_TIME = new Date('2025-06-01T12:00:00.000Z').getTime();

  beforeEach(() => {
    vi.useFakeTimers();
    currentTime = BASE_TIME;
    vi.spyOn(Date, 'now').mockImplementation(() => currentTime);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  function advanceTime(ms: number) {
    currentTime += ms;
    vi.advanceTimersByTime(ms);
  }

  it('returns level "normal" when elapsed time is < 10 minutes', () => {
    // Entry time: 5 minutes before BASE_TIME
    const entryTime = new Date(BASE_TIME - 5 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('normal');
    expect(result.current.elapsedMinutes).toBe(5);
  });

  it('returns level "normal" when elapsed time is exactly 0 minutes', () => {
    const entryTime = new Date(BASE_TIME).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('normal');
    expect(result.current.elapsedMinutes).toBe(0);
  });

  it('returns level "warning" when elapsed time is between 10 and 20 minutes', () => {
    // Entry time: 15 minutes before BASE_TIME
    const entryTime = new Date(BASE_TIME - 15 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(15);
  });

  it('returns level "warning" when elapsed time is exactly 10 minutes', () => {
    const entryTime = new Date(BASE_TIME - 10 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(10);
  });

  it('returns level "warning" when elapsed time is exactly 20 minutes', () => {
    const entryTime = new Date(BASE_TIME - 20 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(20);
  });

  it('returns level "critical" when elapsed time is > 20 minutes', () => {
    // Entry time: 25 minutes before BASE_TIME
    const entryTime = new Date(BASE_TIME - 25 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('critical');
    expect(result.current.elapsedMinutes).toBe(25);
  });

  it('recalculates every 15 seconds when time advances', async () => {
    // Entry time: 9 minutes before BASE_TIME — should start as "normal"
    const entryTime = new Date(BASE_TIME - 9 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('normal');
    expect(result.current.elapsedMinutes).toBe(9);

    // Advance 61 seconds (just over 1 minute) → should now be 10 minutes = "warning"
    await act(async () => {
      advanceTime(61_000);
    });

    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(10);
  });

  it('transitions from warning to critical after advancing past 20 minutes', async () => {
    // Entry time: 19 minutes before BASE_TIME
    const entryTime = new Date(BASE_TIME - 19 * 60_000).toISOString();

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(19);

    // Advance 61 seconds → 20 minutes = still warning
    await act(async () => {
      advanceTime(61_000);
    });
    expect(result.current.level).toBe('warning');
    expect(result.current.elapsedMinutes).toBe(20);

    // Advance another 61 seconds → 21 minutes = critical
    await act(async () => {
      advanceTime(61_000);
    });
    expect(result.current.level).toBe('critical');
    expect(result.current.elapsedMinutes).toBe(21);
  });

  it('accepts a Date object as entradaCocinaAt', () => {
    const entryTime = new Date(BASE_TIME - 5 * 60_000);

    const { result } = renderHook(() => useUrgencyTimer(entryTime));

    expect(result.current.level).toBe('normal');
    expect(result.current.elapsedMinutes).toBe(5);
  });
});
