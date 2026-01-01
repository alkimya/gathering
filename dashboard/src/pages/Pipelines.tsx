// Pipelines page - Visual workflow automation for multi-agent orchestration

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  GitBranch,
  Plus,
  Play,
  Pause,
  Square,
  Settings,
  Trash2,
  Copy,
  MoreHorizontal,
  Bot,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
  ArrowRight,
  Filter,
  RefreshCw,
  Eye,
  Edit3,
  X,
  AlertCircle,
} from 'lucide-react';
import { pipelines as pipelinesApi, agents as agentsApi } from '../services/api';
import { PipelineEditor } from '../components/PipelineEditor';
import { useToast } from '../components/Toast';
import type {
  Pipeline,
  PipelineNode,
  PipelineStatus,
  PipelineNodeType,
} from '../types';

// Node type configurations
const nodeTypeConfig: Record<PipelineNodeType, { icon: React.ReactNode; color: string; bg: string; border: string }> = {
  trigger: { icon: <Zap className="w-4 h-4" />, color: 'text-amber-400', bg: 'bg-amber-500/20', border: 'border-amber-500/30' },
  agent: { icon: <Bot className="w-4 h-4" />, color: 'text-purple-400', bg: 'bg-purple-500/20', border: 'border-purple-500/30' },
  condition: { icon: <GitBranch className="w-4 h-4" />, color: 'text-cyan-400', bg: 'bg-cyan-500/20', border: 'border-cyan-500/30' },
  action: { icon: <Play className="w-4 h-4" />, color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30' },
  parallel: { icon: <Copy className="w-4 h-4" />, color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
  delay: { icon: <Clock className="w-4 h-4" />, color: 'text-zinc-400', bg: 'bg-zinc-500/20', border: 'border-zinc-500/30' },
};

const statusConfig = {
  active: { icon: <Play className="w-3 h-3" />, color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
  paused: { icon: <Pause className="w-3 h-3" />, color: 'text-amber-400', bg: 'bg-amber-500/20' },
  draft: { icon: <Edit3 className="w-3 h-3" />, color: 'text-zinc-400', bg: 'bg-zinc-500/20' },
};

const runStatusConfig = {
  pending: { icon: <Clock className="w-4 h-4" />, color: 'text-zinc-400', bg: 'bg-zinc-500/20' },
  running: { icon: <RefreshCw className="w-4 h-4 animate-spin" />, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  completed: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
  failed: { icon: <XCircle className="w-4 h-4" />, color: 'text-red-400', bg: 'bg-red-500/20' },
  cancelled: { icon: <Square className="w-4 h-4" />, color: 'text-zinc-400', bg: 'bg-zinc-500/20' },
};

// Pipeline Node Component (simplified visual)
function PipelineNodeVisual({ node }: { node: PipelineNode }) {
  const config = nodeTypeConfig[node.type];

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${config.bg} ${config.border}`}>
      <span className={config.color}>{config.icon}</span>
      <span className="text-sm text-zinc-200">{node.name}</span>
    </div>
  );
}

// Pipeline Card Component
function PipelineCard({
  pipeline,
  onView,
  onEdit,
  onToggle,
  onDelete,
  onRun,
}: {
  pipeline: Pipeline;
  onView: () => void;
  onEdit: () => void;
  onToggle: () => void;
  onDelete: () => void;
  onRun: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const status = statusConfig[pipeline.status];
  const successRate = pipeline.run_count > 0
    ? Math.round((pipeline.success_count / pipeline.run_count) * 100)
    : null;

  return (
    <div className="glass-card rounded-xl p-5 hover:bg-white/5 transition-all">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-purple-500/20">
            <GitBranch className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">{pipeline.name}</h3>
            {pipeline.description && (
              <p className="text-sm text-zinc-500 mt-0.5">{pipeline.description}</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`flex items-center gap-1 px-2 py-1 rounded-full text-xs ${status.bg} ${status.color}`}>
            {status.icon}
            {pipeline.status}
          </span>

          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 text-zinc-500 hover:text-white transition-colors rounded-lg hover:bg-white/5"
            >
              <MoreHorizontal className="w-4 h-4" />
            </button>

            {showMenu && (
              <div className="absolute right-0 top-8 z-10 w-44 glass-card rounded-xl shadow-xl border border-white/10 py-2">
                <button
                  onClick={() => { onView(); setShowMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                >
                  <Eye className="w-4 h-4" /> View Details
                </button>
                <button
                  onClick={() => { onEdit(); setShowMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                >
                  <Edit3 className="w-4 h-4" /> Edit Pipeline
                </button>
                <button
                  onClick={() => { onToggle(); setShowMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
                >
                  {pipeline.status === 'active' ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  {pipeline.status === 'active' ? 'Pause' : 'Activate'}
                </button>
                <hr className="my-2 border-white/10" />
                <button
                  onClick={() => { onDelete(); setShowMenu(false); }}
                  className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                >
                  <Trash2 className="w-4 h-4" /> Delete
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pipeline Flow Preview */}
      <div className="flex items-center gap-2 overflow-x-auto py-3 mb-4">
        {pipeline.nodes.slice(0, 5).map((node, i) => (
          <div key={node.id} className="flex items-center gap-2">
            <PipelineNodeVisual node={node} />
            {i < Math.min(pipeline.nodes.length - 1, 4) && (
              <ArrowRight className="w-4 h-4 text-zinc-600 flex-shrink-0" />
            )}
          </div>
        ))}
        {pipeline.nodes.length > 5 && (
          <span className="text-xs text-zinc-500">+{pipeline.nodes.length - 5} more</span>
        )}
        {pipeline.nodes.length === 0 && (
          <span className="text-sm text-zinc-500 italic">No nodes configured</span>
        )}
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between pt-4 border-t border-white/5">
        <div className="flex items-center gap-4 text-sm">
          <span className="text-zinc-400">
            <span className="text-white font-medium">{pipeline.run_count}</span> runs
          </span>
          {successRate !== null && (
            <span className={successRate >= 90 ? 'text-emerald-400' : successRate >= 70 ? 'text-amber-400' : 'text-red-400'}>
              {successRate}% success
            </span>
          )}
          {pipeline.last_run && (
            <span className="text-zinc-500 flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatRelativeTime(pipeline.last_run)}
            </span>
          )}
        </div>

        <button
          onClick={onRun}
          disabled={pipeline.status !== 'active'}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            pipeline.status === 'active'
              ? 'bg-purple-500/20 text-purple-400 hover:bg-purple-500/30'
              : 'bg-zinc-700/30 text-zinc-600 cursor-not-allowed'
          }`}
        >
          <Play className="w-4 h-4" />
          Run Now
        </button>
      </div>
    </div>
  );
}

// Pipeline Detail Modal
function PipelineDetailModal({
  pipeline,
  onClose,
}: {
  pipeline: Pipeline;
  onClose: () => void;
}) {
  const [activeTab, setActiveTab] = useState<'overview' | 'runs' | 'logs'>('overview');

  const { data: runsData } = useQuery({
    queryKey: ['pipeline-runs', pipeline.id],
    queryFn: () => pipelinesApi.getRuns(pipeline.id),
    enabled: activeTab === 'runs' || activeTab === 'logs',
  });

  const runs = runsData?.runs || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-hidden glass-card rounded-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-purple-500/20">
              <GitBranch className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{pipeline.name}</h2>
              {pipeline.description && (
                <p className="text-sm text-zinc-400">{pipeline.description}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-2 mx-6 mt-4 rounded-xl bg-zinc-800/50">
          {(['overview', 'runs', 'logs'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-4 gap-4">
                <div className="glass-card rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-white">{pipeline.run_count}</p>
                  <p className="text-xs text-zinc-500">Total Runs</p>
                </div>
                <div className="glass-card rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-emerald-400">{pipeline.success_count}</p>
                  <p className="text-xs text-zinc-500">Successful</p>
                </div>
                <div className="glass-card rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-red-400">{pipeline.error_count}</p>
                  <p className="text-xs text-zinc-500">Failed</p>
                </div>
                <div className="glass-card rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-white">{pipeline.nodes.length}</p>
                  <p className="text-xs text-zinc-500">Nodes</p>
                </div>
              </div>

              {/* Pipeline Flow */}
              <div>
                <h3 className="text-sm font-semibold text-zinc-400 mb-3">Pipeline Flow</h3>
                <div className="glass-card rounded-xl p-4">
                  <div className="flex flex-wrap items-center gap-3">
                    {pipeline.nodes.map((node, i) => (
                      <div key={node.id} className="flex items-center gap-2">
                        <PipelineNodeVisual node={node} />
                        {i < pipeline.nodes.length - 1 && (
                          <ArrowRight className="w-4 h-4 text-zinc-600" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Nodes Detail */}
              <div>
                <h3 className="text-sm font-semibold text-zinc-400 mb-3">Nodes Configuration</h3>
                <div className="space-y-2">
                  {pipeline.nodes.map((node) => {
                    const config = nodeTypeConfig[node.type];
                    return (
                      <div key={node.id} className="glass-card rounded-xl p-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${config.bg}`}>
                            <span className={config.color}>{config.icon}</span>
                          </div>
                          <div>
                            <p className="font-medium text-zinc-200">{node.name}</p>
                            <p className="text-xs text-zinc-500 capitalize">{node.type}</p>
                          </div>
                        </div>
                        <button className="p-2 text-zinc-500 hover:text-white transition-colors">
                          <Settings className="w-4 h-4" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'runs' && (
            <div className="space-y-3">
              {runs.length === 0 ? (
                <div className="text-center py-12">
                  <Play className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                  <p className="text-zinc-400">No runs yet</p>
                </div>
              ) : (
                runs.map((run) => {
                  const config = runStatusConfig[run.status];

                  return (
                    <div key={run.id} className="glass-card rounded-xl p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-lg ${config.bg}`}>
                            <span className={config.color}>{config.icon}</span>
                          </div>
                          <div>
                            <p className="font-medium text-zinc-200">Run #{run.id}</p>
                            <p className="text-xs text-zinc-500">
                              {run.started_at ? new Date(run.started_at).toLocaleString('fr-FR') : 'Not started'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4 text-sm">
                          {run.duration_seconds > 0 && (
                            <span className="text-zinc-400">{run.duration_seconds}s</span>
                          )}
                          <span className={`px-2 py-1 rounded-full ${config.bg} ${config.color}`}>
                            {run.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {activeTab === 'logs' && (
            <div className="glass-card rounded-xl p-4 font-mono text-sm">
              {runs[0]?.logs && runs[0].logs.length > 0 ? (
                runs[0].logs.map((log, i) => (
                  <div
                    key={i}
                    className={`py-1 ${
                      log.level === 'error' ? 'text-red-400' :
                      log.level === 'warn' ? 'text-amber-400' :
                      'text-zinc-400'
                    }`}
                  >
                    <span className="text-zinc-600">
                      [{new Date(log.timestamp).toLocaleTimeString('fr-FR')}]
                    </span>{' '}
                    <span className="text-zinc-500">[{log.node_id}]</span>{' '}
                    {log.message}
                  </div>
                ))
              ) : (
                <p className="text-zinc-500 text-center py-8">No logs available</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('fr-FR');
}

export function Pipelines() {
  const [filter, setFilter] = useState<'all' | PipelineStatus>('all');
  const [selectedPipeline, setSelectedPipeline] = useState<Pipeline | null>(null);
  const [editingPipeline, setEditingPipeline] = useState<Pipeline | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const queryClient = useQueryClient();
  const toast = useToast();

  // Fetch pipelines
  const { data: pipelinesData, isLoading, error } = useQuery({
    queryKey: ['pipelines', filter === 'all' ? undefined : filter],
    queryFn: () => pipelinesApi.list(filter === 'all' ? undefined : filter),
  });

  // Fetch agents for the editor
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.list(),
  });

  // Use API data
  const pipelines = pipelinesData?.pipelines || [];
  const agents = agentsData?.agents || [];

  // Mutations
  const createMutation = useMutation({
    mutationFn: pipelinesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline created', 'Your pipeline has been saved');
      setIsCreating(false);
    },
    onError: (error) => {
      toast.error('Error', error instanceof Error ? error.message : 'Failed to create pipeline');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Pipeline> }) =>
      pipelinesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline updated', 'Changes have been saved');
      setEditingPipeline(null);
    },
    onError: (error) => {
      toast.error('Error', error instanceof Error ? error.message : 'Failed to update pipeline');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: pipelinesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline deleted', 'Pipeline has been removed');
    },
    onError: (error) => {
      toast.error('Error', error instanceof Error ? error.message : 'Failed to delete pipeline');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: pipelinesApi.toggle,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Status changed', `Pipeline is now ${data.status}`);
    },
    onError: (error) => {
      toast.error('Error', error instanceof Error ? error.message : 'Failed to toggle pipeline');
    },
  });

  const runMutation = useMutation({
    mutationFn: (id: number) => pipelinesApi.run(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] });
      toast.success('Pipeline started', 'Execution has begun');
    },
    onError: (error) => {
      toast.error('Error', error instanceof Error ? error.message : 'Failed to run pipeline');
    },
  });

  // Stats
  const stats = {
    total: pipelines.length,
    active: pipelines.filter(p => p.status === 'active').length,
    totalRuns: pipelines.reduce((sum, p) => sum + p.run_count, 0),
    successRate: pipelines.reduce((sum, p) => sum + p.success_count, 0) /
      Math.max(pipelines.reduce((sum, p) => sum + p.run_count, 0), 1) * 100,
  };

  // Handle save from editor
  const handleSave = async (data: Partial<Pipeline>) => {
    if (editingPipeline && editingPipeline.id > 0) {
      // Update existing pipeline
      await updateMutation.mutateAsync({ id: editingPipeline.id, data });
    } else {
      // Create new pipeline (including copies from demo templates with id=0)
      await createMutation.mutateAsync(data as { name: string });
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="w-12 h-12 text-red-400" />
        <p className="text-zinc-400">Failed to load pipelines</p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['pipelines'] })}
          className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-xl hover:bg-purple-500/30"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <GitBranch className="w-8 h-8 text-purple-400" />
            Pipelines
          </h1>
          <p className="text-zinc-400 mt-1">
            Automated workflows for multi-agent orchestration
          </p>
        </div>

        <button
          onClick={() => setIsCreating(true)}
          className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2"
        >
          <Plus className="w-5 h-5" />
          New Pipeline
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <GitBranch className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-xs text-zinc-500">Total Pipelines</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/20">
              <Play className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.active}</p>
              <p className="text-xs text-zinc-500">Active</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <Zap className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.totalRuns}</p>
              <p className="text-xs text-zinc-500">Total Runs</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <CheckCircle className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.successRate.toFixed(0)}%</p>
              <p className="text-xs text-zinc-500">Success Rate</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-zinc-500" />
        {(['all', 'active', 'paused', 'draft'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              filter === f
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700/50'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Pipeline List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {pipelines.length === 0 ? (
          <div className="col-span-2 glass-card rounded-xl p-12 text-center">
            <GitBranch className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400">No pipelines found</p>
            <button
              onClick={() => setIsCreating(true)}
              className="mt-4 btn-gradient px-4 py-2 rounded-xl"
            >
              Create your first pipeline
            </button>
          </div>
        ) : (
          pipelines.map((pipeline) => (
            <PipelineCard
              key={pipeline.id}
              pipeline={pipeline}
              onView={() => setSelectedPipeline(pipeline)}
              onEdit={() => setEditingPipeline(pipeline)}
              onToggle={() => toggleMutation.mutate(pipeline.id)}
              onDelete={() => {
                if (confirm('Are you sure you want to delete this pipeline?')) {
                  deleteMutation.mutate(pipeline.id);
                }
              }}
              onRun={() => runMutation.mutate(pipeline.id)}
            />
          ))
        )}
      </div>

      {/* Detail Modal */}
      {selectedPipeline && (
        <PipelineDetailModal
          pipeline={selectedPipeline}
          onClose={() => setSelectedPipeline(null)}
        />
      )}

      {/* Editor Modal */}
      {(isCreating || editingPipeline) && (
        <PipelineEditor
          pipeline={editingPipeline}
          agents={agents}
          onSave={handleSave}
          onClose={() => {
            setIsCreating(false);
            setEditingPipeline(null);
          }}
          isNew={isCreating}
        />
      )}
    </div>
  );
}

export default Pipelines;
