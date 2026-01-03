// Circles orchestration page with Web3 dark theme

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Circle,
  Plus,
  Play,
  Square,
  Trash2,
  ListTodo,
  Users,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X,
  Target,
  Bot,
  Settings,
  Zap,
  FolderGit2,
  Menu,
  ArrowLeft,
} from 'lucide-react';
import { circles, agents as agentsApi } from '../services/api';
import type { Circle as CircleType, Task, TaskStatus } from '../types';

const statusConfig: Record<TaskStatus, { bg: string; text: string; glow?: string }> = {
  pending: { bg: 'bg-zinc-500/20', text: 'text-zinc-400' },
  assigned: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
  in_progress: { bg: 'bg-amber-500/20', text: 'text-amber-400', glow: 'glow-amber' },
  in_review: { bg: 'bg-purple-500/20', text: 'text-purple-400', glow: 'glow-purple' },
  review: { bg: 'bg-purple-500/20', text: 'text-purple-400', glow: 'glow-purple' },
  completed: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', glow: 'glow-green' },
  failed: { bg: 'bg-red-500/20', text: 'text-red-400' },
};

const statusIcons: Record<TaskStatus, React.ReactNode> = {
  pending: <Clock className="w-4 h-4" />,
  assigned: <Users className="w-4 h-4" />,
  in_progress: <Loader2 className="w-4 h-4 animate-spin" />,
  in_review: <AlertCircle className="w-4 h-4" />,
  review: <AlertCircle className="w-4 h-4" />,
  completed: <CheckCircle2 className="w-4 h-4" />,
  failed: <AlertCircle className="w-4 h-4" />,
};

function CircleCard({
  circle,
  isSelected,
  onSelect,
  onStart,
  onStop,
  onDelete,
}: {
  circle: CircleType;
  isSelected: boolean;
  onSelect: () => void;
  onStart: () => void;
  onStop: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl cursor-pointer transition-all glass-card-hover ${
        isSelected
          ? 'glass-card border-emerald-500/50 glow-green'
          : 'glass-card'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
              circle.status === 'running'
                ? 'bg-gradient-to-br from-emerald-500 to-teal-500'
                : 'bg-gradient-to-br from-zinc-600 to-zinc-700'
            }`}>
              <Circle className="w-5 h-5 text-white" />
            </div>
            {circle.status === 'running' && (
              <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-[#11111b] bg-emerald-500 animate-pulse" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white">{circle.name}</h3>
            <p className="text-sm text-zinc-500">{circle.agent_count} agents</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {circle.status === 'running' ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStop();
              }}
              className="p-1.5 text-amber-400 hover:bg-amber-500/10 rounded-lg transition-all"
              title="Stop circle"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onStart();
              }}
              className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-all"
              title="Start circle"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
            title="Delete circle"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
        <div className="flex items-center gap-1.5">
          <ListTodo className="w-3.5 h-3.5 text-cyan-400" />
          <span>{circle.active_tasks} active tasks</span>
        </div>
        {circle.project_name && (
          <div className="flex items-center gap-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-purple-400" />
            <span className="text-purple-400 truncate max-w-[120px]" title={circle.project_name}>
              {circle.project_name}
            </span>
          </div>
        )}
      </div>

      <div className="mt-3">
        <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
          circle.status === 'running'
            ? 'badge-success'
            : circle.status === 'starting'
            ? 'badge-warning'
            : 'bg-zinc-500/20 text-zinc-400 border border-zinc-500/30'
        }`}>
          {circle.status}
        </span>
      </div>
    </div>
  );
}

function TaskItem({ task }: { task: Task }) {
  const config = statusConfig[task.status];

  return (
    <div className="p-4 glass-card rounded-xl">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <h4 className="font-medium text-white">{task.title}</h4>
          {task.description && (
            <p className="text-sm text-zinc-400 mt-1">{task.description}</p>
          )}
        </div>
        <span className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full ${config.bg} ${config.text} border border-current/20`}>
          {statusIcons[task.status]}
          {task.status}
        </span>
      </div>

      <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
        <div className="flex items-center gap-1">
          <span className={`px-2 py-0.5 rounded-full ${
            task.priority === 'high' || task.priority === 'critical'
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : task.priority === 'medium'
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              : 'bg-zinc-500/20 text-zinc-400 border border-zinc-500/30'
          }`}>
            {task.priority}
          </span>
        </div>
        {task.assigned_agent_id && (
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-purple-400" />
            <span>{task.assigned_agent_name ?? `Agent #${task.assigned_agent_id}`}</span>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-cyan-400" />
          <span>{new Date(task.created_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}

// Common competencies for quick selection
const commonCompetencies = [
  'python', 'typescript', 'javascript', 'react', 'api', 'testing',
  'code_review', 'documentation', 'security', 'database', 'devops'
];

function CircleDetail({ circle }: { circle: CircleType }) {
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState('medium');
  const [requiredCompetencies, setRequiredCompetencies] = useState<string[]>([]);
  const [showCompetencies, setShowCompetencies] = useState(false);
  const [lastCreatedTask, setLastCreatedTask] = useState<Task | null>(null);
  const queryClient = useQueryClient();

  const { data: tasksData, isLoading } = useQuery({
    queryKey: ['circle-tasks', circle.name],
    queryFn: () => circles.getTasks(circle.name),
    refetchInterval: 30000,
  });

  const { data: metricsData } = useQuery({
    queryKey: ['circle-metrics', circle.name],
    queryFn: () => circles.getMetrics(circle.name),
    refetchInterval: 30000,
  });

  // Display real data from API
  const displayTasks = tasksData?.tasks || [];
  const displayMetrics = metricsData || { tasks_completed: 0, tasks_in_progress: 0, conflicts_resolved: 0, uptime_seconds: 0 };

  const createTaskMutation = useMutation({
    mutationFn: () =>
      circles.createTask(circle.name, {
        title: newTaskTitle,
        description: newTaskDesc,
        required_competencies: requiredCompetencies,
        priority: newTaskPriority as 'low' | 'medium' | 'high' | 'critical',
      }),
    onSuccess: (task) => {
      queryClient.invalidateQueries({ queryKey: ['circle-tasks', circle.name] });
      setLastCreatedTask(task);
      setNewTaskTitle('');
      setNewTaskDesc('');
      setRequiredCompetencies([]);
      setShowCompetencies(false);
      // Clear the success message after 5 seconds
      setTimeout(() => setLastCreatedTask(null), 5000);
    },
  });

  const toggleCompetency = (comp: string) => {
    setRequiredCompetencies(prev =>
      prev.includes(comp) ? prev.filter(c => c !== comp) : [...prev, comp]
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-5 border-b border-white/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center glow-green">
              <Circle className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-semibold text-lg text-white">{circle.name}</h2>
              <p className="text-sm text-zinc-500">{circle.agent_count} agents · {circle.status}</p>
            </div>
          </div>
        </div>

        {/* Metrics */}
        <div className="mt-5 grid grid-cols-4 gap-3">
          <div className="text-center p-3 glass-card rounded-xl">
            <p className="text-2xl font-bold text-emerald-400">{displayMetrics.tasks_completed}</p>
            <p className="text-xs text-zinc-500 mt-1">Completed</p>
          </div>
          <div className="text-center p-3 glass-card rounded-xl">
            <p className="text-2xl font-bold text-amber-400">{displayMetrics.tasks_in_progress}</p>
            <p className="text-xs text-zinc-500 mt-1">In Progress</p>
          </div>
          <div className="text-center p-3 glass-card rounded-xl">
            <p className="text-2xl font-bold text-purple-400">{displayMetrics.conflicts_resolved}</p>
            <p className="text-xs text-zinc-500 mt-1">Conflicts</p>
          </div>
          <div className="text-center p-3 glass-card rounded-xl">
            <p className="text-2xl font-bold text-cyan-400">{Math.round(displayMetrics.uptime_seconds / 60)}m</p>
            <p className="text-xs text-zinc-500 mt-1">Uptime</p>
          </div>
        </div>
      </div>

      {/* Create task form */}
      <div className="p-5 border-b border-white/5">
        {/* Success feedback */}
        {lastCreatedTask && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/30">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span className="text-sm text-emerald-300">Task created!</span>
              {lastCreatedTask.assigned_agent_name ? (
                <span className="text-sm text-emerald-400">
                  → Assigned to <strong>{lastCreatedTask.assigned_agent_name}</strong>
                </span>
              ) : circle.auto_route ? (
                <span className="text-sm text-amber-400">
                  → Routing to best agent...
                </span>
              ) : (
                <span className="text-sm text-zinc-400">
                  → Pending assignment
                </span>
              )}
            </div>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (newTaskTitle.trim()) {
              createTaskMutation.mutate();
            }
          }}
          className="space-y-3"
        >
          <div className="flex gap-3">
            <input
              type="text"
              value={newTaskTitle}
              onChange={(e) => setNewTaskTitle(e.target.value)}
              placeholder="Task title..."
              className="flex-1 px-4 py-3 input-glass rounded-xl text-sm disabled:opacity-50"
            />
            <select
              value={newTaskPriority}
              onChange={(e) => setNewTaskPriority(e.target.value)}
              className="px-4 py-3 input-glass rounded-xl text-sm appearance-none cursor-pointer disabled:opacity-50"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <button
              type="submit"
              disabled={createTaskMutation.isPending || !newTaskTitle.trim()}
              className="p-3 btn-gradient rounded-xl disabled:opacity-50"
            >
              <Plus className="w-5 h-5" />
            </button>
          </div>

          <input
            type="text"
            value={newTaskDesc}
            onChange={(e) => setNewTaskDesc(e.target.value)}
            placeholder="Description (optional)"
            className="w-full px-4 py-3 input-glass rounded-xl text-sm disabled:opacity-50"
          />

          {/* Required competencies */}
          <div>
            <button
              type="button"
              onClick={() => setShowCompetencies(!showCompetencies)}
              className="flex items-center gap-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              <Settings className="w-4 h-4" />
              <span>Required skills</span>
              {requiredCompetencies.length > 0 && (
                <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 text-xs">
                  {requiredCompetencies.length}
                </span>
              )}
            </button>

            {showCompetencies && (
              <div className="mt-2 p-3 glass-card rounded-xl">
                <p className="text-xs text-zinc-500 mb-2">
                  Select competencies to route this task to the right agent:
                </p>
                <div className="flex flex-wrap gap-2">
                  {commonCompetencies.map((comp) => (
                    <button
                      key={comp}
                      type="button"
                      onClick={() => toggleCompetency(comp)}
                      className={`px-2.5 py-1 rounded-lg text-xs transition-all ${
                        requiredCompetencies.includes(comp)
                          ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/50'
                          : 'bg-zinc-700/50 text-zinc-400 hover:bg-zinc-700 border border-transparent'
                      }`}
                    >
                      {comp}
                    </button>
                  ))}
                </div>
                {requiredCompetencies.length > 0 && (
                  <p className="text-xs text-cyan-400 mt-2">
                    Task will be routed to an agent with: {requiredCompetencies.join(', ')}
                  </p>
                )}
              </div>
            )}
          </div>
        </form>
      </div>

      {/* Tasks list */}
      <div className="flex-1 overflow-y-auto p-5 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.1s]" />
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
          </div>
        ) : (
          displayTasks.map((task) => <TaskItem key={task.id} task={task} />)
        )}
      </div>
    </div>
  );
}

function CreateCircleModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState('');
  const [selectedAgents, setSelectedAgents] = useState<number[]>([]);
  const [requireReview, setRequireReview] = useState(true);
  const [autoRoute, setAutoRoute] = useState(true);
  const [autoStart, setAutoStart] = useState(true);
  const queryClient = useQueryClient();

  // Fetch available agents
  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list,
  });

  const agents = agentsData?.agents || [];

  const createMutation = useMutation({
    mutationFn: async () => {
      // Create the circle
      const circle = await circles.create({
        name,
        require_review: requireReview,
        auto_route: autoRoute,
      });

      // Add selected agents to the circle
      for (const agentId of selectedAgents) {
        const agent = agents.find(a => a.id === agentId);
        if (agent) {
          await circles.addAgent(name, {
            agent_id: agent.id,
            agent_name: agent.name,
            provider: agent.provider,
            model: agent.model,
            competencies: agent.competencies?.join(',') || '',
            can_review: agent.can_review?.join(',') || '',
          });
        }
      }

      // Auto-start the circle if option is enabled
      if (autoStart) {
        await circles.start(name);
      }

      return circle;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['circles'] });
      onClose();
      setName('');
      setSelectedAgents([]);
      setRequireReview(true);
      setAutoRoute(true);
      setAutoStart(true);
    },
  });

  const toggleAgent = (id: number) => {
    setSelectedAgents((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-circle-title"
    >
      <div className="glass-card rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center glow-green">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 id="create-circle-title" className="text-xl font-bold text-white">Create Circle</h2>
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
          {/* Circle Name */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Circle Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my-circle"
              required
              className="w-full px-4 py-3 input-glass rounded-xl"
            />
          </div>

          {/* Circle Options */}
          <div className="grid grid-cols-2 gap-4">
            <label className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
              requireReview
                ? 'bg-purple-500/20 border border-purple-500/30'
                : 'glass-card hover:bg-white/5 border border-transparent'
            }`}>
              <input
                type="checkbox"
                checked={requireReview}
                onChange={(e) => setRequireReview(e.target.checked)}
                className="w-4 h-4 text-purple-500 bg-zinc-800 border-zinc-600 rounded focus:ring-purple-500 focus:ring-offset-0"
              />
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-purple-400" />
                <span className="text-sm text-white">Require Review</span>
              </div>
            </label>

            <label className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
              autoRoute
                ? 'bg-cyan-500/20 border border-cyan-500/30'
                : 'glass-card hover:bg-white/5 border border-transparent'
            }`}>
              <input
                type="checkbox"
                checked={autoRoute}
                onChange={(e) => setAutoRoute(e.target.checked)}
                className="w-4 h-4 text-cyan-500 bg-zinc-800 border-zinc-600 rounded focus:ring-cyan-500 focus:ring-offset-0"
              />
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-sm text-white">Auto Route</span>
              </div>
            </label>
          </div>

          {/* Auto Start Option */}
          <label className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
            autoStart
              ? 'bg-emerald-500/20 border border-emerald-500/30'
              : 'glass-card hover:bg-white/5 border border-transparent'
          }`}>
            <input
              type="checkbox"
              checked={autoStart}
              onChange={(e) => setAutoStart(e.target.checked)}
              className="w-4 h-4 text-emerald-500 bg-zinc-800 border-zinc-600 rounded focus:ring-emerald-500 focus:ring-offset-0"
            />
            <div className="flex items-center gap-2">
              <Play className="w-4 h-4 text-emerald-400" />
              <div>
                <span className="text-sm text-white">Start immediately</span>
                <p className="text-xs text-zinc-500">Activate the circle after creation</p>
              </div>
            </div>
          </label>

          {/* Agent Selection */}
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              Agents ({selectedAgents.length} selected)
            </label>
            {agents.length === 0 ? (
              <p className="text-sm text-zinc-500 py-3">
                No agents available. Create agents first.
              </p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-2 glass-card rounded-xl p-3">
                {agents.map((agent) => (
                  <label
                    key={agent.id}
                    className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                      selectedAgents.includes(agent.id)
                        ? 'bg-emerald-500/20 border border-emerald-500/30'
                        : 'hover:bg-white/5 border border-transparent'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedAgents.includes(agent.id)}
                      onChange={() => toggleAgent(agent.id)}
                      className="w-4 h-4 text-emerald-500 bg-zinc-800 border-zinc-600 rounded focus:ring-emerald-500 focus:ring-offset-0"
                    />
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        agent.status === 'idle'
                          ? 'bg-gradient-to-br from-emerald-500 to-teal-500'
                          : agent.status === 'busy'
                          ? 'bg-gradient-to-br from-amber-500 to-orange-500'
                          : 'bg-gradient-to-br from-zinc-600 to-zinc-700'
                      }`}>
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{agent.name}</p>
                        <p className="text-xs text-zinc-500 truncate">{agent.role}</p>
                      </div>
                      {agent.competencies && agent.competencies.length > 0 && (
                        <div className="flex gap-1 flex-wrap justify-end max-w-[120px]">
                          {agent.competencies.slice(0, 2).map((comp) => (
                            <span key={comp} className="text-xs px-1.5 py-0.5 rounded bg-zinc-700/50 text-zinc-400">
                              {comp}
                            </span>
                          ))}
                          {agent.competencies.length > 2 && (
                            <span className="text-xs text-zinc-500">+{agent.competencies.length - 2}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            )}
            <p className="text-xs text-zinc-500 mt-2">
              Tasks will be automatically routed to agents based on their competencies
            </p>
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
              disabled={createMutation.isPending || !name.trim()}
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Circles() {
  const [selectedCircle, setSelectedCircle] = useState<CircleType | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['circles'],
    queryFn: circles.list,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  // Display real data from API
  const displayCircles = data?.circles || [];

  const startMutation = useMutation({
    mutationFn: circles.start,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['circles'] }),
  });

  const stopMutation = useMutation({
    mutationFn: circles.stop,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['circles'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: circles.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['circles'] });
      if (selectedCircle) {
        setSelectedCircle(null);
      }
    },
  });

  // On mobile, hide sidebar when a circle is selected
  const handleSelectCircle = (circle: CircleType) => {
    setSelectedCircle(circle);
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
              <span className="text-sm">Show circles</span>
            </>
          )}
        </button>
        {selectedCircle && !showSidebar && (
          <span className="text-sm text-zinc-400 truncate max-w-[150px]">
            {selectedCircle.name}
          </span>
        )}
      </div>

      {/* Circles list - collapsible on mobile */}
      <div className={`${showSidebar ? 'flex' : 'hidden'} md:flex w-full md:w-80 flex-shrink-0 flex-col`}>
        <div className="flex items-center justify-between mb-4 md:mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-xl md:text-2xl font-bold text-white">Circles</h1>
            <Target className="w-5 h-5 text-emerald-400 animate-pulse" />
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
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          ) : displayCircles.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500">
              <Circle className="w-10 h-10 mb-3 opacity-50" />
              <p className="text-sm">No circles yet</p>
              <p className="text-xs mt-1">Click + to create one</p>
            </div>
          ) : (
            displayCircles.map((circle) => (
              <CircleCard
                key={circle.id}
                circle={circle}
                isSelected={selectedCircle?.id === circle.id}
                onSelect={() => handleSelectCircle(circle)}
                onStart={() => startMutation.mutate(circle.name)}
                onStop={() => stopMutation.mutate(circle.name)}
                onDelete={() => deleteMutation.mutate(circle.name)}
              />
            ))
          )}
        </div>
      </div>

      {/* Circle detail - show on mobile when sidebar is hidden or a circle is selected */}
      <div className={`${!showSidebar || selectedCircle ? 'flex' : 'hidden md:flex'} flex-1 glass-card rounded-2xl overflow-hidden min-h-[300px]`}>
        {selectedCircle ? (
          <CircleDetail circle={selectedCircle} />
        ) : (
          <div className="h-full flex items-center justify-center w-full">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/20 flex items-center justify-center mx-auto mb-6">
                <Circle className="w-10 h-10 text-emerald-400" />
              </div>
              <p className="text-lg font-medium text-zinc-400">Select a circle to view tasks</p>
              <p className="text-sm text-zinc-600 mt-2">Choose from the list on the left</p>
            </div>
          </div>
        )}
      </div>

      <CreateCircleModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
    </div>
  );
}

export default Circles;
