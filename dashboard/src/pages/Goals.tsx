// Agent Goals page - hierarchical goal tracking with decomposition

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Target,
  Plus,
  Play,
  Pause,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  ChevronRight,
  ChevronDown,
  Clock,
  Bot,
  GitBranch,
  Trash2,
  Link2,
  Activity,
} from 'lucide-react';
import { goals, agents } from '../services/api';
import type { Goal, GoalCreate, GoalStatus, GoalPriority, Agent, GoalActivity } from '../types';

// Demo data for when API returns empty
const demoGoals = [
  {
    id: 1,
    agent_id: 1,
    agent_name: 'Sophie',
    title: 'Implement Real-time Dashboard Analytics',
    description: 'Create a comprehensive analytics system with WebSocket-based real-time updates, interactive charts, and customizable widgets.',
    status: 'active' as const,
    priority: 'high' as const,
    progress_percent: 65,
    status_message: 'Working on chart components...',
    is_decomposed: true,
    subgoal_count: 4,
    completed_subgoals: 2,
    blocking_count: 0,
    attempts: 3,
    max_attempts: 10,
    estimated_hours: 16,
    actual_hours: 10,
    depth: 0,
    artifacts: [],
    tags: ['frontend', 'analytics', 'real-time'],
    created_at: new Date(Date.now() - 172800000).toISOString(),
  },
  {
    id: 2,
    agent_id: 2,
    agent_name: 'Olivia',
    title: 'Optimize Database Query Performance',
    description: 'Analyze and optimize slow database queries, add proper indexing, and implement query caching where appropriate.',
    status: 'completed' as const,
    priority: 'high' as const,
    progress_percent: 100,
    status_message: 'All queries optimized successfully',
    result_summary: 'Reduced average query time by 60%. Added 12 new indexes. Implemented Redis caching for frequently accessed data.',
    is_decomposed: false,
    subgoal_count: 0,
    completed_subgoals: 0,
    blocking_count: 0,
    attempts: 2,
    max_attempts: 5,
    estimated_hours: 8,
    actual_hours: 6,
    depth: 0,
    artifacts: [],
    tags: ['database', 'performance', 'optimization'],
    created_at: new Date(Date.now() - 604800000).toISOString(),
    completed_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 3,
    agent_id: 1,
    agent_name: 'Sophie',
    title: 'Write Unit Tests for Authentication Module',
    description: 'Create comprehensive unit tests covering login, logout, password reset, and session management flows.',
    status: 'pending' as const,
    priority: 'medium' as const,
    progress_percent: 0,
    is_decomposed: false,
    subgoal_count: 0,
    completed_subgoals: 0,
    blocking_count: 1,
    attempts: 0,
    max_attempts: 5,
    estimated_hours: 6,
    actual_hours: 0,
    depth: 0,
    artifacts: [],
    tags: ['testing', 'auth'],
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: 4,
    agent_id: 2,
    agent_name: 'Olivia',
    title: 'Implement RAG Pipeline for Knowledge Base',
    description: 'Set up a retrieval-augmented generation pipeline for the knowledge base with vector embeddings and semantic search.',
    status: 'active' as const,
    priority: 'critical' as const,
    progress_percent: 35,
    status_message: 'Configuring vector database...',
    is_decomposed: true,
    subgoal_count: 5,
    completed_subgoals: 1,
    blocking_count: 0,
    attempts: 1,
    max_attempts: 8,
    estimated_hours: 20,
    actual_hours: 7,
    depth: 0,
    artifacts: [],
    tags: ['rag', 'ai', 'knowledge-base'],
    created_at: new Date(Date.now() - 259200000).toISOString(),
  },
] as Goal[];

// Status badge component
function StatusBadge({ status }: { status: GoalStatus }) {
  const config: Record<GoalStatus, { color: string; icon: typeof CheckCircle2 }> = {
    pending: { color: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30', icon: Clock },
    active: { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: Play },
    blocked: { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', icon: AlertCircle },
    paused: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Pause },
    completed: { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: CheckCircle2 },
    failed: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: XCircle },
    cancelled: { color: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30', icon: XCircle },
  };

  const { color, icon: Icon } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}

// Priority badge
function PriorityBadge({ priority }: { priority: GoalPriority }) {
  const colors: Record<GoalPriority, string> = {
    low: 'text-zinc-400',
    medium: 'text-blue-400',
    high: 'text-orange-400',
    critical: 'text-red-400',
  };

  return (
    <span className={`text-xs font-medium uppercase ${colors[priority]}`}>
      {priority}
    </span>
  );
}

// Progress bar
function ProgressBar({ percent }: { percent: number }) {
  const color = percent >= 100 ? 'bg-emerald-500' : percent >= 50 ? 'bg-blue-500' : 'bg-purple-500';

  return (
    <div className="w-full h-2 bg-zinc-800 rounded-full overflow-hidden">
      <div
        className={`h-full ${color} transition-all duration-300`}
        style={{ width: `${Math.min(100, percent)}%` }}
      />
    </div>
  );
}

// Goal Tree Item (recursive)
function GoalTreeItem({
  goal,
  level = 0,
  onStart,
  onPause,
  onResume,
  onComplete,
  onDelete,
  onDecompose,
  onViewDetails,
}: {
  goal: Goal;
  level?: number;
  onStart: (id: number) => void;
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onComplete: (id: number) => void;
  onDelete: (id: number) => void;
  onDecompose: (id: number) => void;
  onViewDetails: (goal: Goal) => void;
}) {
  const [expanded, setExpanded] = useState(level === 0);

  const { data: subgoals } = useQuery({
    queryKey: ['goal-subgoals', goal.id],
    queryFn: () => goals.getSubgoals(goal.id),
    enabled: expanded && goal.subgoal_count > 0,
  });

  const hasSubgoals = goal.subgoal_count > 0;

  return (
    <div className={level > 0 ? 'ml-6 border-l border-white/10 pl-4' : ''}>
      <div className="glass-card rounded-xl p-4 mb-2">
        <div className="flex items-start gap-3">
          {/* Expand/Collapse */}
          {hasSubgoals ? (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 text-zinc-400 hover:text-white transition-colors shrink-0 mt-0.5"
            >
              {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
            </button>
          ) : (
            <div className="w-6" />
          )}

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3
                className="font-semibold text-white truncate cursor-pointer hover:text-purple-300 transition-colors"
                onClick={() => onViewDetails(goal)}
              >
                {goal.title}
              </h3>
              <StatusBadge status={goal.status} />
              <PriorityBadge priority={goal.priority} />
              {goal.is_decomposed && (
                <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded-full flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  {goal.completed_subgoals}/{goal.subgoal_count}
                </span>
              )}
              {goal.blocking_count > 0 && (
                <span className="px-2 py-0.5 bg-orange-500/20 text-orange-300 text-xs rounded-full flex items-center gap-1">
                  <Link2 className="w-3 h-3" />
                  {goal.blocking_count} blocked
                </span>
              )}
            </div>

            {goal.status_message && (
              <p className="text-sm text-zinc-400 mt-1 truncate">{goal.status_message}</p>
            )}

            {/* Progress */}
            <div className="mt-2 flex items-center gap-3">
              <div className="flex-1">
                <ProgressBar percent={goal.progress_percent} />
              </div>
              <span className="text-xs text-zinc-400 shrink-0">{goal.progress_percent}%</span>
            </div>

            {/* Meta */}
            <div className="mt-2 flex items-center gap-4 text-xs text-zinc-500">
              <span className="flex items-center gap-1">
                <Bot className="w-3 h-3" />
                {goal.agent_name || `Agent #${goal.agent_id}`}
              </span>
              {goal.deadline && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(goal.deadline).toLocaleDateString()}
                </span>
              )}
              {goal.estimated_hours && (
                <span>{goal.estimated_hours}h est.</span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-1 shrink-0">
            {goal.status === 'pending' && (
              <button
                onClick={() => onStart(goal.id)}
                className="p-2 text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                title="Start"
              >
                <Play className="w-4 h-4" />
              </button>
            )}
            {goal.status === 'active' && (
              <>
                <button
                  onClick={() => onPause(goal.id)}
                  className="p-2 text-zinc-400 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
                  title="Pause"
                >
                  <Pause className="w-4 h-4" />
                </button>
                <button
                  onClick={() => onComplete(goal.id)}
                  className="p-2 text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                  title="Complete"
                >
                  <CheckCircle2 className="w-4 h-4" />
                </button>
              </>
            )}
            {goal.status === 'paused' && (
              <button
                onClick={() => onResume(goal.id)}
                className="p-2 text-zinc-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-lg transition-colors"
                title="Resume"
              >
                <Play className="w-4 h-4" />
              </button>
            )}
            {!goal.is_decomposed && goal.status === 'pending' && (
              <button
                onClick={() => onDecompose(goal.id)}
                className="p-2 text-zinc-400 hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-colors"
                title="Decompose into subgoals"
              >
                <GitBranch className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => onDelete(goal.id)}
              className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Subgoals */}
      {expanded && subgoals && subgoals.subgoals && subgoals.subgoals.length > 0 && (
        <div className="mt-2">
          {subgoals.subgoals.map((subgoal: Goal) => (
            <GoalTreeItem
              key={subgoal.id}
              goal={subgoal}
              level={level + 1}
              onStart={onStart}
              onPause={onPause}
              onResume={onResume}
              onComplete={onComplete}
              onDelete={onDelete}
              onDecompose={onDecompose}
              onViewDetails={onViewDetails}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// Goal Detail Modal
function GoalDetailModal({
  goal,
  onClose,
}: {
  goal: Goal;
  onClose: () => void;
}) {
  const { data: activities, isLoading: loadingActivities } = useQuery({
    queryKey: ['goal-activities', goal.id],
    queryFn: () => goals.getActivities(goal.id),
  });

  const { data: dependencies } = useQuery({
    queryKey: ['goal-dependencies', goal.id],
    queryFn: () => goals.getDependencies(goal.id),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 modal-overlay" onClick={onClose} />
      <div className="relative glass-card rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-white/5">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-xl font-bold text-white">{goal.title}</h2>
              <div className="flex items-center gap-2 mt-2">
                <StatusBadge status={goal.status} />
                <PriorityBadge priority={goal.priority} />
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-white transition-colors"
            >
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium text-zinc-400 mb-2">Description</h3>
            <p className="text-zinc-300 bg-zinc-800/50 rounded-lg p-3">{goal.description}</p>
          </div>

          {/* Success Criteria */}
          {goal.success_criteria && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-2">Success Criteria</h3>
              <p className="text-zinc-300 bg-zinc-800/50 rounded-lg p-3">{goal.success_criteria}</p>
            </div>
          )}

          {/* Progress */}
          <div>
            <h3 className="text-sm font-medium text-zinc-400 mb-2">Progress</h3>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <ProgressBar percent={goal.progress_percent} />
              </div>
              <span className="text-lg font-bold text-white">{goal.progress_percent}%</span>
            </div>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-xs text-zinc-500">Attempts</p>
              <p className="text-lg font-bold text-white">{goal.attempts}/{goal.max_attempts}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-xs text-zinc-500">Subgoals</p>
              <p className="text-lg font-bold text-white">{goal.completed_subgoals}/{goal.subgoal_count}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-xs text-zinc-500">Estimated</p>
              <p className="text-lg font-bold text-white">{goal.estimated_hours || '-'}h</p>
            </div>
            <div className="bg-zinc-800/50 rounded-lg p-3">
              <p className="text-xs text-zinc-500">Actual</p>
              <p className="text-lg font-bold text-white">{goal.actual_hours || '0'}h</p>
            </div>
          </div>

          {/* Dependencies */}
          {dependencies && dependencies.dependencies && dependencies.dependencies.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Dependencies ({dependencies.dependencies.length})
              </h3>
              <div className="space-y-2">
                {dependencies.dependencies.map((dep: Goal) => (
                  <div key={dep.id} className="flex items-center gap-3 bg-zinc-800/50 rounded-lg p-2">
                    <StatusBadge status={dep.status} />
                    <span className="text-sm text-zinc-300">{dep.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Activity Log */}
          <div>
            <h3 className="text-sm font-medium text-zinc-400 mb-2 flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Activity Log
            </h3>
            {loadingActivities ? (
              <p className="text-zinc-500 text-sm">Loading...</p>
            ) : activities && activities.activities && activities.activities.length > 0 ? (
              <div className="space-y-2 max-h-48 overflow-auto">
                {activities.activities.map((activity: GoalActivity) => (
                  <div key={activity.id} className="flex items-center gap-3 text-sm p-2 bg-zinc-800/50 rounded-lg">
                    <span className="text-xs text-zinc-500 shrink-0">
                      {new Date(activity.created_at || '').toLocaleString()}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 text-xs rounded">
                      {activity.activity_type}
                    </span>
                    <span className="text-zinc-400 truncate">
                      {activity.description || `${activity.old_value} → ${activity.new_value}`}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-zinc-500 text-sm">No activity yet</p>
            )}
          </div>

          {/* Result */}
          {goal.result_summary && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-2">Result</h3>
              <p className="text-zinc-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
                {goal.result_summary}
              </p>
            </div>
          )}

          {/* Tags */}
          {goal.tags && goal.tags.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-zinc-400 mb-2">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {goal.tags.map((tag, i) => (
                  <span key={i} className="px-2 py-1 bg-zinc-800 text-zinc-300 text-xs rounded">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Create Goal Modal
function CreateGoalModal({
  isOpen,
  onClose,
  agentsList,
}: {
  isOpen: boolean;
  onClose: () => void;
  agentsList: Agent[];
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<GoalCreate>>({
    priority: 'medium',
    tags: [],
  });

  const createMutation = useMutation({
    mutationFn: (data: GoalCreate) => goals.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['goals'] });
      onClose();
      setFormData({ priority: 'medium', tags: [] });
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.agent_id || !formData.title || !formData.description) return;
    createMutation.mutate(formData as GoalCreate);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 modal-overlay" onClick={onClose} />
      <div className="relative glass-card rounded-2xl w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-white/5">
          <h2 className="text-xl font-bold text-white">Create Goal</h2>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Agent Selection */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Agent</label>
            <select
              value={formData.agent_id || ''}
              onChange={(e) => setFormData({ ...formData, agent_id: Number(e.target.value) })}
              className="w-full px-3 py-2 input-glass rounded-lg"
              required
            >
              <option value="">Select an agent</option>
              {agentsList.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name} ({agent.role})
                </option>
              ))}
            </select>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Title</label>
            <input
              type="text"
              value={formData.title || ''}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg"
              placeholder="Implement user authentication"
              required
              maxLength={255}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Description</label>
            <textarea
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg resize-none"
              rows={3}
              placeholder="Detailed description of what needs to be accomplished"
              required
            />
          </div>

          {/* Success Criteria */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Success Criteria (optional)</label>
            <textarea
              value={formData.success_criteria || ''}
              onChange={(e) => setFormData({ ...formData, success_criteria: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg resize-none"
              rows={2}
              placeholder="How do we know when this goal is complete?"
            />
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Priority</label>
            <div className="grid grid-cols-4 gap-2">
              {(['low', 'medium', 'high', 'critical'] as GoalPriority[]).map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setFormData({ ...formData, priority: p })}
                  className={`p-2 rounded-lg border text-sm capitalize transition-colors ${
                    formData.priority === p
                      ? 'border-purple-500 bg-purple-500/20 text-purple-300'
                      : 'border-white/10 hover:border-white/20 text-zinc-400'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced Options */}
          <details className="group">
            <summary className="cursor-pointer text-sm text-zinc-400 hover:text-white transition-colors">
              Advanced Options
            </summary>
            <div className="mt-4 space-y-4 pl-4 border-l border-white/10">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Deadline</label>
                <input
                  type="datetime-local"
                  value={formData.deadline || ''}
                  onChange={(e) => setFormData({ ...formData, deadline: e.target.value })}
                  className="w-full px-3 py-2 input-glass rounded-lg"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Estimated Hours</label>
                <input
                  type="number"
                  value={formData.estimated_hours || ''}
                  onChange={(e) => setFormData({ ...formData, estimated_hours: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full px-3 py-2 input-glass rounded-lg"
                  min={0}
                  step={0.5}
                  placeholder="0"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={(formData.tags || []).join(', ')}
                  onChange={(e) => setFormData({ ...formData, tags: e.target.value.split(',').map(t => t.trim()).filter(Boolean) })}
                  className="w-full px-3 py-2 input-glass rounded-lg"
                  placeholder="feature, auth, critical"
                />
              </div>
            </div>
          </details>

          {/* Error */}
          {createMutation.isError && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {(createMutation.error as Error).message}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="btn-gradient px-4 py-2 rounded-xl disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Goal'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main Page Component
export function Goals() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<GoalStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);

  // Fetch goals
  const { data: goalsData, isLoading, error } = useQuery({
    queryKey: ['goals', statusFilter],
    queryFn: () => goals.list(statusFilter === 'all' ? undefined : statusFilter, true),
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Use demo data when API returns empty
  const displayGoals = goalsData?.goals?.length ? goalsData.goals : demoGoals;

  // Calculate counts from displayGoals to ensure they match
  const calculatedCounts = displayGoals.reduce((acc, goal) => {
    acc[goal.status] = (acc[goal.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Use calculated counts if API returns empty, otherwise use API counts
  const displayCounts = goalsData?.goals?.length
    ? (goalsData.counts || calculatedCounts)
    : calculatedCounts;

  // Filter goals based on status filter
  const filteredGoals = statusFilter === 'all'
    ? displayGoals
    : displayGoals.filter(g => g.status === statusFilter);

  // Fetch agents for the create modal
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agents.list(),
  });

  // Mutations
  const startMutation = useMutation({
    mutationFn: (id: number) => goals.start(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: number) => goals.pause(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => goals.resume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const completeMutation = useMutation({
    mutationFn: (id: number) => goals.complete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => goals.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  const decomposeMutation = useMutation({
    mutationFn: (id: number) => goals.decompose(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['goals'] }),
  });

  // Stats from counts
  const stats = {
    total: Object.values(displayCounts).reduce((a: number, b: unknown) => a + (b as number), 0),
    active: (displayCounts.active as number) || 0,
    pending: (displayCounts.pending as number) || 0,
    completed: (displayCounts.completed as number) || 0,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agent Goals</h1>
          <p className="text-zinc-400 mt-1">Hierarchical goal tracking with auto-decomposition</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create Goal
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Target className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-xs text-zinc-500">Total Goals</p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Play className="w-5 h-5 text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.active}</p>
              <p className="text-xs text-zinc-500">Active</p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-zinc-500/20 flex items-center justify-center">
              <Clock className="w-5 h-5 text-zinc-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.pending}</p>
              <p className="text-xs text-zinc-500">Pending</p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.completed}</p>
              <p className="text-xs text-zinc-500">Completed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-zinc-800/50 rounded-lg p-1">
          {(['all', 'pending', 'active', 'blocked', 'completed'] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                statusFilter === status
                  ? 'bg-purple-500/20 text-purple-300'
                  : 'text-zinc-400 hover:text-white'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['goals'] })}
          className="p-2 text-zinc-400 hover:text-white transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Goals List */}
      {isLoading ? (
        <div className="glass-card rounded-xl p-8 text-center">
          <RefreshCw className="w-8 h-8 text-purple-400 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Loading goals...</p>
        </div>
      ) : error ? (
        <div className="glass-card rounded-xl p-8 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-red-400">{(error as Error).message}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredGoals.map((goal: Goal) => (
            <GoalTreeItem
              key={goal.id}
              goal={goal}
              onStart={(id) => startMutation.mutate(id)}
              onPause={(id) => pauseMutation.mutate(id)}
              onResume={(id) => resumeMutation.mutate(id)}
              onComplete={(id) => completeMutation.mutate(id)}
              onDelete={(id) => {
                if (confirm('Are you sure you want to delete this goal and all its subgoals?')) {
                  deleteMutation.mutate(id);
                }
              }}
              onDecompose={(id) => {
                if (confirm('Decompose this goal into subgoals using AI?')) {
                  decomposeMutation.mutate(id);
                }
              }}
              onViewDetails={(goal) => setSelectedGoal(goal)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateGoalModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        agentsList={agentsData?.agents || []}
      />

      {/* Detail Modal */}
      {selectedGoal && (
        <GoalDetailModal
          goal={selectedGoal}
          onClose={() => setSelectedGoal(null)}
        />
      )}
    </div>
  );
}

export default Goals;
