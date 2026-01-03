/**
 * Streaming chat panel component using WebSocket for real-time responses.
 */

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  Send,
  Clock,
  Sparkles,
  MessageSquare,
  AlertCircle,
  RefreshCw,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useStreamingChat, type StreamingMessage } from '../hooks/useStreamingChat';
import type { Agent } from '../types';

interface StreamingChatPanelProps {
  agent: Agent;
}

export function StreamingChatPanel({ agent }: StreamingChatPanelProps) {
  const [inputMessage, setInputMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    isConnected,
    isStreaming,
    isLoadingHistory,
    sendMessage,
    connect,
  } = useStreamingChat({
    agentId: agent.id,
    onConnect: () => setError(null),
    onError: (err) => setError(err),
  });

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim() && !isStreaming) {
      sendMessage(inputMessage);
      setInputMessage('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Chat header */}
      <div className="p-5 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center glow-purple">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-lg text-white">{agent.name}</h2>
            <p className="text-sm text-zinc-500">{agent.role}</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {/* Connection status */}
            <span className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full font-medium ${
              isConnected ? 'badge-success' : 'badge-warning'
            }`}>
              {isConnected ? (
                <><Wifi className="w-3 h-3" /> Connected</>
              ) : (
                <><WifiOff className="w-3 h-3" /> Disconnected</>
              )}
            </span>
            {/* Streaming status */}
            {isStreaming && (
              <span className="text-xs px-3 py-1.5 rounded-full font-medium badge-info flex items-center gap-1.5">
                <Sparkles className="w-3 h-3 animate-pulse" /> Streaming...
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mx-5 mt-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-red-400">{error}</p>
          </div>
          <button
            onClick={() => {
              setError(null);
              if (!isConnected) connect();
            }}
            className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {isLoadingHistory ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.1s]" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
            <p className="text-sm text-zinc-500">Loading history...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center">
              <MessageSquare className="w-7 h-7 text-zinc-500" />
            </div>
            <p className="text-sm text-zinc-500">No messages yet</p>
            <p className="text-xs text-zinc-600">Start the conversation below</p>
          </div>
        ) : (
          messages.map((msg: StreamingMessage) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  msg.role === 'user'
                    ? 'bg-gradient-to-br from-indigo-500 to-purple-500 text-white'
                    : 'glass-card'
                }`}
              >
                <div className={`text-sm leading-relaxed prose prose-sm max-w-none ${
                  msg.role === 'user'
                    ? 'prose-invert text-white prose-p:text-white prose-strong:text-white prose-code:text-white prose-headings:text-white'
                    : 'prose-invert prose-p:text-zinc-300 prose-strong:text-white prose-code:bg-zinc-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-purple-300 prose-pre:bg-zinc-800 prose-pre:border prose-pre:border-white/10 prose-headings:text-white prose-li:text-zinc-300'
                }`}>
                  {msg.content ? (
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  ) : msg.isStreaming ? (
                    <span className="flex items-center gap-2 text-zinc-400">
                      <span className="flex gap-1">
                        <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" />
                        <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                        <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce [animation-delay:0.2s]" />
                      </span>
                    </span>
                  ) : null}
                  {/* Cursor animation while streaming */}
                  {msg.isStreaming && msg.content && (
                    <span className="inline-block w-2 h-4 bg-purple-400 ml-0.5 animate-pulse" />
                  )}
                </div>
                <p className={`text-xs mt-2 flex items-center gap-1 ${
                  msg.role === 'user' ? 'text-indigo-200' : 'text-zinc-500'
                }`}>
                  <Clock className="w-3 h-3" />
                  {new Date(msg.timestamp).toLocaleTimeString()}
                  {msg.agent_name && (
                    <span className="ml-2 text-purple-400">- {msg.agent_name}</span>
                  )}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-5 border-t border-white/5">
        <div className="flex gap-3">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder={
              !isConnected
                ? 'Connecting...'
                : isStreaming
                ? `${agent.name} is responding...`
                : 'Type a message...'
            }
            aria-label={`Send message to ${agent.name}`}
            disabled={!isConnected || isStreaming}
            className="flex-1 px-5 py-3.5 input-glass rounded-xl disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!isConnected || isStreaming || !inputMessage.trim()}
            className="btn-gradient px-5 py-3.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
          >
            {isStreaming ? (
              <Sparkles className="w-5 h-5 animate-pulse" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

export default StreamingChatPanel;
