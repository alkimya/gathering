// Scheduled Actions page - cron-like scheduling for agent tasks

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Calendar,
  Clock,
  Play,
  Pause,
  Trash2,
  Plus,
  RefreshCw,
  Zap,
  Timer,
  CalendarClock,
  Radio,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Bot,
} from 'lucide-react';
import { scheduledActions, agents } from '../services/api';
import type {
  ScheduledAction,
  ScheduledActionCreate,
  ScheduledActionRun,
  ScheduleType,
  ScheduledActionStatus,
  Agent,
} from '../types';

// Status badge component
function StatusBadge({ status }: { status: ScheduledActionStatus }) {
  const config = {
    active: { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: CheckCircle2 },
    paused: { color: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: Pause },
    disabled: { color: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30', icon: XCircle },
    expired: { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: AlertCircle },
  };

  const { color, icon: Icon } = config[status] || config.disabled;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}

// Schedule type icon
function ScheduleTypeIcon({ type }: { type: ScheduleType }) {
  const icons = {
    cron: Calendar,
    interval: Timer,
    once: CalendarClock,
    event: Radio,
  };
  const Icon = icons[type] || Calendar;
  return <Icon className="w-4 h-4" />;
}

// Format schedule description
function formatSchedule(action: ScheduledAction): string {
  switch (action.schedule_type) {
    case 'cron':
      return action.cron_expression || 'Invalid cron';
    case 'interval':
      if (!action.interval_seconds) return 'Invalid interval';
      if (action.interval_seconds < 3600) return `Every ${Math.round(action.interval_seconds / 60)} min`;
      if (action.interval_seconds < 86400) return `Every ${Math.round(action.interval_seconds / 3600)} hours`;
      return `Every ${Math.round(action.interval_seconds / 86400)} days`;
    case 'once':
      return action.next_run_at ? new Date(action.next_run_at).toLocaleString() : 'Not scheduled';
    case 'event':
      return `On: ${action.event_trigger || 'unknown event'}`;
    default:
      return 'Unknown';
  }
}

// Format relative time
function formatRelativeTime(dateStr: string | undefined): string {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  const diffSec = Math.abs(diffMs / 1000);
  const isPast = diffMs < 0;

  if (diffSec < 60) return isPast ? 'Just now' : 'In a moment';
  if (diffSec < 3600) {
    const mins = Math.round(diffSec / 60);
    return isPast ? `${mins}m ago` : `In ${mins}m`;
  }
  if (diffSec < 86400) {
    const hours = Math.round(diffSec / 3600);
    return isPast ? `${hours}h ago` : `In ${hours}h`;
  }
  const days = Math.round(diffSec / 86400);
  return isPast ? `${days}d ago` : `In ${days}d`;
}

// Action Card Component
function ActionCard({
  action,
  onPause,
  onResume,
  onTrigger,
  onDelete,
}: {
  action: ScheduledAction;
  onPause: (id: number) => void;
  onResume: (id: number) => void;
  onTrigger: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ['scheduled-action-runs', action.id],
    queryFn: () => scheduledActions.getRuns(action.id),
    enabled: expanded,
  });

  const successRate = action.successful_runs + action.failed_runs > 0
    ? Math.round((action.successful_runs / (action.successful_runs + action.failed_runs)) * 100)
    : null;

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold text-white truncate">{action.name}</h3>
              <StatusBadge status={action.status} />
            </div>
            {action.description && (
              <p className="mt-1 text-sm text-zinc-400 line-clamp-2">{action.description}</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {action.status === 'active' ? (
              <button
                onClick={() => onPause(action.id)}
                className="p-2 text-zinc-400 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
                title="Pause"
              >
                <Pause className="w-4 h-4" />
              </button>
            ) : action.status === 'paused' ? (
              <button
                onClick={() => onResume(action.id)}
                className="p-2 text-zinc-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-colors"
                title="Resume"
              >
                <Play className="w-4 h-4" />
              </button>
            ) : null}
            <button
              onClick={() => onTrigger(action.id)}
              className="p-2 text-zinc-400 hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-colors"
              title="Trigger Now"
            >
              <Zap className="w-4 h-4" />
            </button>
            <button
              onClick={() => onDelete(action.id)}
              className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
              title="Delete"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Info Grid */}
      <div className="p-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Agent */}
        <div>
          <p className="text-xs text-zinc-500 mb-1">Agent</p>
          <div className="flex items-center gap-2">
            <Bot className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-zinc-300">{action.agent_name || `#${action.agent_id}`}</span>
          </div>
        </div>

        {/* Schedule */}
        <div>
          <p className="text-xs text-zinc-500 mb-1">Schedule</p>
          <div className="flex items-center gap-2">
            <ScheduleTypeIcon type={action.schedule_type} />
            <span className="text-sm text-zinc-300">{formatSchedule(action)}</span>
          </div>
        </div>

        {/* Next Run */}
        <div>
          <p className="text-xs text-zinc-500 mb-1">Next Run</p>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-zinc-300">{formatRelativeTime(action.next_run_at)}</span>
          </div>
        </div>

        {/* Stats */}
        <div>
          <p className="text-xs text-zinc-500 mb-1">Executions</p>
          <div className="flex items-center gap-2">
            <span className="text-sm text-zinc-300">
              {action.execution_count}
              {action.max_executions ? ` / ${action.max_executions}` : ''}
            </span>
            {successRate !== null && (
              <span className={`text-xs px-1.5 py-0.5 rounded ${successRate >= 80 ? 'bg-emerald-500/20 text-emerald-400' : successRate >= 50 ? 'bg-amber-500/20 text-amber-400' : 'bg-red-500/20 text-red-400'}`}>
                {successRate}%
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Goal Preview */}
      <div className="px-4 pb-4">
        <p className="text-xs text-zinc-500 mb-1">Goal</p>
        <p className="text-sm text-zinc-400 line-clamp-2 bg-zinc-800/50 rounded-lg p-2">
          {action.goal}
        </p>
      </div>

      {/* Expandable Runs Section */}
      <div className="border-t border-white/5">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full px-4 py-2 flex items-center justify-between text-sm text-zinc-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <span>Execution History</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {expanded && (
          <div className="px-4 pb-4 max-h-64 overflow-auto">
            {runsLoading ? (
              <div className="text-center text-zinc-500 py-4">Loading...</div>
            ) : runs && runs.length > 0 ? (
              <div className="space-y-2">
                {runs.map((run: ScheduledActionRun) => (
                  <div
                    key={run.id}
                    className="flex items-center justify-between p-2 bg-zinc-800/50 rounded-lg text-sm"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-500">#{run.run_number}</span>
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        run.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' :
                        run.status === 'failed' ? 'bg-red-500/20 text-red-400' :
                        run.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-zinc-500/20 text-zinc-400'
                      }`}>
                        {run.status}
                      </span>
                      <span className="text-zinc-500">{run.triggered_by}</span>
                    </div>
                    <div className="flex items-center gap-4 text-zinc-500">
                      {run.duration_ms > 0 && <span>{(run.duration_ms / 1000).toFixed(1)}s</span>}
                      <span>{new Date(run.triggered_at).toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-zinc-500 py-4">No executions yet</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Create Action Modal
function CreateActionModal({
  isOpen,
  onClose,
  agentsList,
}: {
  isOpen: boolean;
  onClose: () => void;
  agentsList: Agent[];
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<Partial<ScheduledActionCreate>>({
    schedule_type: 'interval',
    interval_seconds: 3600,
    max_steps: 50,
    timeout_seconds: 3600,
    retry_on_failure: true,
    max_retries: 3,
  });

  const createMutation = useMutation({
    mutationFn: (data: ScheduledActionCreate) => scheduledActions.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] });
      onClose();
      setFormData({
        schedule_type: 'interval',
        interval_seconds: 3600,
        max_steps: 50,
        timeout_seconds: 3600,
        retry_on_failure: true,
        max_retries: 3,
      });
    },
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.agent_id || !formData.name || !formData.goal) return;
    createMutation.mutate(formData as ScheduledActionCreate);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 modal-overlay" onClick={onClose} />
      <div className="relative glass-card rounded-2xl w-full max-w-lg max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-white/5">
          <h2 className="text-xl font-bold text-white">Create Scheduled Action</h2>
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

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Name</label>
            <input
              type="text"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg"
              placeholder="Daily report generation"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Description</label>
            <input
              type="text"
              value={formData.description || ''}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg"
              placeholder="Optional description"
            />
          </div>

          {/* Goal */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Goal</label>
            <textarea
              value={formData.goal || ''}
              onChange={(e) => setFormData({ ...formData, goal: e.target.value })}
              className="w-full px-3 py-2 input-glass rounded-lg resize-none"
              rows={3}
              placeholder="What should the agent accomplish?"
              required
            />
          </div>

          {/* Schedule Type */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Schedule Type</label>
            <div className="grid grid-cols-4 gap-2">
              {(['interval', 'cron', 'once', 'event'] as ScheduleType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setFormData({ ...formData, schedule_type: type })}
                  className={`p-2 rounded-lg border text-sm flex flex-col items-center gap-1 transition-colors ${
                    formData.schedule_type === type
                      ? 'border-purple-500 bg-purple-500/20 text-purple-300'
                      : 'border-white/10 hover:border-white/20 text-zinc-400'
                  }`}
                >
                  <ScheduleTypeIcon type={type} />
                  <span className="capitalize">{type}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Schedule Configuration */}
          {formData.schedule_type === 'interval' && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Interval (seconds)</label>
              <input
                type="number"
                value={formData.interval_seconds || 3600}
                onChange={(e) => setFormData({ ...formData, interval_seconds: Number(e.target.value) })}
                className="w-full px-3 py-2 input-glass rounded-lg"
                min={60}
                required
              />
              <p className="text-xs text-zinc-500 mt-1">Minimum: 60 seconds (1 minute)</p>
            </div>
          )}

          {formData.schedule_type === 'cron' && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Cron Expression</label>
              <input
                type="text"
                value={formData.cron_expression || ''}
                onChange={(e) => setFormData({ ...formData, cron_expression: e.target.value })}
                className="w-full px-3 py-2 input-glass rounded-lg font-mono"
                placeholder="0 9 * * MON-FRI"
                required
              />
              <p className="text-xs text-zinc-500 mt-1">Format: minute hour day month weekday</p>
            </div>
          )}

          {formData.schedule_type === 'once' && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Run At</label>
              <input
                type="datetime-local"
                value={formData.next_run_at || ''}
                onChange={(e) => setFormData({ ...formData, next_run_at: e.target.value })}
                className="w-full px-3 py-2 input-glass rounded-lg"
                required
              />
            </div>
          )}

          {formData.schedule_type === 'event' && (
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Event Trigger</label>
              <input
                type="text"
                value={formData.event_trigger || ''}
                onChange={(e) => setFormData({ ...formData, event_trigger: e.target.value })}
                className="w-full px-3 py-2 input-glass rounded-lg"
                placeholder="task.completed"
                required
              />
              <p className="text-xs text-zinc-500 mt-1">Event name to listen for</p>
            </div>
          )}

          {/* Advanced Options */}
          <details className="group">
            <summary className="cursor-pointer text-sm text-zinc-400 hover:text-white transition-colors">
              Advanced Options
            </summary>
            <div className="mt-4 space-y-4 pl-4 border-l border-white/10">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Max Steps</label>
                  <input
                    type="number"
                    value={formData.max_steps || 50}
                    onChange={(e) => setFormData({ ...formData, max_steps: Number(e.target.value) })}
                    className="w-full px-3 py-2 input-glass rounded-lg"
                    min={1}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">Timeout (s)</label>
                  <input
                    type="number"
                    value={formData.timeout_seconds || 3600}
                    onChange={(e) => setFormData({ ...formData, timeout_seconds: Number(e.target.value) })}
                    className="w-full px-3 py-2 input-glass rounded-lg"
                    min={60}
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.retry_on_failure}
                    onChange={(e) => setFormData({ ...formData, retry_on_failure: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm text-zinc-300">Retry on failure</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.allow_concurrent}
                    onChange={(e) => setFormData({ ...formData, allow_concurrent: e.target.checked })}
                    className="w-4 h-4 rounded"
                  />
                  <span className="text-sm text-zinc-300">Allow concurrent</span>
                </label>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">Max Executions</label>
                <input
                  type="number"
                  value={formData.max_executions || ''}
                  onChange={(e) => setFormData({ ...formData, max_executions: e.target.value ? Number(e.target.value) : undefined })}
                  className="w-full px-3 py-2 input-glass rounded-lg"
                  min={1}
                  placeholder="Unlimited"
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
              {createMutation.isPending ? 'Creating...' : 'Create Action'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main Page Component
export function ScheduledActions() {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<ScheduledActionStatus | 'all'>('all');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Fetch scheduled actions
  const { data: actions, isLoading, error } = useQuery({
    queryKey: ['scheduled-actions', statusFilter],
    queryFn: () => scheduledActions.list(statusFilter === 'all' ? undefined : statusFilter),
    refetchInterval: 30000,
  });

  // Use API data
  const displayActions = actions || [];

  // Fetch agents for the create modal
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agents.list(),
  });

  // Mutations
  const pauseMutation = useMutation({
    mutationFn: (id: number) => scheduledActions.pause(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => scheduledActions.resume(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] }),
  });

  const triggerMutation = useMutation({
    mutationFn: (id: number) => scheduledActions.trigger(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => scheduledActions.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] }),
  });

  // Stats
  const stats = {
    total: displayActions.length,
    active: displayActions.filter((a: ScheduledAction) => a.status === 'active').length,
    paused: displayActions.filter((a: ScheduledAction) => a.status === 'paused').length,
    expired: displayActions.filter((a: ScheduledAction) => a.status === 'expired').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Scheduled Actions</h1>
          <p className="text-zinc-400 mt-1">Cron-like scheduling for agent tasks</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Create Action
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
              <Calendar className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total}</p>
              <p className="text-xs text-zinc-500">Total Actions</p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 flex items-center justify-center">
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
            <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
              <Pause className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.paused}</p>
              <p className="text-xs text-zinc-500">Paused</p>
            </div>
          </div>
        </div>

        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
              <XCircle className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.expired}</p>
              <p className="text-xs text-zinc-500">Expired</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-zinc-800/50 rounded-lg p-1">
          {(['all', 'active', 'paused', 'expired'] as const).map((status) => (
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
          onClick={() => queryClient.invalidateQueries({ queryKey: ['scheduled-actions'] })}
          className="p-2 text-zinc-400 hover:text-white transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Actions List */}
      {isLoading ? (
        <div className="glass-card rounded-xl p-8 text-center">
          <RefreshCw className="w-8 h-8 text-purple-400 animate-spin mx-auto mb-4" />
          <p className="text-zinc-400">Loading scheduled actions...</p>
        </div>
      ) : error ? (
        <div className="glass-card rounded-xl p-8 text-center">
          <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-4" />
          <p className="text-red-400">{(error as Error).message}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {displayActions.map((action: ScheduledAction) => (
            <ActionCard
              key={action.id}
              action={action}
              onPause={(id) => pauseMutation.mutate(id)}
              onResume={(id) => resumeMutation.mutate(id)}
              onTrigger={(id) => triggerMutation.mutate(id)}
              onDelete={(id) => {
                if (confirm('Are you sure you want to delete this scheduled action?')) {
                  deleteMutation.mutate(id);
                }
              }}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      <CreateActionModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        agentsList={agentsData?.agents || []}
      />
    </div>
  );
}

export default ScheduledActions;
