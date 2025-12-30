// Knowledge Base page with Web3 design

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Brain,
  Search,
  Plus,
  FileText,
  Lightbulb,
  Book,
  HelpCircle,
  Tag,
  ExternalLink,
  X,
  Loader2,
  Sparkles,
  Zap,
  ArrowUpRight,
} from 'lucide-react';
import { memories, agents } from '../services/api';
import type { Knowledge, KnowledgeCreate, KnowledgeCategory, Agent } from '../types';

const categoryConfig: Record<KnowledgeCategory, { icon: React.ReactNode; gradient: string; glowClass: string }> = {
  docs: {
    icon: <FileText className="w-4 h-4" />,
    gradient: 'from-blue-500 to-cyan-500',
    glowClass: 'glow-blue',
  },
  best_practice: {
    icon: <Lightbulb className="w-4 h-4" />,
    gradient: 'from-amber-500 to-orange-500',
    glowClass: 'glow-purple',
  },
  decision: {
    icon: <Book className="w-4 h-4" />,
    gradient: 'from-purple-500 to-pink-500',
    glowClass: 'glow-purple',
  },
  faq: {
    icon: <HelpCircle className="w-4 h-4" />,
    gradient: 'from-emerald-500 to-teal-500',
    glowClass: 'glow-green',
  },
};

function KnowledgeCard({ knowledge }: { knowledge: Knowledge }) {
  const [expanded, setExpanded] = useState(false);
  const config = knowledge.category ? categoryConfig[knowledge.category] : null;

  return (
    <div className="glass-card rounded-2xl overflow-hidden glass-card-hover group">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-3">
              {config && (
                <div className={`p-2 rounded-lg bg-gradient-to-br ${config.gradient} ${config.glowClass}`}>
                  {config.icon}
                </div>
              )}
              {knowledge.similarity !== undefined && (
                <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-purple-500/20 border border-purple-500/30">
                  <Sparkles className="w-3 h-3 text-purple-400" />
                  <span className="text-xs font-medium text-purple-300">
                    {Math.round(knowledge.similarity * 100)}% match
                  </span>
                </div>
              )}
            </div>
            <h3 className="font-semibold text-lg text-white group-hover:text-purple-300 transition-colors">
              {knowledge.title}
            </h3>
            <p className={`mt-2 text-sm text-zinc-400 leading-relaxed ${expanded ? '' : 'line-clamp-3'}`}>
              {knowledge.content}
            </p>
            {knowledge.content.length > 200 && (
              <button
                onClick={() => setExpanded(!expanded)}
                className="mt-2 text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1"
              >
                {expanded ? 'Show less' : 'Read more'}
                <ArrowUpRight className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>
        {knowledge.tags && knowledge.tags.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/5 flex flex-wrap gap-2">
            {knowledge.tags.map((tag, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium badge"
              >
                <Tag className="w-3 h-3" />
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AddKnowledgeModal({
  open,
  onClose,
  onAdd,
  agents: agentsList,
}: {
  open: boolean;
  onClose: () => void;
  onAdd: (data: KnowledgeCreate, authorId?: number) => void;
  agents: Agent[];
}) {
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [category, setCategory] = useState<KnowledgeCategory>('docs');
  const [tags, setTags] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [isGlobal, setIsGlobal] = useState(true);
  const [authorId, setAuthorId] = useState<number | undefined>();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({
      title,
      content,
      category,
      tags: tags ? tags.split(',').map(t => t.trim()) : undefined,
      source_url: sourceUrl || undefined,
      is_global: isGlobal,
    }, authorId);
    setTitle('');
    setContent('');
    setCategory('docs');
    setTags('');
    setSourceUrl('');
    setIsGlobal(true);
    setAuthorId(undefined);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay">
      <div className="glass-card rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center glow-purple">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Add Knowledge</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full px-4 py-3 input-glass rounded-xl"
              placeholder="Knowledge entry title"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              rows={5}
              className="w-full px-4 py-3 input-glass rounded-xl resize-none"
              placeholder="Knowledge content..."
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as KnowledgeCategory)}
                className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
              >
                <option value="docs">Documentation</option>
                <option value="best_practice">Best Practice</option>
                <option value="decision">Decision</option>
                <option value="faq">FAQ</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Author Agent
              </label>
              <select
                value={authorId ?? ''}
                onChange={(e) => setAuthorId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
              >
                <option value="">No author</option>
                {agentsList.map((agent) => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full px-4 py-3 input-glass rounded-xl"
              placeholder="api, setup, configuration"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Source URL (optional)
            </label>
            <div className="relative">
              <ExternalLink className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
              <input
                type="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                className="w-full pl-11 pr-4 py-3 input-glass rounded-xl"
                placeholder="https://..."
              />
            </div>
          </div>
          <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/5">
            <input
              type="checkbox"
              id="isGlobal"
              checked={isGlobal}
              onChange={(e) => setIsGlobal(e.target.checked)}
              className="w-5 h-5 rounded border-zinc-600 bg-zinc-800 text-purple-500 focus:ring-purple-500 focus:ring-offset-0"
            />
            <label htmlFor="isGlobal" className="text-sm text-zinc-300">
              Make globally accessible to all agents
            </label>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-gradient px-5 py-2.5 rounded-xl flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Knowledge
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Knowledge() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Knowledge[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<KnowledgeCategory | ''>('');

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
  });

  const searchMutation = useMutation({
    mutationFn: (query: string) => memories.searchKnowledge(query, {
      category: categoryFilter || undefined,
      limit: 20,
      threshold: 0.5,
    }),
    onSuccess: (data) => {
      setSearchResults(data.results);
      setHasSearched(true);
    },
  });

  const addMutation = useMutation({
    mutationFn: ({ data, authorId }: { data: KnowledgeCreate; authorId?: number }) =>
      memories.addKnowledge(data, authorId),
    onSuccess: () => {
      if (hasSearched && searchQuery) {
        searchMutation.mutate(searchQuery);
      }
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery);
    }
  };

  const handleAdd = (data: KnowledgeCreate, authorId?: number) => {
    addMutation.mutate({ data, authorId });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-rose-500 flex items-center justify-center glow-purple">
              <Brain className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Knowledge Base</h1>
              <p className="text-zinc-500 mt-0.5">
                Semantic search powered by RAG
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn-gradient px-5 py-3 rounded-xl flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          Add Knowledge
        </button>
      </div>

      {/* Search */}
      <div className="glass-card rounded-2xl p-6">
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search knowledge base with natural language..."
                className="w-full pl-12 pr-4 py-4 input-glass rounded-xl text-lg"
              />
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as KnowledgeCategory | '')}
              className="px-5 py-4 input-glass rounded-xl appearance-none cursor-pointer min-w-[160px]"
            >
              <option value="">All categories</option>
              <option value="docs">Documentation</option>
              <option value="best_practice">Best Practice</option>
              <option value="decision">Decision</option>
              <option value="faq">FAQ</option>
            </select>
            <button
              type="submit"
              disabled={searchMutation.isPending || !searchQuery.trim()}
              className="btn-gradient px-8 py-4 rounded-xl flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {searchMutation.isPending ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Zap className="w-5 h-5" />
              )}
              <span className="font-semibold">Search</span>
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {hasSearched && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-purple-400" />
              <h2 className="text-xl font-semibold text-white">
                Search Results
              </h2>
            </div>
            <span className="text-sm text-zinc-500 badge px-3 py-1.5 rounded-full">
              {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
            </span>
          </div>

          {searchResults.length === 0 ? (
            <div className="empty-state p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center mx-auto mb-4">
                <Brain className="w-8 h-8 text-zinc-500" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">
                No results found
              </h3>
              <p className="text-zinc-500 max-w-sm mx-auto">
                Try adjusting your search query or add new knowledge entries to expand your base.
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="mt-6 btn-gradient px-5 py-2.5 rounded-xl inline-flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Knowledge
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {searchResults.map((knowledge) => (
                <KnowledgeCard key={knowledge.id} knowledge={knowledge} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Initial state */}
      {!hasSearched && (
        <div className="glass-card rounded-2xl p-12 text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-rose-500 flex items-center justify-center mx-auto mb-6 glow-purple float">
            <Brain className="w-10 h-10 text-white" />
          </div>
          <h3 className="text-2xl font-bold text-white mb-3">
            Explore Your Knowledge Base
          </h3>
          <p className="text-zinc-400 max-w-lg mx-auto mb-8 leading-relaxed">
            Use natural language to search through your knowledge entries. Our semantic search finds conceptually similar content, not just keyword matches.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {(['docs', 'best_practice', 'decision', 'faq'] as KnowledgeCategory[]).map((cat) => {
              const config = categoryConfig[cat];
              return (
                <div
                  key={cat}
                  className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl"
                >
                  <div className={`p-1.5 rounded-lg bg-gradient-to-br ${config.gradient}`}>
                    {config.icon}
                  </div>
                  <span className="text-sm font-medium text-zinc-300 capitalize">
                    {cat.replace('_', ' ')}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Add Modal */}
      <AddKnowledgeModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAdd}
        agents={agentsData?.agents ?? []}
      />
    </div>
  );
}

export default Knowledge;
