// Background Tasks page - monitor and manage long-running agent tasks

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlayCircle,
  PauseCircle,
  XCircle,
  RefreshCw,
  Clock,
  Zap,
  Bot,
  Circle,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Activity,
} from 'lucide-react';
import { backgroundTasks, agents } from '../services/api';
import type { BackgroundTask, BackgroundTaskStatus } from '../types';

// Demo data for when API returns empty
const demoTasks = [
  {
    id: 1,
    agent_id: 1,
    agent_name: 'sophie',
    agent_display_name: 'Sophie',
    circle_name: 'dev-team',
    goal: 'Implement the new user dashboard with analytics widgets and real-time data updates',
    status: 'running' as const,
    current_step: 12,
    max_steps: 50,
    progress_percent: 24,
    progress_summary: 'Creating analytics components and integrating with API...',
    total_llm_calls: 45,
    total_tokens_used: 12500,
    total_tool_calls: 23,
    duration_seconds: 1845,
    created_at: new Date(Date.now() - 1845000).toISOString(),
  },
  {
    id: 2,
    agent_id: 2,
    agent_name: 'olivia',
    agent_display_name: 'Olivia',
    circle_name: 'code-review',
    goal: 'Review and optimize database queries for better performance',
    status: 'completed' as const,
    current_step: 30,
    max_steps: 30,
    progress_percent: 100,
    progress_summary: 'Successfully optimized 5 queries, reducing response time by 40%',
    total_llm_calls: 78,
    total_tokens_used: 25000,
    total_tool_calls: 45,
    duration_seconds: 3600,
    created_at: new Date(Date.now() - 7200000).toISOString(),
    completed_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 3,
    agent_id: 1,
    agent_name: 'sophie',
    agent_display_name: 'Sophie',
    circle_name: 'dev-team',
    goal: 'Write comprehensive unit tests for the authentication module',
    status: 'paused' as const,
    current_step: 8,
    max_steps: 40,
    progress_percent: 20,
    progress_summary: 'Paused after completing login flow tests. Waiting for auth refactor.',
    total_llm_calls: 22,
    total_tokens_used: 8000,
    total_tool_calls: 12,
    duration_seconds: 900,
    created_at: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    id: 4,
    agent_id: 2,
    agent_name: 'olivia',
    agent_display_name: 'Olivia',
    goal: 'Generate API documentation for all public endpoints',
    status: 'pending' as const,
    current_step: 0,
    max_steps: 25,
    progress_percent: 0,
    total_llm_calls: 0,
    total_tokens_used: 0,
    total_tool_calls: 0,
    duration_seconds: 0,
    created_at: new Date().toISOString(),
  },
] as BackgroundTask[];

const statusConfig: Record<BackgroundTaskStatus, { color: string; icon: React.ReactNode; label: string }> = {
  pending: { color: 'text-zinc-400', icon: <Clock className="w-4 h-4" />, label: 'Pending' },
  running: { color: 'text-blue-400', icon: <Loader2 className="w-4 h-4 animate-spin" />, label: 'Running' },
  paused: { color: 'text-amber-400', icon: <PauseCircle className="w-4 h-4" />, label: 'Paused' },
  completed: { color: 'text-emerald-400', icon: <CheckCircle className="w-4 h-4" />, label: 'Completed' },
  failed: { color: 'text-red-400', icon: <AlertCircle className="w-4 h-4" />, label: 'Failed' },
  cancelled: { color: 'text-zinc-500', icon: <XCircle className="w-4 h-4" />, label: 'Cancelled' },
  timeout: { color: 'text-orange-400', icon: <Clock className="w-4 h-4" />, label: 'Timeout' },
};

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${mins}m`;
}

function TaskCard({
  task,
  expanded,
  onToggle,
  onPause,
  onResume,
  onCancel,
  onDelete,
}: {
  task: BackgroundTask;
  expanded: boolean;
  onToggle: () => void;
  onPause: () => void;
  onResume: () => void;
  onCancel: () => void;
  onDelete: () => void;
}) {
  const config = statusConfig[task.status];

  const { data: stepsData } = useQuery({
    queryKey: ['background-task-steps', task.id],
    queryFn: () => backgroundTasks.getSteps(task.id),
    enabled: expanded,
    refetchInterval: task.status === 'running' ? 3000 : false,
  });

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-white">
                  {task.agent_display_name || task.agent_name || `Agent #${task.agent_id}`}
                </span>
                {task.circle_name && (
                  <span className="flex items-center gap-1 text-xs text-zinc-500">
                    <Circle className="w-3 h-3" />
                    {task.circle_name}
                  </span>
                )}
              </div>
              <p className="text-sm text-zinc-400 mt-1 line-clamp-2">{task.goal}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-shrink-0">
            <div className={`flex items-center gap-1.5 ${config.color}`}>
              {config.icon}
              <span className="text-sm font-medium">{config.label}</span>
            </div>
            {expanded ? <ChevronUp className="w-5 h-5 text-zinc-500" /> : <ChevronDown className="w-5 h-5 text-zinc-500" />}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-zinc-500 mb-1">
            <span>Step {task.current_step} / {task.max_steps}</span>
            <span>{task.progress_percent}%</span>
          </div>
          <div className="h-2 bg-white/5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                task.status === 'completed' ? 'bg-emerald-500' :
                task.status === 'failed' || task.status === 'cancelled' ? 'bg-red-500' :
                'bg-gradient-to-r from-indigo-500 to-purple-500'
              }`}
              style={{ width: `${task.progress_percent}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="flex items-center gap-4 mt-3 text-xs text-zinc-500">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {task.total_llm_calls} calls
          </span>
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3" />
            {task.total_tokens_used.toLocaleString()} tokens
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatDuration(task.duration_seconds)}
          </span>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-white/5">
          {/* Actions */}
          <div className="p-4 flex items-center gap-2 border-b border-white/5">
            {task.status === 'running' && (
              <button
                onClick={(e) => { e.stopPropagation(); onPause(); }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
              >
                <PauseCircle className="w-4 h-4" />
                Pause
              </button>
            )}
            {task.status === 'paused' && (
              <button
                onClick={(e) => { e.stopPropagation(); onResume(); }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
              >
                <PlayCircle className="w-4 h-4" />
                Resume
              </button>
            )}
            {(task.status === 'running' || task.status === 'paused' || task.status === 'pending') && (
              <button
                onClick={(e) => { e.stopPropagation(); onCancel(); }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              >
                <XCircle className="w-4 h-4" />
                Cancel
              </button>
            )}
            {(task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled' || task.status === 'timeout') && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(); }}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            )}
          </div>

          {/* Progress summary */}
          {task.progress_summary && (
            <div className="p-4 border-b border-white/5">
              <p className="text-sm text-zinc-400">{task.progress_summary}</p>
            </div>
          )}

          {/* Error message */}
          {task.error_message && (
            <div className="p-4 border-b border-white/5 bg-red-500/5">
              <p className="text-sm text-red-400">{task.error_message}</p>
            </div>
          )}

          {/* Steps */}
          <div className="p-4">
            <h4 className="text-sm font-medium text-zinc-400 mb-3">Execution Steps</h4>
            {stepsData?.steps && stepsData.steps.length > 0 ? (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {stepsData.steps.map((step) => (
                  <div
                    key={step.id}
                    className={`p-3 rounded-lg ${step.success ? 'bg-white/5' : 'bg-red-500/10'}`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium text-zinc-300">
                        Step {step.step_number}: {step.action_type}
                      </span>
                      <span className="text-zinc-500">{step.duration_ms}ms</span>
                    </div>
                    {step.action_output && (
                      <p className="text-xs text-zinc-500 mt-1 line-clamp-2">
                        {step.action_output}
                      </p>
                    )}
                    {step.error_message && (
                      <p className="text-xs text-red-400 mt-1">{step.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-zinc-500">No steps recorded yet</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function CreateTaskModal({
  isOpen,
  onClose,
  onCreate,
}: {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (data: { agent_id: number; goal: string; max_steps: number }) => void;
}) {
  const [agentId, setAgentId] = useState<number | null>(null);
  const [goal, setGoal] = useState('');
  const [maxSteps, setMaxSteps] = useState(50);

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (agentId && goal.trim()) {
      onCreate({ agent_id: agentId, goal: goal.trim(), max_steps: maxSteps });
      setGoal('');
      setMaxSteps(50);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 modal-overlay" onClick={onClose} />
      <div className="relative glass-card rounded-2xl p-6 w-full max-w-lg mx-4">
        <h2 className="text-xl font-bold text-white mb-4">Create Background Task</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">Agent</label>
            <select
              value={agentId ?? ''}
              onChange={(e) => setAgentId(Number(e.target.value) || null)}
              className="w-full px-4 py-2.5 input-glass rounded-xl text-sm"
              required
            >
              <option value="">Select an agent...</option>
              {agentsData?.agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name} - {agent.role}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">Goal</label>
            <textarea
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              className="w-full px-4 py-2.5 input-glass rounded-xl text-sm resize-none"
              rows={4}
              placeholder="Describe what the agent should accomplish..."
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-2">
              Max Steps: {maxSteps}
            </label>
            <input
              type="range"
              min={10}
              max={200}
              step={10}
              value={maxSteps}
              onChange={(e) => setMaxSteps(Number(e.target.value))}
              className="w-full"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!agentId || !goal.trim()}
              className="btn-gradient px-6 py-2 rounded-xl text-sm font-medium disabled:opacity-50"
            >
              Create Task
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function BackgroundTasks() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<BackgroundTaskStatus | ''>('');
  const [expandedTask, setExpandedTask] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['background-tasks', statusFilter],
    queryFn: () => backgroundTasks.list(statusFilter || undefined),
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Use demo data when API returns empty
  const displayTasks = data?.tasks?.length ? data.tasks : demoTasks;

  // Calculate counts from displayTasks to ensure they match
  const calculatedCounts = displayTasks.reduce((acc, task) => {
    acc[task.status] = (acc[task.status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Use calculated counts if API returns empty
  const displayCounts = data?.tasks?.length
    ? (data.counts || calculatedCounts)
    : calculatedCounts;

  const displayTotal = displayTasks.length;

  // Filter tasks based on status filter
  const filteredTasks = statusFilter
    ? displayTasks.filter(t => t.status === statusFilter)
    : displayTasks;

  const pauseMutation = useMutation({
    mutationFn: backgroundTasks.pause,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['background-tasks'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: backgroundTasks.resume,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['background-tasks'] }),
  });

  const cancelMutation = useMutation({
    mutationFn: backgroundTasks.cancel,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['background-tasks'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: backgroundTasks.delete,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['background-tasks'] }),
  });

  const createMutation = useMutation({
    mutationFn: backgroundTasks.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['background-tasks'] });
      setShowCreateModal(false);
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Background Tasks</h1>
          <p className="text-zinc-500 mt-1">
            Monitor and manage long-running autonomous agent tasks
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="p-2 text-zinc-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2"
          >
            <Plus className="w-5 h-5" />
            <span>New Task</span>
          </button>
        </div>
      </div>

      {/* Status counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <button
          onClick={() => setStatusFilter('')}
          className={`p-3 rounded-xl text-center transition-colors ${
            statusFilter === '' ? 'bg-purple-500/20 border border-purple-500/50' : 'glass-card hover:bg-white/5'
          }`}
        >
          <div className="text-2xl font-bold text-white">{displayTotal}</div>
          <div className="text-xs text-zinc-500">All</div>
        </button>
        {Object.entries(statusConfig).map(([status, config]) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status as BackgroundTaskStatus)}
            className={`p-3 rounded-xl text-center transition-colors ${
              statusFilter === status ? 'bg-purple-500/20 border border-purple-500/50' : 'glass-card hover:bg-white/5'
            }`}
          >
            <div className={`text-2xl font-bold ${config.color}`}>
              {displayCounts[status] || 0}
            </div>
            <div className="text-xs text-zinc-500">{config.label}</div>
          </button>
        ))}
      </div>

      {/* Task list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {filteredTasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              expanded={expandedTask === task.id}
              onToggle={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
              onPause={() => pauseMutation.mutate(task.id)}
              onResume={() => resumeMutation.mutate(task.id)}
              onCancel={() => cancelMutation.mutate(task.id)}
              onDelete={() => deleteMutation.mutate(task.id)}
            />
          ))}
        </div>
      )}

      {/* Create modal */}
      <CreateTaskModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={(data) => createMutation.mutate(data)}
      />
    </div>
  );
}

export default BackgroundTasks;
