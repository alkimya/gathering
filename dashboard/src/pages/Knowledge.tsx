// Knowledge Base page with Web3 design

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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
  Database,
  TrendingUp,
  Clock,
  Upload,
  File,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { memories, agents } from '../services/api';
import type { Knowledge, KnowledgeCreate, KnowledgeCategory, Agent, DocumentUploadResponse } from '../types';

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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-knowledge-title"
    >
      <div className="glass-card rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center glow-purple">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 id="add-knowledge-title" className="text-xl font-bold text-white">Add Knowledge</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
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

const SUPPORTED_FORMATS = ['.md', '.markdown', '.txt', '.csv', '.pdf'];

function UploadDocumentModal({
  open,
  onClose,
  agents: agentsList,
  onSuccess,
}: {
  open: boolean;
  onClose: () => void;
  agents: Agent[];
  onSuccess: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState<KnowledgeCategory>('docs');
  const [tags, setTags] = useState('');
  const [isGlobal, setIsGlobal] = useState(true);
  const [authorId, setAuthorId] = useState<number | undefined>();
  const [dragActive, setDragActive] = useState(false);
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return memories.uploadDocument(file, {
        title: title || undefined,
        category,
        tags: tags ? tags.split(',').map(t => t.trim()) : undefined,
        is_global: isGlobal,
        author_agent_id: authorId,
      });
    },
    onSuccess: (data) => {
      setUploadResult(data);
      setError(null);
      onSuccess();
    },
    onError: (err: Error) => {
      setError(err.message);
      setUploadResult(null);
    },
  });

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (isValidFile(droppedFile)) {
        setFile(droppedFile);
        setError(null);
      } else {
        setError(`Unsupported format. Use: ${SUPPORTED_FORMATS.join(', ')}`);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (isValidFile(selectedFile)) {
        setFile(selectedFile);
        setError(null);
      } else {
        setError(`Unsupported format. Use: ${SUPPORTED_FORMATS.join(', ')}`);
      }
    }
  };

  const isValidFile = (f: File) => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase();
    return SUPPORTED_FORMATS.includes(ext);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (file) {
      uploadMutation.mutate();
    }
  };

  const resetForm = () => {
    setFile(null);
    setTitle('');
    setCategory('docs');
    setTags('');
    setIsGlobal(true);
    setAuthorId(undefined);
    setUploadResult(null);
    setError(null);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 modal-overlay"
      role="dialog"
      aria-modal="true"
    >
      <div className="glass-card rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center glow-blue">
              <Upload className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Upload Document</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors rounded-lg hover:bg-white/5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {uploadResult ? (
          <div className="p-6 space-y-4">
            <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
              <div>
                <p className="font-medium text-white">Upload successful!</p>
                <p className="text-sm text-zinc-400">{uploadResult.filename}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 rounded-lg bg-white/5">
                <p className="text-zinc-500">Format</p>
                <p className="text-white font-medium">{uploadResult.format.toUpperCase()}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/5">
                <p className="text-zinc-500">Characters</p>
                <p className="text-white font-medium">{uploadResult.char_count.toLocaleString()}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/5">
                <p className="text-zinc-500">Chunks</p>
                <p className="text-white font-medium">{uploadResult.chunk_count}</p>
              </div>
              <div className="p-3 rounded-lg bg-white/5">
                <p className="text-zinc-500">Category</p>
                <p className="text-white font-medium capitalize">{uploadResult.category || 'None'}</p>
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
              <button
                onClick={resetForm}
                className="px-5 py-2.5 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors font-medium"
              >
                Upload Another
              </button>
              <button
                onClick={handleClose}
                className="btn-gradient px-5 py-2.5 rounded-xl"
              >
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {/* Drag & Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                dragActive
                  ? 'border-purple-500 bg-purple-500/10'
                  : file
                  ? 'border-emerald-500/50 bg-emerald-500/5'
                  : 'border-zinc-700 hover:border-zinc-600'
              }`}
            >
              <input
                type="file"
                onChange={handleFileChange}
                accept={SUPPORTED_FORMATS.join(',')}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <File className="w-8 h-8 text-emerald-400" />
                  <div className="text-left">
                    <p className="font-medium text-white">{file.name}</p>
                    <p className="text-sm text-zinc-500">{(file.size / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
              ) : (
                <>
                  <Upload className="w-10 h-10 text-zinc-500 mx-auto mb-3" />
                  <p className="text-zinc-300">Drop a file here or click to browse</p>
                  <p className="text-sm text-zinc-500 mt-1">
                    Supports: {SUPPORTED_FORMATS.join(', ')}
                  </p>
                </>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                Title (optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-3 input-glass rounded-xl"
                placeholder="Uses filename if empty"
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

            <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/5">
              <input
                type="checkbox"
                id="uploadIsGlobal"
                checked={isGlobal}
                onChange={(e) => setIsGlobal(e.target.checked)}
                className="w-5 h-5 rounded border-zinc-600 bg-zinc-800 text-purple-500 focus:ring-purple-500 focus:ring-offset-0"
              />
              <label htmlFor="uploadIsGlobal" className="text-sm text-zinc-300">
                Make globally accessible to all agents
              </label>
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-white/5">
              <button
                type="button"
                onClick={handleClose}
                className="px-5 py-2.5 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!file || uploadMutation.isPending}
                className="btn-gradient px-5 py-2.5 rounded-xl flex items-center gap-2 disabled:opacity-50"
              >
                {uploadMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                Upload Document
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export function Knowledge() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Knowledge[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState<KnowledgeCategory | ''>('');
  const queryClient = useQueryClient();

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
  });

  // Fetch knowledge stats
  const { data: statsData, isLoading: statsLoading } = useQuery({
    queryKey: ['knowledge-stats'],
    queryFn: memories.knowledgeStats,
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
      queryClient.invalidateQueries({ queryKey: ['knowledge-stats'] });
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
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowUploadModal(true)}
            className="px-4 py-3 rounded-xl flex items-center gap-2 bg-gradient-to-r from-cyan-500/20 to-blue-500/20 border border-cyan-500/30 text-cyan-300 hover:from-cyan-500/30 hover:to-blue-500/30 hover:text-cyan-200 transition-all"
          >
            <Upload className="w-5 h-5" />
            Upload Doc
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="btn-gradient px-5 py-3 rounded-xl flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            Add Knowledge
          </button>
        </div>
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
                aria-label="Search knowledge base"
                className="w-full pl-12 pr-4 py-4 input-glass rounded-xl text-lg"
              />
            </div>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value as KnowledgeCategory | '')}
              aria-label="Filter by category"
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

      {/* Stats and Overview */}
      {!hasSearched && (
        <div className="space-y-6">
          {/* Stats Cards */}
          {!statsLoading && statsData && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {/* Total */}
              <div className="glass-card rounded-xl p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                    <Database className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{statsData.total_entries}</p>
                    <p className="text-xs text-zinc-500">Total Entries</p>
                  </div>
                </div>
              </div>

              {/* By Category */}
              {Object.entries(statsData.by_category || {}).map(([cat, count]) => {
                const config = categoryConfig[cat as KnowledgeCategory];
                return (
                  <div key={cat} className="glass-card rounded-xl p-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config?.gradient || 'from-zinc-500 to-zinc-600'} flex items-center justify-center`}>
                        {config?.icon || <FileText className="w-5 h-5 text-white" />}
                      </div>
                      <div>
                        <p className="text-2xl font-bold text-white">{count as number}</p>
                        <p className="text-xs text-zinc-500 capitalize">{cat.replace('_', ' ')}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Recent Entries */}
          {!statsLoading && statsData && statsData.recent_entries.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-cyan-400" />
                <h2 className="text-xl font-semibold text-white">Recent Entries</h2>
              </div>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {statsData.recent_entries.map((knowledge) => (
                  <KnowledgeCard key={knowledge.id} knowledge={knowledge} />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!statsLoading && (!statsData || statsData.total_entries === 0) && (
            <div className="glass-card rounded-2xl p-12 text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-500 via-pink-500 to-rose-500 flex items-center justify-center mx-auto mb-6 glow-purple float">
                <Brain className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-2xl font-bold text-white mb-3">
                Start Building Your Knowledge Base
              </h3>
              <p className="text-zinc-400 max-w-lg mx-auto mb-8 leading-relaxed">
                Add documentation, best practices, and FAQs. Our semantic search will help you find relevant content using natural language.
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="btn-gradient px-6 py-3 rounded-xl inline-flex items-center gap-2"
              >
                <Plus className="w-5 h-5" />
                Add Your First Entry
              </button>
            </div>
          )}

          {/* Category Pills */}
          {!statsLoading && statsData && statsData.total_entries > 0 && (
            <div className="glass-card rounded-2xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <TrendingUp className="w-5 h-5 text-purple-400" />
                <h3 className="text-lg font-semibold text-white">Browse by Category</h3>
              </div>
              <div className="flex flex-wrap gap-3">
                {(['docs', 'best_practice', 'decision', 'faq'] as KnowledgeCategory[]).map((cat) => {
                  const config = categoryConfig[cat];
                  const count = statsData.by_category?.[cat] || 0;
                  return (
                    <button
                      key={cat}
                      onClick={() => {
                        setCategoryFilter(cat);
                        setSearchQuery(`category:${cat}`);
                        searchMutation.mutate(`category:${cat}`);
                      }}
                      className="flex items-center gap-2 px-4 py-2.5 glass-card rounded-xl hover:bg-white/5 transition-colors group"
                    >
                      <div className={`p-1.5 rounded-lg bg-gradient-to-br ${config.gradient}`}>
                        {config.icon}
                      </div>
                      <span className="text-sm font-medium text-zinc-300 capitalize group-hover:text-white transition-colors">
                        {cat.replace('_', ' ')}
                      </span>
                      <span className="text-xs text-zinc-500 ml-1">({count})</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Modal */}
      <AddKnowledgeModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAdd}
        agents={agentsData?.agents ?? []}
      />

      {/* Upload Modal */}
      <UploadDocumentModal
        open={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        agents={agentsData?.agents ?? []}
        onSuccess={() => queryClient.invalidateQueries({ queryKey: ['knowledge-stats'] })}
      />
    </div>
  );
}

export default Knowledge;
