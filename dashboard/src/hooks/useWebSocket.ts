// WebSocket hook for real-time updates

import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketEvent } from '../types';

interface UseWebSocketOptions {
  topics?: string[];
  onMessage?: (event: WebSocketEvent) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  autoReconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  lastEvent: WebSocketEvent | null;
  subscribe: (topics: string[]) => void;
  unsubscribe: (topics: string[]) => void;
  send: (data: unknown) => void;
  reconnectAttempts: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    topics = [],
    onMessage,
    onConnect,
    onDisconnect,
    autoReconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
  } = options;

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<WebSocketEvent | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Use refs to store callbacks to avoid reconnection loops
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const topicsRef = useRef(topics);

  // Update refs when callbacks change (without triggering reconnection)
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    topicsRef.current = topics;
  }, [onMessage, onConnect, onDisconnect, topics]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // In development, connect directly to backend to avoid Vite proxy issues
    // In production, use the same host
    const isDev = import.meta.env.DEV;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = isDev
      ? 'ws://localhost:8000/ws'
      : `${protocol}//${window.location.host}/ws`;

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        setReconnectAttempts(0);
        onConnectRef.current?.();

        // Subscribe to initial topics
        const currentTopics = topicsRef.current;
        if (currentTopics.length > 0) {
          ws.send(JSON.stringify({ action: 'subscribe', topics: currentTopics }));
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          setLastEvent(data);
          onMessageRef.current?.(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);

        // Only call onDisconnect if we were previously connected
        if (reconnectAttemptsRef.current === 0) {
          onDisconnectRef.current?.();
        }

        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          setReconnectAttempts(reconnectAttemptsRef.current);

          // Exponential backoff: 3s, 6s, 12s, 24s, 48s...
          const delay = reconnectInterval * Math.pow(2, reconnectAttemptsRef.current - 1);
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connect();
          }, Math.min(delay, 30000)); // Cap at 30 seconds
        }
      };

      ws.onerror = () => {
        // Silently handle errors - onclose will be called after this
      };

      wsRef.current = ws;
    } catch {
      // Failed to create WebSocket - will retry on next reconnect
    }
  }, [autoReconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const subscribe = useCallback((newTopics: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', topics: newTopics }));
    }
  }, []);

  const unsubscribe = useCallback((topicsToRemove: string[]) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'unsubscribe', topics: topicsToRemove }));
    }
  }, []);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    lastEvent,
    subscribe,
    unsubscribe,
    send,
    reconnectAttempts,
  };
}

export default useWebSocket;
