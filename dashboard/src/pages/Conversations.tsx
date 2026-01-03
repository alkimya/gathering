// Conversations page with Web3 dark theme

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  MessageSquare,
  Plus,
  Trash2,
  Clock,
  Bot,
  ChevronRight,
  X,
  Sparkles,
  Users,
  User,
  CircleDot,
  AlertCircle,
  Send,
  Menu,
  ArrowLeft,
} from 'lucide-react';
import { conversations, agents, circles } from '../services/api';
import type { Conversation, ConversationMessage } from '../types';

function ConversationCard({
  conversation,
  isSelected,
  onSelect,
  onDelete,
}: {
  conversation: Conversation;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl cursor-pointer transition-all glass-card-hover ${
        isSelected
          ? 'glass-card border-purple-500/50 glow-purple'
          : 'glass-card'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              conversation.status === 'active'
                ? 'bg-gradient-to-br from-emerald-500 to-teal-500'
                : 'bg-gradient-to-br from-zinc-600 to-zinc-700'
            }`}>
              <MessageSquare className="w-5 h-5 text-white" />
            </div>
            {conversation.status === 'active' && (
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#11111b] bg-emerald-500 animate-pulse" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white">{conversation.topic}</h3>
            <p className="text-sm text-zinc-500">
              {conversation.participant_count ?? conversation.participant_names?.length ?? 0} participants
            </p>
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
        <div className="flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
          <span>{conversation.message_count ?? conversation.turns_taken ?? 0} messages</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>{new Date(conversation.created_at ?? conversation.started_at ?? Date.now()).toLocaleDateString()}</span>
        </div>
      </div>

      <div className="mt-3">
        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
          conversation.status === 'active'
            ? 'badge-success'
            : conversation.status === 'pending'
            ? 'badge-warning'
            : 'bg-zinc-500/20 text-zinc-400 border border-zinc-500/30'
        }`}>
          {conversation.status}
        </span>
      </div>
    </div>
  );
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isSystem = message.agent_name === 'System';
  const isUser = message.agent_id === 0 && message.agent_name !== 'System';

  // System messages (centered, minimal)
  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="text-xs text-zinc-500 bg-zinc-800/50 px-4 py-2 rounded-full border border-white/5">
          {message.content}
        </div>
      </div>
    );
  }

  // User messages (right-aligned, cyan theme)
  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%]">
          <div className="flex items-center justify-end gap-2 mb-2">
            <span className="text-xs text-zinc-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
            <span className="text-sm font-medium text-white">{message.agent_name || 'You'}</span>
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
          </div>
          <div className="mr-9 bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 rounded-2xl rounded-tr-none p-4">
            <div className="text-sm text-zinc-200 leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-2 prose-pre:bg-zinc-800 prose-pre:border prose-pre:border-white/10 prose-code:text-cyan-300 prose-code:bg-zinc-800 prose-code:px-1 prose-code:rounded prose-headings:text-white prose-strong:text-white prose-ul:my-2 prose-li:my-0 prose-table:border-collapse prose-th:border prose-th:border-white/20 prose-th:bg-zinc-800 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-white/10 prose-td:px-3 prose-td:py-2">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Agent messages (left-aligned, purple theme)
  return (
    <div className="flex justify-start">
      <div className="max-w-[80%]">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <Bot className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-medium text-white">{message.agent_name}</span>
          <span className="text-xs text-zinc-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
        <div className="ml-9 glass-card rounded-2xl rounded-tl-none p-4">
          <div className="text-sm text-zinc-300 leading-relaxed prose prose-invert prose-sm max-w-none prose-p:my-2 prose-pre:bg-zinc-800 prose-pre:border prose-pre:border-white/10 prose-code:text-purple-300 prose-code:bg-zinc-800 prose-code:px-1 prose-code:rounded prose-headings:text-white prose-strong:text-white prose-ul:my-2 prose-li:my-0 prose-table:border-collapse prose-th:border prose-th:border-white/20 prose-th:bg-zinc-800 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-white/10 prose-td:px-3 prose-td:py-2">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

function ConversationDetail({ conversation }: { conversation: Conversation }) {
  const [prompt, setPrompt] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: messagesData, isLoading } = useQuery({
    queryKey: ['conversation-messages', conversation.id],
    queryFn: () => conversations.getMessages(conversation.id),
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Display real messages from API (no more demo data fallback)
  const displayMessages = messagesData?.messages || [];

  const advanceMutation = useMutation({
    mutationFn: (p?: string) => conversations.advance(conversation.id, p),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversation-messages', conversation.id] });
      setPrompt('');
    },
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [displayMessages]);

  const handleAdvance = (e: React.FormEvent) => {
    e.preventDefault();
    advanceMutation.mutate(prompt || undefined);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-5 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center glow-purple">
              <MessageSquare className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-white">{conversation.topic}</h2>
              <p className="text-sm text-zinc-500">
                {conversation.participant_count ?? conversation.participant_names?.length ?? 0} participants · {conversation.status}
              </p>
            </div>
          </div>
        </div>

        {/* Participants */}
        <div className="mt-4">
          <p className="text-xs text-zinc-500 mb-2 flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5" />
            Participants
          </p>
          <div className="flex flex-wrap gap-2">
            {(conversation.participants ?? conversation.participant_names ?? []).map((p: string, i: number) => (
              <span
                key={i}
                className="text-xs px-3 py-1.5 glass-card rounded-full text-zinc-300"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.1s]" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
          </div>
        ) : displayMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
            <MessageSquare className="w-12 h-12 mb-3 opacity-50" />
            <p>No messages yet</p>
            <p className="text-xs mt-1">Click "Advance" to continue the conversation</p>
          </div>
        ) : (
          <>
            {displayMessages.map((msg, i: number) => (
              <MessageBubble key={i} message={msg as ConversationMessage} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
        {advanceMutation.isPending && (
          <div className="flex justify-center">
            <div className="glass-card rounded-2xl p-4">
              <div className="flex gap-1.5">
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Advance form */}
      <form onSubmit={handleAdvance} className="p-5 border-t border-white/5">
        <div className="flex gap-3">
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Optional prompt for next turn..."
            aria-label="Prompt for next conversation turn"
            disabled={advanceMutation.isPending}
            className="flex-1 px-5 py-3.5 input-glass rounded-xl disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={advanceMutation.isPending}
            className="btn-gradient px-5 py-3.5 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 font-medium"
          >
            <span>Advance</span>
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}

// Turn strategy options
const turnStrategies = [
  { value: 'round_robin', label: 'Round Robin', description: 'Each agent speaks in order' },
  { value: 'mention_based', label: 'Mention Based', description: 'Agent mentioned by @name speaks next' },
  { value: 'free_form', label: 'Free Form', description: 'Any agent can speak anytime' },
  { value: 'facilitator_led', label: 'Facilitator Led', description: 'Facilitator decides who speaks' },
] as const;

type TurnStrategy = typeof turnStrategies[number]['value'];

function CreateConversationModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [topic, setTopic] = useState('');
  const [initialPrompt, setInitialPrompt] = useState('');
  const [selectedCircle, setSelectedCircle] = useState<string | null>(null);
  const [selectedAgents, setSelectedAgents] = useState<number[]>([]);
  const [maxTurns, setMaxTurns] = useState(10);
  const [turnStrategy, setTurnStrategy] = useState<TurnStrategy>('round_robin');
  const [facilitatorId, setFacilitatorId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  // Fetch circles
  const { data: circlesData } = useQuery({
    queryKey: ['circles'],
    queryFn: circles.list,
    enabled: isOpen,
  });

  // Only show running circles
  const runningCircles = circlesData?.circles.filter(c => c.status === 'running') || [];

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
    enabled: isOpen,
  });

  // Get agents that are in the selected circle
  const { data: circleDetail } = useQuery({
    queryKey: ['circle-detail', selectedCircle],
    queryFn: () => selectedCircle ? circles.get(selectedCircle) : null,
    enabled: !!selectedCircle,
  });

  // Filter agents to only those in the selected circle
  const availableAgents = selectedCircle && circleDetail?.agents
    ? agentsData?.agents.filter(a => circleDetail.agents.some((ca: any) => ca.id === a.id)) || []
    : agentsData?.agents || [];

  const createMutation = useMutation({
    mutationFn: () => {
      if (!selectedCircle) throw new Error('Please select a circle');
      return conversations.create({
        topic,
        agent_ids: selectedAgents,
        max_turns: maxTurns,
        turn_strategy: turnStrategy,
        initial_prompt: initialPrompt || undefined,
        ...(turnStrategy === 'facilitator_led' && facilitatorId ? { facilitator_id: facilitatorId } : {}),
      }, selectedCircle);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      onClose();
      setTopic('');
      setInitialPrompt('');
      setSelectedCircle(null);
      setSelectedAgents([]);
      setMaxTurns(10);
      setTurnStrategy('round_robin');
      setFacilitatorId(null);
    },
  });

  // Reset agents when circle changes
  useEffect(() => {
    setSelectedAgents([]);
    setFacilitatorId(null);
  }, [selectedCircle]);

  // Reset facilitator when strategy changes or selected agents change
  const handleStrategyChange = (newStrategy: TurnStrategy) => {
    setTurnStrategy(newStrategy);
    if (newStrategy !== 'facilitator_led') {
      setFacilitatorId(null);
    }
  };

  // Get selected agents for facilitator dropdown (from available agents in the circle)
  const selectedAgentsList = availableAgents.filter(a => selectedAgents.includes(a.id));

  const toggleAgent = (id: number) => {
    setSelectedAgents((prev) => {
      const newSelection = prev.includes(id)
        ? prev.filter((a) => a !== id)
        : [...prev, id];

      // Reset facilitator if they were deselected
      if (facilitatorId === id && !newSelection.includes(id)) {
        setFacilitatorId(null);
      }

      return newSelection;
    });
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="start-conversation-title"
    >
      <div className="glass-card rounded-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center glow-purple">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 id="start-conversation-title" className="text-xl font-bold text-white">Start Conversation</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="space-y-5"
        >
          {/* Circle Selection - Required */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              <CircleDot className="w-4 h-4 inline mr-2" />
              Circle (required)
            </label>
            {runningCircles.length === 0 ? (
              <div className="p-4 glass-card rounded-xl text-center">
                <AlertCircle className="w-8 h-8 text-amber-400 mx-auto mb-2" />
                <p className="text-sm text-zinc-400">No running circles available</p>
                <p className="text-xs text-zinc-500 mt-1">
                  Go to Circles page and start a circle first
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {runningCircles.map((circle) => (
                  <label
                    key={circle.name}
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                      selectedCircle === circle.name
                        ? 'bg-emerald-500/20 border border-emerald-500/30'
                        : 'glass-card hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <input
                      type="radio"
                      name="circle"
                      checked={selectedCircle === circle.name}
                      onChange={() => setSelectedCircle(circle.name)}
                      className="w-4 h-4 text-emerald-500 bg-zinc-800 border-zinc-600 focus:ring-emerald-500 focus:ring-offset-0"
                    />
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
                        <CircleDot className="w-3 h-3 text-white" />
                      </div>
                      <span className="text-sm text-white">{(circle as any).display_name || circle.name}</span>
                      <span className="text-xs text-zinc-500">({circle.agent_count} agents)</span>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Topic
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="What should agents discuss?"
              required
              className="w-full px-4 py-3 input-glass rounded-xl"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              <Send className="w-4 h-4 inline mr-2" />
              Initial Prompt (optional)
            </label>
            <textarea
              value={initialPrompt}
              onChange={(e) => setInitialPrompt(e.target.value)}
              placeholder="Optional: provide context or a question to start the conversation..."
              rows={3}
              className="w-full px-4 py-3 input-glass rounded-xl resize-none"
            />
          </div>

          {/* Max Turns & Strategy Row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Max Turns
              </label>
              <input
                type="number"
                value={maxTurns}
                onChange={(e) => setMaxTurns(Math.max(2, Math.min(50, parseInt(e.target.value) || 10)))}
                min={2}
                max={50}
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
              <p className="text-xs text-zinc-500 mt-1">2-50 turns</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Turn Strategy
              </label>
              <select
                value={turnStrategy}
                onChange={(e) => handleStrategyChange(e.target.value as TurnStrategy)}
                className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
              >
                {turnStrategies.map((strategy) => (
                  <option key={strategy.value} value={strategy.value}>
                    {strategy.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-zinc-500 mt-1">
                {turnStrategies.find(s => s.value === turnStrategy)?.description}
              </p>
            </div>
          </div>

          {/* Facilitator Selector - only shown for facilitator_led strategy */}
          {turnStrategy === 'facilitator_led' && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Facilitator {selectedAgentsList.length < 2 && <span className="text-zinc-500">(select participants first)</span>}
              </label>
              {selectedAgentsList.length >= 2 ? (
                <div className="space-y-2">
                  {selectedAgentsList.map((agent) => (
                    <label
                      key={agent.id}
                      className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                        facilitatorId === agent.id
                          ? 'bg-amber-500/20 border border-amber-500/30'
                          : 'glass-card hover:bg-white/5 border border-transparent'
                      }`}
                    >
                      <input
                        type="radio"
                        name="facilitator"
                        checked={facilitatorId === agent.id}
                        onChange={() => setFacilitatorId(agent.id)}
                        className="w-4 h-4 text-amber-500 bg-zinc-800 border-zinc-600 focus:ring-amber-500 focus:ring-offset-0"
                      />
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
                          <Bot className="w-3 h-3 text-white" />
                        </div>
                        <span className="text-sm text-white">{agent.name}</span>
                        <span className="text-xs text-zinc-500">({agent.role})</span>
                      </div>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-zinc-500 py-3">
                  Select at least 2 participants to choose a facilitator
                </p>
              )}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Participants ({selectedAgents.length} selected)
              {selectedCircle && <span className="text-zinc-500 ml-2">from selected circle</span>}
            </label>
            {!selectedCircle ? (
              <div className="p-4 glass-card rounded-xl text-center text-zinc-500">
                <p className="text-sm">Select a circle first to see available agents</p>
              </div>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-2 glass-card rounded-xl p-3">
                {availableAgents.map((agent) => (
                  <label
                    key={agent.id}
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                      selectedAgents.includes(agent.id)
                        ? 'bg-purple-500/20 border border-purple-500/30'
                        : 'hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedAgents.includes(agent.id)}
                      onChange={() => toggleAgent(agent.id)}
                      className="w-4 h-4 text-purple-500 bg-zinc-800 border-zinc-600 rounded focus:ring-purple-500 focus:ring-offset-0"
                    />
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                        <Bot className="w-3 h-3 text-white" />
                      </div>
                      <span className="text-sm text-white">{agent.name}</span>
                      <span className="text-xs text-zinc-500">({agent.role})</span>
                    </div>
                  </label>
                ))}
                {availableAgents.length === 0 && (
                  <p className="text-sm text-zinc-500 text-center py-6">
                    No agents in this circle. Add agents first!
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Error display */}
          {createMutation.isError && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              <p className="text-sm text-red-400">{(createMutation.error as Error)?.message || 'Failed to create conversation'}</p>
            </div>
          )}

          <div className="flex gap-3 pt-4 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-all font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                createMutation.isPending ||
                !selectedCircle ||
                selectedAgents.length < 2 ||
                (turnStrategy === 'facilitator_led' && !facilitatorId)
              }
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {createMutation.isPending ? 'Creating...' : 'Start'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Conversations() {
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversations.list,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Display real conversations from API (no more demo data fallback)
  const displayConversations = data?.conversations || [];

  const deleteMutation = useMutation({
    mutationFn: conversations.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (selectedConversation) {
        setSelectedConversation(null);
      }
    },
  });

  // On mobile, hide sidebar when a conversation is selected
  const handleSelectConversation = (conv: Conversation) => {
    setSelectedConversation(conv);
    if (window.innerWidth < 768) {
      setShowSidebar(false);
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row gap-4 md:gap-6">
      {/* Mobile header with toggle */}
      <div className="md:hidden flex items-center justify-between">
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="flex items-center gap-2 p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
        >
          {showSidebar ? (
            <>
              <ArrowLeft className="w-5 h-5" />
              <span className="text-sm">Hide list</span>
            </>
          ) : (
            <>
              <Menu className="w-5 h-5" />
              <span className="text-sm">Show conversations</span>
            </>
          )}
        </button>
        {selectedConversation && !showSidebar && (
          <span className="text-sm text-zinc-400 truncate max-w-[150px]">
            {selectedConversation.topic}
          </span>
        )}
      </div>

      {/* Conversations list - collapsible on mobile */}
      <div className={`${showSidebar ? 'flex' : 'hidden'} md:flex w-full md:w-80 flex-shrink-0 flex-col`}>
        <div className="flex items-center justify-between mb-4 md:mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-xl md:text-2xl font-bold text-white">Conversations</h1>
            <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="p-2.5 btn-gradient rounded-xl"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-2">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="flex gap-1 justify-center">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          ) : displayConversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
              <MessageSquare className="w-10 h-10 mb-3 opacity-50" />
              <p className="text-sm">No conversations yet</p>
              <p className="text-xs mt-1">Click + to start one</p>
            </div>
          ) : (
            displayConversations.map((conv) => (
              <ConversationCard
                key={conv.id}
                conversation={conv}
                isSelected={selectedConversation?.id === conv.id}
                onSelect={() => handleSelectConversation(conv)}
                onDelete={() => deleteMutation.mutate(conv.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Conversation detail - show on mobile when sidebar is hidden or a conversation is selected */}
      <div className={`${!showSidebar || selectedConversation ? 'flex' : 'hidden md:flex'} flex-1 glass-card rounded-2xl overflow-hidden min-h-[300px]`}>
        {selectedConversation ? (
          <ConversationDetail conversation={selectedConversation} />
        ) : (
          <div className="h-full flex items-center justify-center w-full">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/20 flex items-center justify-center mx-auto mb-6">
                <MessageSquare className="w-10 h-10 text-purple-400" />
              </div>
              <p className="text-lg font-medium text-zinc-400">Select a conversation to view messages</p>
              <p className="text-sm text-zinc-600 mt-2">Choose from the list on the left</p>
            </div>
          </div>
        )}
      </div>

      <CreateConversationModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
      />
    </div>
  );
}

export default Conversations;
