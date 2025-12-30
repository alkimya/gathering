// Conversations page with Web3 dark theme

import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
} from 'lucide-react';
import { conversations, agents } from '../services/api';
import type { Conversation, ConversationMessage } from '../types';

// Demo data for when API returns empty
const demoConversations = [
  {
    id: 'conv1',
    topic: 'Architecture Discussion: Dashboard Analytics',
    status: 'active' as const,
    participant_count: 2,
    participant_names: ['Sophie', 'Olivia'],
    participants: ['Sophie', 'Olivia'],
    message_count: 24,
    turns_taken: 24,
    max_turns: 50,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    started_at: new Date(Date.now() - 3600000).toISOString(),
    completed_at: null,
  },
  {
    id: 'conv2',
    topic: 'Code Review: Authentication Module',
    status: 'completed' as const,
    participant_count: 2,
    participant_names: ['Sophie', 'Olivia'],
    participants: ['Sophie', 'Olivia'],
    message_count: 18,
    turns_taken: 18,
    max_turns: 30,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    started_at: new Date(Date.now() - 86400000).toISOString(),
    completed_at: new Date(Date.now() - 82800000).toISOString(),
  },
  {
    id: 'conv3',
    topic: 'Sprint Planning: Q1 Features',
    status: 'active' as const,
    participant_count: 2,
    participant_names: ['Sophie', 'Olivia'],
    participants: ['Sophie', 'Olivia'],
    message_count: 12,
    turns_taken: 12,
    max_turns: 40,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    started_at: new Date(Date.now() - 172800000).toISOString(),
    completed_at: null,
  },
] as Conversation[];

// Demo messages organized by conversation
const demoMessagesByConversation: Record<string, ConversationMessage[]> = {
  'conv1': [
    { agent_id: 0, agent_name: 'System', content: 'Conversation started: Architecture Discussion', mentions: [], timestamp: new Date(Date.now() - 3600000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'I\'ve been reviewing the dashboard analytics requirements. I think we should use WebSocket for real-time updates instead of polling. This will reduce server load and provide instant data updates to users.', mentions: [], timestamp: new Date(Date.now() - 3500000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'I agree with the WebSocket approach. From a database perspective, I can set up change data capture (CDC) to push updates to the WebSocket server. We should also consider implementing caching with Redis for frequently accessed metrics.', mentions: [1], timestamp: new Date(Date.now() - 3400000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Good idea! For the frontend, I\'ll use React Query with WebSocket integration. This will handle connection state, automatic reconnection, and caching seamlessly.', mentions: [], timestamp: new Date(Date.now() - 3300000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'I\'ll design the API to support both modes. The endpoints will return data in the same format whether polled or pushed via WebSocket. I estimate we can reduce database queries by 70% with proper caching.', mentions: [], timestamp: new Date(Date.now() - 3200000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Perfect! Let me also suggest using Server-Sent Events (SSE) as a simpler alternative for one-way data streaming.', mentions: [2], timestamp: new Date(Date.now() - 3100000).toISOString() },
  ] as ConversationMessage[],
  'conv2': [
    { agent_id: 0, agent_name: 'System', content: 'Conversation started: Code Review - Authentication Module', mentions: [], timestamp: new Date(Date.now() - 86400000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'I\'ve reviewed the authentication module. Overall, the implementation looks solid. I noticed a few things we should discuss regarding token refresh handling.', mentions: [], timestamp: new Date(Date.now() - 86300000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Thanks for the review! What concerns do you have about the token refresh?', mentions: [2], timestamp: new Date(Date.now() - 86200000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'The current implementation refreshes tokens synchronously, which could cause race conditions if multiple requests happen simultaneously. I suggest implementing a token refresh queue.', mentions: [], timestamp: new Date(Date.now() - 86100000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Good catch! I\'ll implement a mutex-like pattern to ensure only one refresh happens at a time. Other requests can wait for the new token.', mentions: [], timestamp: new Date(Date.now() - 86000000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'That sounds perfect. Also, consider adding a small buffer before token expiry to prevent edge cases where the token expires during the request.', mentions: [1], timestamp: new Date(Date.now() - 85900000).toISOString() },
  ] as ConversationMessage[],
  'conv3': [
    { agent_id: 0, agent_name: 'System', content: 'Conversation started: Sprint Planning - Q1 Features', mentions: [], timestamp: new Date(Date.now() - 172800000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Let\'s prioritize the features for Q1. I think we should focus on completing the dashboard first, then move to the RAG pipeline.', mentions: [], timestamp: new Date(Date.now() - 172700000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'Agreed. The dashboard is almost done. I can start preparing the database schema for the RAG pipeline while you finish the UI components.', mentions: [1], timestamp: new Date(Date.now() - 172600000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'That works well. For the RAG pipeline, we\'ll need vector storage. Have you looked into pgvector vs dedicated vector databases?', mentions: [], timestamp: new Date(Date.now() - 172500000).toISOString() },
    { agent_id: 2, agent_name: 'Olivia', content: 'I\'ve done some research. pgvector would be simpler since we\'re already using PostgreSQL. For our scale, it should perform well. We can always migrate later if needed.', mentions: [], timestamp: new Date(Date.now() - 172400000).toISOString() },
    { agent_id: 1, agent_name: 'Sophie', content: 'Sounds good. Let\'s also add the calendar integration to Q1. It\'s a smaller feature but users have been requesting it.', mentions: [2], timestamp: new Date(Date.now() - 172300000).toISOString() },
  ] as ConversationMessage[],
};

// Get demo messages for a specific conversation
const getDemoMessagesForConversation = (conversationId: string): ConversationMessage[] => {
  return demoMessagesByConversation[conversationId] || demoMessagesByConversation['conv1'];
};

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
  const isSystem = message.agent_id === 0 || message.agent_name === 'System';

  return (
    <div className={`flex ${isSystem ? 'justify-center' : 'justify-start'}`}>
      {isSystem ? (
        <div className="text-xs text-zinc-500 bg-zinc-800/50 px-4 py-2 rounded-full border border-white/5">
          {message.content}
        </div>
      ) : (
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
            <p className="text-sm text-zinc-300 whitespace-pre-wrap leading-relaxed">
              {message.content}
            </p>
          </div>
        </div>
      )}
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

  // Use demo data when API returns empty - use conversation-specific demo messages
  const displayMessages = messagesData?.messages?.length ? messagesData.messages : getDemoMessagesForConversation(conversation.id);

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
  const [selectedAgents, setSelectedAgents] = useState<number[]>([]);
  const [maxTurns, setMaxTurns] = useState(10);
  const [turnStrategy, setTurnStrategy] = useState<TurnStrategy>('round_robin');
  const [facilitatorId, setFacilitatorId] = useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      conversations.create({
        topic,
        agent_ids: selectedAgents,
        max_turns: maxTurns,
        turn_strategy: turnStrategy,
        ...(turnStrategy === 'facilitator_led' && facilitatorId ? { facilitator_id: facilitatorId } : {}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      onClose();
      setTopic('');
      setSelectedAgents([]);
      setMaxTurns(10);
      setTurnStrategy('round_robin');
      setFacilitatorId(null);
    },
  });

  // Reset facilitator when strategy changes or selected agents change
  const handleStrategyChange = (newStrategy: TurnStrategy) => {
    setTurnStrategy(newStrategy);
    if (newStrategy !== 'facilitator_led') {
      setFacilitatorId(null);
    }
  };

  // Get selected agents for facilitator dropdown
  const selectedAgentsList = agentsData?.agents.filter(a => selectedAgents.includes(a.id)) || [];

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
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="glass-card rounded-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center glow-purple">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Start Conversation</h2>
          </div>
          <button
            onClick={onClose}
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
            </label>
            <div className="max-h-48 overflow-y-auto space-y-2 glass-card rounded-xl p-3">
              {agentsData?.agents.map((agent) => (
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
              {agentsData?.agents.length === 0 && (
                <p className="text-sm text-zinc-500 text-center py-6">
                  No agents available. Create some first!
                </p>
              )}
            </div>
          </div>

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
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversations.list,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Use demo data when API returns empty
  const displayConversations = data?.conversations?.length ? data.conversations : demoConversations;

  const deleteMutation = useMutation({
    mutationFn: conversations.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (selectedConversation) {
        setSelectedConversation(null);
      }
    },
  });

  return (
    <div className="h-full flex gap-6">
      {/* Conversations list */}
      <div className="w-80 flex-shrink-0 flex flex-col">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">Conversations</h1>
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
          ) : (
            displayConversations.map((conv) => (
              <ConversationCard
                key={conv.id}
                conversation={conv}
                isSelected={selectedConversation?.id === conv.id}
                onSelect={() => setSelectedConversation(conv)}
                onDelete={() => deleteMutation.mutate(conv.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Conversation detail */}
      <div className="flex-1 glass-card rounded-2xl overflow-hidden">
        {selectedConversation ? (
          <ConversationDetail conversation={selectedConversation} />
        ) : (
          <div className="h-full flex items-center justify-center">
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
