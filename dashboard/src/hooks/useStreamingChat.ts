/**
 * Hook for streaming WebSocket chat with agents.
 * Provides real-time token-by-token response streaming.
 * Loads existing history via REST API on mount.
 */

import { useState, useCallback, useRef, useEffect } from 'react';

export interface StreamingMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  agent_name?: string;
  timestamp: string;
  isStreaming?: boolean;
}

interface UseStreamingChatOptions {
  agentId: number;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

interface UseStreamingChatReturn {
  messages: StreamingMessage[];
  isConnected: boolean;
  isStreaming: boolean;
  isLoadingHistory: boolean;
  sendMessage: (message: string) => void;
  connect: () => void;
  disconnect: () => void;
  clearMessages: () => void;
}

export function useStreamingChat({
  agentId,
  onConnect,
  onDisconnect,
  onError,
}: UseStreamingChatOptions): UseStreamingChatReturn {
  const [messages, setMessages] = useState<StreamingMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const currentResponseRef = useRef<string>('');
  const agentNameRef = useRef<string>('');

  // Stable refs for callbacks to avoid useEffect dependency issues
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  }, [onConnect, onDisconnect, onError]);

  // Load history on mount
  useEffect(() => {
    const loadHistory = async () => {
      setIsLoadingHistory(true);
      try {
        const apiUrl = `${window.location.protocol}//${window.location.hostname}:8000`;
        const response = await fetch(`${apiUrl}/agents/${agentId}/history`);
        if (response.ok) {
          const data = await response.json();
          if (data.messages && Array.isArray(data.messages)) {
            setMessages(data.messages.map((msg: any) => ({
              id: msg.id || `hist-${Date.now()}-${Math.random()}`,
              role: msg.role,
              content: msg.content,
              agent_name: msg.agent_name,
              timestamp: msg.timestamp,
              isStreaming: false,
            })));
          }
        }
      } catch (e) {
        console.error('Failed to load chat history:', e);
      } finally {
        setIsLoadingHistory(false);
      }
    };
    loadHistory();
  }, [agentId]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000'; // API port
    const wsUrl = `${protocol}//${host}:${port}/ws/chat/${agentId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      onConnectRef.current?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'connected':
            agentNameRef.current = data.agent_name;
            break;

          case 'start':
            // Agent is starting to respond
            setIsStreaming(true);
            currentResponseRef.current = '';
            // Add placeholder message
            setMessages((prev) => [
              ...prev,
              {
                id: `assistant-${Date.now()}`,
                role: 'assistant',
                content: '',
                agent_name: data.agent_name,
                timestamp: data.timestamp,
                isStreaming: true,
              },
            ]);
            break;

          case 'token':
            // Append token to current response
            currentResponseRef.current += data.content;
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.role === 'assistant' && lastMessage.isStreaming) {
                lastMessage.content = currentResponseRef.current;
              }
              return newMessages;
            });
            break;

          case 'done':
            // Response complete
            setIsStreaming(false);
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.role === 'assistant') {
                lastMessage.content = data.content;
                lastMessage.isStreaming = false;
              }
              return newMessages;
            });
            currentResponseRef.current = '';
            break;

          case 'error':
            setIsStreaming(false);
            onErrorRef.current?.(data.message);
            break;
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = () => {
      onErrorRef.current?.('WebSocket connection error');
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsStreaming(false);
      onDisconnectRef.current?.();
    };

    wsRef.current = ws;
  }, [agentId]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setIsStreaming(false);
  }, []);

  const sendMessage = useCallback((message: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      onErrorRef.current?.('Not connected to WebSocket');
      return;
    }

    if (isStreaming) {
      onErrorRef.current?.('Please wait for the current response to complete');
      return;
    }

    // Add user message
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Send to WebSocket
    wsRef.current.send(
      JSON.stringify({
        message,
        include_memories: true,
        allow_tools: true,
      })
    );
  }, [isStreaming]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    currentResponseRef.current = '';
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    isConnected,
    isStreaming,
    isLoadingHistory,
    sendMessage,
    connect,
    disconnect,
    clearMessages,
  };
}

/**
 * Hook for streaming multi-agent conversations.
 */
export interface ConversationMessage {
  id: string;
  agent_id: number;
  agent_name: string;
  content: string;
  timestamp: string;
  turn: number;
  isStreaming?: boolean;
}

interface UseStreamingConversationOptions {
  convId: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
  onComplete?: (turnsCompleted: number) => void;
}

interface UseStreamingConversationReturn {
  messages: ConversationMessage[];
  isConnected: boolean;
  isStreaming: boolean;
  currentAgent: string | null;
  turnsCompleted: number;
  maxTurns: number;
  advance: (prompt?: string) => void;
  connect: () => void;
  disconnect: () => void;
}

export function useStreamingConversation({
  convId,
  onConnect,
  onDisconnect,
  onError,
  onComplete,
}: UseStreamingConversationOptions): UseStreamingConversationReturn {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [turnsCompleted, setTurnsCompleted] = useState(0);
  const [maxTurns, setMaxTurns] = useState(20);
  const wsRef = useRef<WebSocket | null>(null);
  const currentResponseRef = useRef<string>('');

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.hostname;
    const port = '8000';
    const wsUrl = `${protocol}//${host}:${port}/ws/conversation/${convId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setIsConnected(true);
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'connected':
            setTurnsCompleted(data.turns_taken || 0);
            setMaxTurns(data.max_turns || 20);
            break;

          case 'turn_start':
            setIsStreaming(true);
            setCurrentAgent(data.agent_name);
            currentResponseRef.current = '';
            // Add placeholder message
            setMessages((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}`,
                agent_id: data.agent_id,
                agent_name: data.agent_name,
                content: '',
                timestamp: data.timestamp,
                turn: data.turn,
                isStreaming: true,
              },
            ]);
            break;

          case 'token':
            currentResponseRef.current += data.content;
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.isStreaming) {
                lastMessage.content = currentResponseRef.current;
              }
              return newMessages;
            });
            break;

          case 'turn_end':
            setIsStreaming(false);
            setCurrentAgent(null);
            setTurnsCompleted(data.turn);
            setMessages((prev) => {
              const newMessages = [...prev];
              const lastMessage = newMessages[newMessages.length - 1];
              if (lastMessage?.isStreaming) {
                lastMessage.content = data.content;
                lastMessage.isStreaming = false;
              }
              return newMessages;
            });
            currentResponseRef.current = '';
            break;

          case 'conversation_complete':
            onComplete?.(data.turns_taken);
            break;

          case 'error':
            setIsStreaming(false);
            setCurrentAgent(null);
            onError?.(data.message);
            break;
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = () => {
      onError?.('WebSocket connection error');
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsStreaming(false);
      setCurrentAgent(null);
      onDisconnect?.();
    };

    wsRef.current = ws;
  }, [convId, onConnect, onDisconnect, onError, onComplete]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setIsConnected(false);
    setIsStreaming(false);
    setCurrentAgent(null);
  }, []);

  const advance = useCallback((prompt?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      onError?.('Not connected to WebSocket');
      return;
    }

    if (isStreaming) {
      onError?.('Please wait for the current turn to complete');
      return;
    }

    wsRef.current.send(
      JSON.stringify({
        action: 'advance',
        prompt,
      })
    );
  }, [isStreaming, onError]);

  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    messages,
    isConnected,
    isStreaming,
    currentAgent,
    turnsCompleted,
    maxTurns,
    advance,
    connect,
    disconnect,
  };
}
