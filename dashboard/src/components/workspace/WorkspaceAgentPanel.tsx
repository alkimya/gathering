/**
 * Workspace Agent Panel - Multi-Agent Conversation from Workspace
 *
 * Allows opening conversations with agents from the workspace context:
 * - Current file and selection as context
 * - Select multiple agents for discussion
 * - Real-time chat interface
 * - Insert code suggestions directly into editor
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot,
  X,
  Send,
  Users,
  FileCode,
  Loader2,
  ChevronDown,
  ChevronUp,
  Check,
  Sparkles,
  Code,
  Play,
  Maximize2,
  Minimize2,
  Copy,
  ExternalLink,
  Wifi,
  WifiOff,
  Plus,
  Circle,
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { conversations, circles } from '../../services/api';
import { useWebSocket } from '../../hooks/useWebSocket';
import type { Agent, ConversationDetail, ConversationMessage, Circle as CircleType, WebSocketEvent } from '../../types';

interface WorkspaceContext {
  projectId: number;
  projectName: string;
  currentFile?: string;
  selectedCode?: string;
  fileLanguage?: string;
}

interface WorkspaceAgentPanelProps {
  context: WorkspaceContext;
  onClose: () => void;
  onInsertCode?: (code: string) => void;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
}

// Agent selection component
function AgentSelector({
  agents: agentList,
  selectedAgents,
  onToggle,
  isLoading,
}: {
  agents: Agent[];
  selectedAgents: Set<number>;
  onToggle: (id: number) => void;
  isLoading: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(true);

  if (isLoading) {
    return (
      <div className="p-4 flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="border-b border-white/5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-zinc-300 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-purple-400" />
          <span>Agents ({selectedAgents.size} selected)</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-zinc-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-zinc-500" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2">
          {agentList.length === 0 ? (
            <p className="text-xs text-zinc-500 py-2">
              No agents in this circle. Add agents to the circle first.
            </p>
          ) : (
            agentList.map((agent) => (
              <label
                key={agent.id}
                className={`flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all ${
                  selectedAgents.has(agent.id)
                    ? 'bg-purple-500/20 border border-purple-500/30'
                    : 'bg-white/5 border border-white/5 hover:bg-white/10'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedAgents.has(agent.id)}
                  onChange={() => onToggle(agent.id)}
                  className="sr-only"
                />
                <div
                  className={`w-4 h-4 rounded border flex items-center justify-center ${
                    selectedAgents.has(agent.id)
                      ? 'bg-purple-500 border-purple-500'
                      : 'border-zinc-600'
                  }`}
                >
                  {selectedAgents.has(agent.id) && (
                    <Check className="w-3 h-3 text-white" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-white truncate">
                    {agent.name}
                  </div>
                  <div className="text-xs text-zinc-500 truncate">
                    {agent.role || agent.model || 'Assistant'}
                  </div>
                </div>
                <div
                  className={`w-2 h-2 rounded-full ${
                    agent.status === 'idle'
                      ? 'bg-green-500'
                      : agent.status === 'busy'
                      ? 'bg-amber-500'
                      : 'bg-zinc-500'
                  }`}
                />
              </label>
            ))
          )}
        </div>
      )}
    </div>
  );
}

// Context display component
function ContextDisplay({ context }: { context: WorkspaceContext }) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="border-b border-white/5">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between text-sm text-zinc-300 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-cyan-400" />
          <span>Context</span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-zinc-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-zinc-500" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 space-y-2 text-xs">
          <div className="flex items-center gap-2 text-zinc-400">
            <span className="text-zinc-500">Project:</span>
            <span className="text-white">{context.projectName}</span>
          </div>
          {context.currentFile && (
            <div className="flex items-center gap-2 text-zinc-400">
              <span className="text-zinc-500">File:</span>
              <code className="px-2 py-0.5 bg-white/5 text-cyan-400 rounded">
                {context.currentFile.split('/').pop()}
              </code>
            </div>
          )}
          {context.selectedCode && (
            <div className="mt-2">
              <span className="text-zinc-500">Selection:</span>
              <pre className="mt-1 p-2 bg-white/5 rounded-lg text-zinc-300 overflow-x-auto max-h-24 overflow-y-auto custom-scrollbar">
                {context.selectedCode.length > 200
                  ? context.selectedCode.substring(0, 200) + '...'
                  : context.selectedCode}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Message component
function ChatMessage({
  message,
  onInsertCode,
}: {
  message: ConversationMessage;
  onInsertCode?: (code: string) => void;
}) {
  const isSystem = message.agent_name === 'System' || message.agent_name === 'User';
  const isUser = message.agent_name === 'User';

  // Extract code blocks from message
  const extractCodeBlocks = (content: string): string[] => {
    const codeBlockRegex = /```[\w]*\n?([\s\S]*?)```/g;
    const blocks: string[] = [];
    let match;
    while ((match = codeBlockRegex.exec(content)) !== null) {
      blocks.push(match[1].trim());
    }
    return blocks;
  };

  const codeBlocks = extractCodeBlocks(message.content);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''} ${
        isSystem ? 'opacity-60' : ''
      }`}
    >
      {!isSystem && (
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isUser
              ? 'bg-gradient-to-br from-cyan-500 to-blue-500'
              : 'bg-gradient-to-br from-purple-500 to-pink-500'
          }`}
        >
          {isUser ? (
            <span className="text-xs font-bold text-white">You</span>
          ) : (
            <Bot className="w-4 h-4 text-white" />
          )}
        </div>
      )}

      <div
        className={`flex-1 ${isUser ? 'text-right' : ''} ${
          isSystem ? 'text-center' : ''
        }`}
      >
        {!isSystem && !isUser && (
          <div className="text-xs text-purple-400 font-medium mb-1">
            {message.agent_name}
          </div>
        )}

        <div
          className={`inline-block p-3 rounded-lg text-sm ${
            isUser
              ? 'bg-cyan-500/20 text-cyan-100 text-left'
              : isSystem
              ? 'bg-white/5 text-zinc-500 text-xs py-1.5'
              : 'bg-white/5 text-zinc-200'
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>

          {/* Code block actions */}
          {codeBlocks.length > 0 && onInsertCode && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              {codeBlocks.map((code, idx) => (
                <div key={idx} className="flex items-center gap-1">
                  <button
                    onClick={() => copyToClipboard(code)}
                    className="px-2 py-1 text-xs bg-white/10 hover:bg-white/20 rounded text-zinc-300 flex items-center gap-1 transition-colors"
                  >
                    <Copy className="w-3 h-3" />
                    Copy
                  </button>
                  <button
                    onClick={() => onInsertCode(code)}
                    className="px-2 py-1 text-xs bg-purple-500/20 hover:bg-purple-500/30 rounded text-purple-300 flex items-center gap-1 transition-colors"
                  >
                    <Code className="w-3 h-3" />
                    Insert
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {!isSystem && (
          <div className="text-xs text-zinc-600 mt-1">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}

export function WorkspaceAgentPanel({
  context,
  onClose,
  onInsertCode,
  isMaximized = false,
  onToggleMaximize,
}: WorkspaceAgentPanelProps) {
  const [selectedAgents, setSelectedAgents] = useState<Set<number>>(new Set());
  const [topic, setTopic] = useState('');
  const [userMessage, setUserMessage] = useState('');
  const [activeConversation, setActiveConversation] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [selectedCircle, setSelectedCircle] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket handler for real-time message updates
  const handleWebSocketMessage = useCallback((event: WebSocketEvent) => {
    if (event.type === 'conversation.message' && event.data?.conversation_id) {
      // Check if this message is for our active conversation
      const convId = event.data.conversation_id as string;
      if (activeConversation && convId === activeConversation.id) {
        const newMessage: ConversationMessage = {
          agent_id: (event.data.agent_id as number) || 0,
          agent_name: (event.data.agent_name as string) || 'Unknown',
          content: (event.data.content as string) || '',
          mentions: [],
          timestamp: (event.data.timestamp as string) || new Date().toISOString(),
        };

        // Avoid duplicates by checking if we already have this message
        setMessages((prev) => {
          const isDuplicate = prev.some(
            (m) =>
              m.agent_name === newMessage.agent_name &&
              m.content === newMessage.content &&
              Math.abs(new Date(m.timestamp).getTime() - new Date(newMessage.timestamp).getTime()) < 2000
          );
          if (isDuplicate) return prev;
          return [...prev, newMessage];
        });

        // Stop loading indicator when we receive an agent message
        if (newMessage.agent_name !== 'User') {
          setIsSending(false);
        }
      }
    }
  }, [activeConversation]);

  // WebSocket connection - subscribe to conversations topic
  const { isConnected, subscribe } = useWebSocket({
    topics: activeConversation ? [`conversations:${activeConversation.id}`, 'conversations'] : ['conversations'],
    onMessage: handleWebSocketMessage,
  });

  // Subscribe to conversation-specific topic when conversation starts
  useEffect(() => {
    if (activeConversation) {
      subscribe([`conversations:${activeConversation.id}`]);
    }
  }, [activeConversation, subscribe]);

  // Fetch circles list
  const { data: circlesData, isLoading: circlesLoading } = useQuery({
    queryKey: ['circles'],
    queryFn: () => circles.list(),
  });

  const queryClient = useQueryClient();
  const circleList = circlesData?.circles || [];
  const runningCircles = circleList.filter((c: CircleType) => c.status === 'running');
  const stoppedCircles = circleList.filter((c: CircleType) => c.status === 'stopped');

  // Fetch circle details (includes agents) when a circle is selected
  const { data: circleDetail, isLoading: circleDetailLoading } = useQuery({
    queryKey: ['circle-detail', selectedCircle],
    queryFn: () => circles.get(selectedCircle),
    enabled: !!selectedCircle, // Only fetch when a circle is selected
  });

  // Get agents from the selected circle only
  const agentList = circleDetail?.agents || [];
  const agentsLoading = circleDetailLoading && !!selectedCircle;

  // Quick circle creation state
  const [showQuickCreate, setShowQuickCreate] = useState(false);
  const [newCircleName, setNewCircleName] = useState('');
  const [isCreatingCircle, setIsCreatingCircle] = useState(false);

  // Create and start circle mutation
  const createCircleMutation = useMutation({
    mutationFn: async (name: string) => {
      // Create the circle
      await circles.create({ name, require_review: true, auto_route: true });
      // Start it immediately
      await circles.start(name);
      return name;
    },
    onSuccess: (name) => {
      queryClient.invalidateQueries({ queryKey: ['circles'] });
      setSelectedCircle(name);
      setShowQuickCreate(false);
      setNewCircleName('');
      setIsCreatingCircle(false);
    },
    onError: () => {
      setIsCreatingCircle(false);
    },
  });

  // Start existing circle mutation
  const startCircleMutation = useMutation({
    mutationFn: (name: string) => circles.start(name),
    onSuccess: (_, name) => {
      queryClient.invalidateQueries({ queryKey: ['circles'] });
      setSelectedCircle(name);
    },
  });

  const handleQuickCreateCircle = () => {
    if (!newCircleName.trim()) return;
    setIsCreatingCircle(true);
    createCircleMutation.mutate(newCircleName.trim());
  };

  // Auto-select first running circle
  useEffect(() => {
    if (runningCircles.length > 0 && !selectedCircle) {
      setSelectedCircle(runningCircles[0].name);
    }
  }, [runningCircles, selectedCircle]);

  // Reset agent selection when circle changes
  useEffect(() => {
    setSelectedAgents(new Set());
  }, [selectedCircle]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Generate default topic based on context
  useEffect(() => {
    if (context.currentFile) {
      const fileName = context.currentFile.split('/').pop() || 'file';
      if (context.selectedCode) {
        setTopic(`Review code in ${fileName}`);
      } else {
        setTopic(`Discussion about ${fileName}`);
      }
    } else {
      setTopic(`Project discussion: ${context.projectName}`);
    }
  }, [context]);

  const toggleAgent = (id: number) => {
    setSelectedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Start conversation mutation
  const startConversation = async () => {
    if (selectedAgents.size < 1) {
      console.warn('[Agent Panel] No agents selected');
      return;
    }

    if (!topic.trim()) {
      console.warn('[Agent Panel] No topic provided');
      return;
    }

    if (!selectedCircle) {
      console.warn('[Agent Panel] No circle selected');
      setMessages([{
        agent_id: 0,
        agent_name: 'System',
        content: 'Error: No running circle available. Please create and start a circle first.',
        mentions: [],
        timestamp: new Date().toISOString(),
      }]);
      return;
    }

    setIsStarting(true);

    try {
      // Build initial prompt with context
      let initialPrompt = userMessage || topic;
      if (context.currentFile) {
        initialPrompt = `[Context: Working on file ${context.currentFile}]\n\n${initialPrompt}`;
      }
      if (context.selectedCode) {
        initialPrompt = `${initialPrompt}\n\n[Selected code]:\n\`\`\`${context.fileLanguage || ''}\n${context.selectedCode}\n\`\`\``;
      }

      console.log('[Agent Panel] Creating conversation:', {
        topic: topic.trim(),
        agent_ids: Array.from(selectedAgents),
        circle: selectedCircle,
        initial_prompt: initialPrompt.slice(0, 100) + '...',
      });

      // Create and start conversation (pass circle name)
      const conv = await conversations.create({
        topic: topic.trim(),
        agent_ids: Array.from(selectedAgents),
        max_turns: 20,
        initial_prompt: initialPrompt,
        turn_strategy: selectedAgents.size > 1 ? 'round_robin' : 'free_form',
      }, selectedCircle);

      // Start the conversation
      const started = await conversations.start(conv.id);
      setActiveConversation(started);

      // Add initial user message to display
      // (Agent messages will arrive via WebSocket)
      setMessages([
        {
          agent_id: 0,
          agent_name: 'User',
          content: userMessage || topic,
          mentions: [],
          timestamp: new Date().toISOString(),
        },
      ]);

      // Subscribe to this conversation's WebSocket topic
      subscribe([`conversations:${conv.id}`]);

    } catch (err: any) {
      console.error('Failed to start conversation:', err);
      if (err.response) {
        console.error('[Agent Panel] Server response:', err.response);
      }
      if (err.data) {
        console.error('[Agent Panel] Error data:', err.data);
      }
      // Show error to user
      setMessages([{
        agent_id: 0,
        agent_name: 'System',
        content: `Error: ${err.message || 'Failed to start conversation'}`,
        mentions: [],
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsStarting(false);
    }
  };

  // Continue conversation
  const advanceConversation = async () => {
    if (!activeConversation || !userMessage.trim()) return;

    const msgToSend = userMessage;
    setUserMessage('');
    setIsSending(true);

    // Add user message to display immediately
    // (The same message will come via WebSocket, but we show it right away for responsiveness)
    setMessages((prev) => [
      ...prev,
      {
        agent_id: 0,
        agent_name: 'User',
        content: msgToSend,
        mentions: [],
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      // Advance conversation - agent responses will arrive via WebSocket
      await conversations.advance(activeConversation.id, msgToSend);
    } catch (err) {
      console.error('Failed to advance conversation:', err);
      setIsSending(false);
      // Show error message
      setMessages((prev) => [
        ...prev,
        {
          agent_id: 0,
          agent_name: 'System',
          content: 'Failed to send message. Please try again.',
          mentions: [],
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  const handleSend = () => {
    if (activeConversation) {
      advanceConversation();
    } else {
      startConversation();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Agent Conversation</h3>
            <p className="text-xs text-zinc-500">
              {activeConversation
                ? `${messages.length} messages`
                : 'Select agents to start'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* WebSocket connection indicator */}
          {activeConversation && (
            <div
              className={`p-1.5 rounded-lg ${isConnected ? 'text-green-400' : 'text-red-400'}`}
              title={isConnected ? 'Connected (real-time)' : 'Disconnected'}
            >
              {isConnected ? (
                <Wifi className="w-4 h-4" />
              ) : (
                <WifiOff className="w-4 h-4" />
              )}
            </div>
          )}
          {onToggleMaximize && (
            <button
              onClick={onToggleMaximize}
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
            >
              {isMaximized ? (
                <Minimize2 className="w-4 h-4 text-zinc-400" />
              ) : (
                <Maximize2 className="w-4 h-4 text-zinc-400" />
              )}
            </button>
          )}
          {activeConversation && (
            <a
              href={`/conversations`}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
              title="Open in Conversations page"
            >
              <ExternalLink className="w-4 h-4 text-zinc-400" />
            </a>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-4 h-4 text-zinc-400" />
          </button>
        </div>
      </div>

      {/* Setup mode - before conversation starts */}
      {!activeConversation && (
        <>
          {/* Context */}
          <ContextDisplay context={context} />

          {/* Circle Selection */}
          <div className="p-4 border-b border-white/5">
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-zinc-500">Circle</label>
              {!showQuickCreate && (
                <button
                  onClick={() => setShowQuickCreate(true)}
                  className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1 transition-colors"
                >
                  <Plus className="w-3 h-3" />
                  New
                </button>
              )}
            </div>
            {circlesLoading ? (
              <div className="flex items-center gap-2 text-zinc-500 text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading circles...
              </div>
            ) : showQuickCreate ? (
              /* Quick create circle form */
              <div className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newCircleName}
                    onChange={(e) => setNewCircleName(e.target.value)}
                    placeholder="circle-name"
                    className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
                    onKeyDown={(e) => e.key === 'Enter' && handleQuickCreateCircle()}
                    autoFocus
                  />
                  <button
                    onClick={handleQuickCreateCircle}
                    disabled={isCreatingCircle || !newCircleName.trim()}
                    className="px-3 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 disabled:opacity-50 flex items-center gap-1 transition-colors"
                  >
                    {isCreatingCircle ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Check className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => {
                      setShowQuickCreate(false);
                      setNewCircleName('');
                    }}
                    className="px-3 py-2 bg-white/5 text-zinc-400 rounded-lg text-sm hover:bg-white/10 transition-colors"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
                <p className="text-xs text-zinc-500">
                  Creates and starts a new circle immediately
                </p>
              </div>
            ) : runningCircles.length === 0 ? (
              /* No running circles - show options */
              <div className="space-y-2">
                {stoppedCircles.length > 0 ? (
                  /* Has stopped circles - allow starting one */
                  <div className="space-y-2">
                    <p className="text-xs text-amber-400 mb-2">
                      No active circles. Start one or create a new one.
                    </p>
                    {stoppedCircles.slice(0, 3).map((circle: CircleType) => (
                      <button
                        key={circle.name}
                        onClick={() => startCircleMutation.mutate(circle.name)}
                        disabled={startCircleMutation.isPending}
                        className="w-full flex items-center justify-between px-3 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm transition-colors"
                      >
                        <div className="flex items-center gap-2">
                          <Circle className="w-4 h-4 text-zinc-500" />
                          <span className="text-white">{circle.name}</span>
                          <span className="text-xs text-zinc-500">({circle.agent_count} agents)</span>
                        </div>
                        <div className="flex items-center gap-1 text-emerald-400">
                          {startCircleMutation.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <>
                              <Play className="w-3 h-3" />
                              <span className="text-xs">Start</span>
                            </>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                ) : (
                  /* No circles at all */
                  <div className="text-center py-3">
                    <Circle className="w-8 h-8 text-zinc-600 mx-auto mb-2" />
                    <p className="text-sm text-zinc-400 mb-2">No circles yet</p>
                    <button
                      onClick={() => setShowQuickCreate(true)}
                      className="px-3 py-1.5 bg-purple-500/20 text-purple-400 rounded-lg text-sm hover:bg-purple-500/30 flex items-center gap-1 mx-auto transition-colors"
                    >
                      <Plus className="w-4 h-4" />
                      Create your first circle
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <select
                value={selectedCircle}
                onChange={(e) => setSelectedCircle(e.target.value)}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-purple-500/50"
              >
                {runningCircles.map((circle: CircleType) => (
                  <option key={circle.name} value={circle.name} className="bg-zinc-900">
                    {circle.name} ({circle.agent_count} agents)
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Agent Selection - only show when a circle is selected */}
          {selectedCircle && (
            <AgentSelector
              agents={agentList}
              selectedAgents={selectedAgents}
              onToggle={toggleAgent}
              isLoading={agentsLoading}
            />
          )}

          {/* Topic */}
          <div className="p-4 border-b border-white/5">
            <label className="text-xs text-zinc-500 mb-2 block">Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="What would you like to discuss?"
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50"
            />
          </div>
        </>
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {messages.length === 0 && !activeConversation ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-purple-400" />
            </div>
            <h4 className="text-white font-medium mb-2">Start a Conversation</h4>
            <p className="text-zinc-500 text-sm max-w-xs">
              Select one or more agents and describe what you'd like to discuss about your code.
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <ChatMessage
                key={idx}
                message={msg}
                onInsertCode={onInsertCode}
              />
            ))}
            {/* Loading indicator when waiting for agent response */}
            {isSending && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                  <Bot className="w-4 h-4 text-white" />
                </div>
                <div className="flex items-center gap-2 text-zinc-400 text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Agents are thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input area */}
      <div className="p-4 border-t border-white/5">
        <div className="flex items-end gap-2">
          <textarea
            value={userMessage}
            onChange={(e) => setUserMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeConversation
                ? 'Continue the conversation...'
                : 'Describe what you want to discuss...'
            }
            rows={2}
            className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500/50 resize-none"
          />
          <button
            onClick={handleSend}
            disabled={
              isStarting ||
              isSending ||
              (!activeConversation && selectedAgents.size < 1) ||
              (!activeConversation && !topic.trim()) ||
              (!activeConversation && !selectedCircle) ||
              (activeConversation !== null && !userMessage.trim())
            }
            className="px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting...
              </>
            ) : activeConversation ? (
              <>
                <Send className="w-4 h-4" />
                Send
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Start
              </>
            )}
          </button>
        </div>
        {!activeConversation && selectedAgents.size < 1 && (
          <p className="text-xs text-amber-500 mt-2">
            Please select at least one agent
          </p>
        )}
      </div>
    </div>
  );
}
