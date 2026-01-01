// Agent Dashboard - Personal workspace for a single agent

import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Bot,
  Activity,
  Target,
  CheckCircle,
  Clock,
  MessageSquare,
  Brain,
  Zap,
  ArrowLeft,
  Play,
  RefreshCw,
  Calendar,
  AlertCircle,
  FileText,
  ChevronRight,
  Circle,
} from 'lucide-react';
import { agents } from '../services/api';
import type { AgentDetail } from '../types';

// Types
interface AgentTask {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  due_date?: string;
  project_name?: string;
}

interface AgentGoal {
  id: string;
  title: string;
  progress: number;
  status: 'active' | 'completed' | 'paused';
  subgoals_count: number;
  subgoals_completed: number;
}

interface AgentMemory {
  id: string;
  type: 'preference' | 'decision' | 'context' | 'fact';
  content: string;
  created_at: string;
}

interface AgentConversation {
  id: string;
  title: string;
  participants: string[];
  last_message: string;
  last_activity: string;
}

interface AgentStats {
  tasks_today: number;
  tasks_completed: number;
  tasks_in_progress: number;
  reviews_pending: number;
  tokens_used: number;
  messages_sent: number;
}

// Priority config
const priorityConfig = {
  critical: { color: 'text-pink-400', bg: 'bg-pink-500/20', label: 'Critical' },
  high: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'High' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Medium' },
  low: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Low' },
};

const memoryTypeConfig = {
  preference: { color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Preference' },
  decision: { color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Decision' },
  context: { color: 'text-cyan-400', bg: 'bg-cyan-500/20', label: 'Context' },
  fact: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Fact' },
};

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

function formatDueDate(timestamp: string): { text: string; urgent: boolean } {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = date.getTime() - now.getTime();
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffHours < 0) return { text: 'Overdue', urgent: true };
  if (diffHours < 24) return { text: `${diffHours}h left`, urgent: true };
  if (diffDays === 1) return { text: 'Tomorrow', urgent: false };
  if (diffDays < 7) return { text: `${diffDays} days`, urgent: false };
  return { text: date.toLocaleDateString('fr-FR'), urgent: false };
}

// Stat Card Component
function StatCard({
  title,
  value,
  icon,
  color,
  trend,
}: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  color: string;
  trend?: { value: number; positive: boolean };
}) {
  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-zinc-400 text-sm">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 ${trend.positive ? 'text-emerald-400' : 'text-red-400'}`}>
              {trend.positive ? '+' : ''}{trend.value}% today
            </p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${color}`}>{icon}</div>
      </div>
    </div>
  );
}

// Task Item Component
function TaskItem({ task }: { task: AgentTask }) {
  const priority = priorityConfig[task.priority];
  const statusIcon = {
    pending: <Circle className="w-4 h-4 text-zinc-500" />,
    in_progress: <Play className="w-4 h-4 text-blue-400" />,
    completed: <CheckCircle className="w-4 h-4 text-emerald-400" />,
    failed: <AlertCircle className="w-4 h-4 text-red-400" />,
  };

  return (
    <div className="flex items-center gap-4 p-3 rounded-xl hover:bg-white/5 transition-colors">
      {statusIcon[task.status]}
      <div className="flex-1 min-w-0">
        <p className="text-zinc-200 truncate">{task.title}</p>
        {task.project_name && (
          <p className="text-xs text-zinc-500">{task.project_name}</p>
        )}
      </div>
      <span className={`px-2 py-0.5 text-xs rounded-full ${priority.bg} ${priority.color}`}>
        {priority.label}
      </span>
      {task.due_date && (
        <span className={`text-xs ${formatDueDate(task.due_date).urgent ? 'text-amber-400' : 'text-zinc-500'}`}>
          {formatDueDate(task.due_date).text}
        </span>
      )}
    </div>
  );
}

// Goal Item Component
function GoalItem({ goal }: { goal: AgentGoal }) {
  const statusColor = goal.status === 'completed' ? 'text-emerald-400' :
    goal.status === 'active' ? 'text-blue-400' : 'text-zinc-400';

  return (
    <div className="p-4 glass-card rounded-xl">
      <div className="flex items-center justify-between mb-2">
        <p className="font-medium text-zinc-200">{goal.title}</p>
        <span className={`text-xs ${statusColor}`}>
          {goal.subgoals_completed}/{goal.subgoals_count} subgoals
        </span>
      </div>
      <div className="h-2 bg-zinc-700/50 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            goal.progress >= 100 ? 'bg-emerald-500' :
            goal.progress >= 50 ? 'bg-blue-500' : 'bg-amber-500'
          }`}
          style={{ width: `${goal.progress}%` }}
        />
      </div>
      <p className="text-xs text-zinc-500 mt-1">{goal.progress}% complete</p>
    </div>
  );
}

export function AgentDashboard() {
  const { agentId } = useParams<{ agentId: string }>();

  // Fetch agent from API
  const { data: agent, isLoading, error } = useQuery<AgentDetail>({
    queryKey: ['agent', agentId],
    queryFn: () => agents.get(Number(agentId)),
    enabled: !!agentId,
  });

  // TODO: Fetch real data from API when endpoints are available
  // For now, initialize with empty arrays
  const tasks: AgentTask[] = [];
  const goals: AgentGoal[] = [];
  const memories: AgentMemory[] = [];
  const conversations: AgentConversation[] = [];
  const stats: AgentStats = {
    tasks_today: 0,
    tasks_completed: 0,
    tasks_in_progress: 0,
    reviews_pending: 0,
    tokens_used: 0,
    messages_sent: agent?.session?.message_count || agent?.message_count || 0,
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="glass-card rounded-xl p-12 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">Agent Not Found</h2>
        <p className="text-zinc-400 mb-4">The agent you're looking for doesn't exist or has been deleted.</p>
        <Link to="/agents" className="btn-gradient px-4 py-2 rounded-xl inline-flex items-center gap-2">
          <ArrowLeft className="w-4 h-4" />
          Back to Agents
        </Link>
      </div>
    );
  }

  // Support both nested persona object and flat persona_name/persona_role fields
  const agentData = agent as AgentDetail & { persona_name?: string; persona_role?: string };
  const agentName = agentData.persona?.name || agentData.persona_name || agentData.name || 'Unknown Agent';
  const agentRole = agentData.persona?.role || agentData.persona_role || agentData.role || 'Agent';
  const agentModel = agentData.config?.model || agentData.model || null;
  const isOnline = agent.status === 'idle' || agent.status === 'busy';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/agents"
            className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Bot className="w-8 h-8 text-white" />
              </div>
              <div className={`absolute -bottom-1 -right-1 w-4 h-4 rounded-full border-2 border-zinc-900 ${
                isOnline ? 'bg-emerald-400' : 'bg-zinc-500'
              }`} />
            </div>

            <div>
              <h1 className="text-2xl font-bold text-white">{agentName}</h1>
              <p className="text-zinc-400">{agentRole}</p>
              <div className="flex items-center gap-2 mt-1">
                {agentModel && (
                  <span className="px-2 py-0.5 text-xs rounded-full bg-purple-500/20 text-purple-400">
                    {agentModel}
                  </span>
                )}
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  isOnline ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-500/20 text-zinc-400'
                }`}>
                  {isOnline ? 'Online' : 'Offline'}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/agents`}
            className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
          >
            <MessageSquare className="w-4 h-4" />
            Chat
          </Link>
          <button className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors">
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <StatCard
            title="Tasks Today"
            value={stats.tasks_today}
            icon={<FileText className="w-5 h-5 text-blue-400" />}
            color="bg-blue-500/20"
          />
          <StatCard
            title="Completed"
            value={stats.tasks_completed}
            icon={<CheckCircle className="w-5 h-5 text-emerald-400" />}
            color="bg-emerald-500/20"
            trend={{ value: 15, positive: true }}
          />
          <StatCard
            title="In Progress"
            value={stats.tasks_in_progress}
            icon={<Activity className="w-5 h-5 text-cyan-400" />}
            color="bg-cyan-500/20"
          />
          <StatCard
            title="Reviews"
            value={stats.reviews_pending}
            icon={<Clock className="w-5 h-5 text-amber-400" />}
            color="bg-amber-500/20"
          />
          <StatCard
            title="Tokens Used"
            value={stats.tokens_used.toLocaleString()}
            icon={<Zap className="w-5 h-5 text-purple-400" />}
            color="bg-purple-500/20"
          />
          <StatCard
            title="Messages"
            value={stats.messages_sent}
            icon={<MessageSquare className="w-5 h-5 text-pink-400" />}
            color="bg-pink-500/20"
          />
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Tasks Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* My Tasks */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-400" />
                My Tasks
              </h2>
              <Link
                to="/board"
                className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
              >
                View Board <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-1">
              {tasks.filter(t => t.status !== 'completed').slice(0, 5).map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
              {tasks.filter(t => t.status !== 'completed').length === 0 && (
                <p className="text-center py-8 text-zinc-500">No pending tasks</p>
              )}
            </div>
          </div>

          {/* Active Goals */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Target className="w-5 h-5 text-purple-400" />
                Active Goals
              </h2>
              <Link
                to="/goals"
                className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-3">
              {goals.filter(g => g.status === 'active').length === 0 ? (
                <p className="text-center py-8 text-zinc-500">No active goals</p>
              ) : (
                goals.filter(g => g.status === 'active').map((goal) => (
                  <GoalItem key={goal.id} goal={goal} />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Recent Conversations */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-purple-400" />
                Conversations
              </h2>
              <Link
                to="/conversations"
                className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-3">
              {conversations.length === 0 ? (
                <p className="text-center py-8 text-zinc-500">No conversations yet</p>
              ) : (
                conversations.map((conv) => (
                  <div key={conv.id} className="p-3 rounded-xl hover:bg-white/5 transition-colors cursor-pointer">
                    <div className="flex items-center justify-between mb-1">
                      <p className="font-medium text-zinc-200 text-sm">{conv.title}</p>
                      <span className="text-xs text-zinc-500">{formatRelativeTime(conv.last_activity)}</span>
                    </div>
                    <p className="text-xs text-zinc-500 truncate">{conv.last_message}</p>
                    <div className="flex items-center gap-1 mt-2">
                      {conv.participants.map((p, i) => (
                        <span key={i} className="px-2 py-0.5 text-xs rounded-full bg-zinc-700/50 text-zinc-400">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Memories */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-400" />
                Recent Memories
              </h2>
              <Link
                to="/knowledge"
                className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-3">
              {memories.length === 0 ? (
                <p className="text-center py-8 text-zinc-500">No memories stored</p>
              ) : (
                memories.slice(0, 4).map((memory) => {
                  const typeConfig = memoryTypeConfig[memory.type];
                  return (
                    <div key={memory.id} className="p-3 rounded-xl bg-zinc-800/30">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${typeConfig.bg} ${typeConfig.color}`}>
                          {typeConfig.label}
                        </span>
                        <span className="text-xs text-zinc-600">{formatRelativeTime(memory.created_at)}</span>
                      </div>
                      <p className="text-sm text-zinc-300">{memory.content}</p>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Scheduled Actions */}
          <div className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Calendar className="w-5 h-5 text-purple-400" />
                Upcoming
              </h2>
              <Link
                to="/schedules"
                className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <div className="space-y-3">
              <p className="text-center py-8 text-zinc-500">No scheduled actions</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentDashboard;
