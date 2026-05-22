/**
 * Tests for buildWebSocketUrl — lib/ws.ts
 *
 * Contract:
 * - When VITE_WS_URL is set → uses it as origin base, appends /ws?token=<encoded>
 * - Strips a trailing slash from VITE_WS_URL before appending
 * - When VITE_WS_URL is unset/empty → derives origin from window.location (protocol + host)
 * - Uses wss: when window.location.protocol === 'https:', ws: otherwise
 * - Token is always URL-encoded
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// Import AFTER mocks are established (vi.stubEnv applies per-test in beforeEach)
import { buildWebSocketUrl } from '../ws';

describe('buildWebSocketUrl — VITE_WS_URL set', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('uses the configured origin and appends /ws?token=<encoded>', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://api.example.com');

    const result = buildWebSocketUrl('my-token-123');

    expect(result).toBe('wss://api.example.com/ws?token=my-token-123');
  });

  it('strips a trailing slash from VITE_WS_URL before appending path', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://api.example.com/');

    const result = buildWebSocketUrl('abc');

    expect(result).toBe('wss://api.example.com/ws?token=abc');
  });

  it('URL-encodes the token when env var is set', () => {
    vi.stubEnv('VITE_WS_URL', 'wss://api.example.com');
    const token = 'header.pay load+special/chars=';

    const result = buildWebSocketUrl(token);

    expect(result).toContain('wss://api.example.com/ws?token=');
    expect(result).toBe(`wss://api.example.com/ws?token=${encodeURIComponent(token)}`);
  });
});

describe('buildWebSocketUrl — VITE_WS_URL unset (fallback to window.location)', () => {
  const originalLocation = window.location;

  beforeEach(() => {
    vi.unstubAllEnvs();
    // Ensure VITE_WS_URL is not set
    vi.stubEnv('VITE_WS_URL', '');
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    Object.defineProperty(window, 'location', {
      value: originalLocation,
      writable: true,
      configurable: true,
    });
  });

  function mockWindowLocation(protocol: string, host: string) {
    Object.defineProperty(window, 'location', {
      value: { protocol, host },
      writable: true,
      configurable: true,
    });
  }

  it('uses wss: when window.location.protocol is https:', () => {
    mockWindowLocation('https:', 'app.example.com');

    const result = buildWebSocketUrl('tok');

    expect(result).toBe('wss://app.example.com/ws?token=tok');
  });

  it('uses ws: when window.location.protocol is http:', () => {
    mockWindowLocation('http:', 'localhost:5173');

    const result = buildWebSocketUrl('tok');

    expect(result).toBe('ws://localhost:5173/ws?token=tok');
  });

  it('URL-encodes the token in fallback mode', () => {
    mockWindowLocation('http:', 'localhost:8000');
    const token = 'eyJhb<special> chars&more=1';

    const result = buildWebSocketUrl(token);

    expect(result).toBe(`ws://localhost:8000/ws?token=${encodeURIComponent(token)}`);
  });
});
