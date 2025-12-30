import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from './useWebSocket';

// Mock WebSocket class
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  static instances: MockWebSocket[] = [];

  readyState = 0;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;

  url: string;
  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  });
}

describe('useWebSocket', () => {
  const originalWebSocket = (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket;

  beforeEach(() => {
    MockWebSocket.instances = [];
    (globalThis as unknown as { WebSocket: typeof MockWebSocket }).WebSocket = MockWebSocket;
  });

  afterEach(() => {
    (globalThis as unknown as { WebSocket: typeof WebSocket }).WebSocket = originalWebSocket;
    vi.clearAllMocks();
  });

  const getLastMockWs = () => MockWebSocket.instances[MockWebSocket.instances.length - 1];

  it('creates WebSocket connection on mount', () => {
    renderHook(() => useWebSocket());
    expect(MockWebSocket.instances.length).toBeGreaterThan(0);
  });

  it('starts disconnected', () => {
    const { result } = renderHook(() => useWebSocket());
    expect(result.current.isConnected).toBe(false);
  });

  it('initializes lastEvent as null', () => {
    const { result } = renderHook(() => useWebSocket());
    expect(result.current.lastEvent).toBeNull();
  });

  it('calls onConnect callback when connected', async () => {
    const onConnect = vi.fn();
    renderHook(() => useWebSocket({ onConnect }));
    const mockWs = getLastMockWs();

    await act(async () => {
      mockWs.readyState = 1;
      mockWs.onopen?.();
    });

    expect(onConnect).toHaveBeenCalled();
  });

  it('subscribes to topics on connect', async () => {
    const topics = ['agents', 'tasks'];
    renderHook(() => useWebSocket({ topics }));
    const mockWs = getLastMockWs();

    await act(async () => {
      mockWs.readyState = 1;
      mockWs.onopen?.();
    });

    expect(mockWs.send).toHaveBeenCalledWith(
      JSON.stringify({ action: 'subscribe', topics: ['agents', 'tasks'] })
    );
  });

  it('handles incoming messages', async () => {
    const onMessage = vi.fn();
    const { result } = renderHook(() => useWebSocket({ onMessage }));
    const mockWs = getLastMockWs();

    await act(async () => {
      mockWs.readyState = 1;
      mockWs.onopen?.();
    });

    const testEvent = {
      type: 'agent_update',
      data: { id: 1, status: 'busy' },
      timestamp: '2024-01-01T00:00:00Z',
    };

    await act(async () => {
      mockWs.onmessage?.({ data: JSON.stringify(testEvent) });
    });

    expect(onMessage).toHaveBeenCalledWith(testEvent);
    expect(result.current.lastEvent).toEqual(testEvent);
  });

  it('handles malformed messages gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onMessage = vi.fn();
    renderHook(() => useWebSocket({ onMessage }));
    const mockWs = getLastMockWs();

    await act(async () => {
      mockWs.readyState = 1;
      mockWs.onopen?.();
    });

    await act(async () => {
      mockWs.onmessage?.({ data: 'invalid json{' });
    });

    expect(consoleSpy).toHaveBeenCalled();
    expect(onMessage).not.toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it('calls onDisconnect when connection closes', async () => {
    const onDisconnect = vi.fn();
    renderHook(() => useWebSocket({ onDisconnect, autoReconnect: false }));
    const mockWs = getLastMockWs();

    await act(async () => {
      mockWs.readyState = 1;
      mockWs.onopen?.();
    });

    await act(async () => {
      mockWs.readyState = 3;
      mockWs.onclose?.();
    });

    expect(onDisconnect).toHaveBeenCalled();
  });

  it('does not send when WebSocket is not open', () => {
    const { result } = renderHook(() => useWebSocket({ autoReconnect: false }));
    const mockWs = getLastMockWs();

    // WebSocket is still in CONNECTING state
    act(() => {
      result.current.send({ type: 'test' });
    });

    // Should not send when not open
    expect(mockWs.send).not.toHaveBeenCalled();
  });

  it('exposes subscribe function', () => {
    const { result } = renderHook(() => useWebSocket());
    expect(typeof result.current.subscribe).toBe('function');
  });

  it('exposes unsubscribe function', () => {
    const { result } = renderHook(() => useWebSocket());
    expect(typeof result.current.unsubscribe).toBe('function');
  });

  it('exposes send function', () => {
    const { result } = renderHook(() => useWebSocket());
    expect(typeof result.current.send).toBe('function');
  });

  it('creates WebSocket with correct URL', () => {
    renderHook(() => useWebSocket());
    const mockWs = getLastMockWs();
    expect(mockWs.url).toContain('/ws');
  });
});
