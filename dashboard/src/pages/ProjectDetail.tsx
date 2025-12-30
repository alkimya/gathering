// Project Detail page - Rich project view with burndown, velocity, sprint

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  FolderOpen,
  GitBranch,
  Users,
  Target,
  TrendingUp,
  TrendingDown,
  Clock,
  Bot,
  Calendar,
  Zap,
  BarChart3,
} from 'lucide-react';

// Types
interface SprintTask {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  assignee?: string;
  story_points: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface Sprint {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  status: 'active' | 'completed' | 'planning';
  tasks: SprintTask[];
  goal: string;
}

interface DailyProgress {
  date: string;
  ideal: number;
  actual: number;
}

interface VelocityData {
  sprint: string;
  planned: number;
  completed: number;
}

// Demo data
const generateDemoSprint = (): Sprint => ({
  id: 'sprint-1',
  name: 'Sprint 23 - Dashboard Enhancement',
  start_date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  status: 'active',
  goal: 'Deliver Calendar view, Pipeline editor, and Agent Dashboard improvements',
  tasks: [
    { id: '1', title: 'Implement Calendar view', status: 'done', assignee: 'Sophie', story_points: 5, priority: 'high' },
    { id: '2', title: 'Create Pipeline editor', status: 'done', assignee: 'Sophie', story_points: 8, priority: 'high' },
    { id: '3', title: 'Agent Dashboard Personal', status: 'done', assignee: 'Sophie', story_points: 5, priority: 'medium' },
    { id: '4', title: 'Add Edit Agent modal', status: 'done', assignee: 'Sophie', story_points: 3, priority: 'medium' },
    { id: '5', title: 'API Pipelines endpoints', status: 'done', assignee: 'Olivia', story_points: 5, priority: 'high' },
    { id: '6', title: 'Connect real-time data', status: 'in_progress', assignee: 'Sophie', story_points: 8, priority: 'high' },
    { id: '7', title: 'Project detail view', status: 'in_progress', assignee: 'Sophie', story_points: 5, priority: 'medium' },
    { id: '8', title: 'Documentation update', status: 'todo', assignee: 'Claude', story_points: 3, priority: 'low' },
    { id: '9', title: 'Unit tests for skills', status: 'todo', story_points: 5, priority: 'medium' },
    { id: '10', title: 'Performance optimization', status: 'todo', story_points: 8, priority: 'low' },
  ],
});

const generateBurndownData = (): DailyProgress[] => {
  const data: DailyProgress[] = [];
  const totalPoints = 55;
  const daysInSprint = 14;

  for (let i = 0; i <= 10; i++) {
    const date = new Date(Date.now() - (10 - i) * 24 * 60 * 60 * 1000);
    const ideal = totalPoints - (totalPoints / daysInSprint) * i;
    // Simulated actual progress (slightly behind ideal initially, then catching up)
    const actualOffset = i < 5 ? Math.random() * 5 + 2 : Math.random() * 3 - 3;
    const actual = Math.max(0, totalPoints - (totalPoints / daysInSprint) * i + actualOffset);

    data.push({
      date: date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
      ideal: Math.round(ideal),
      actual: Math.round(actual),
    });
  }

  return data;
};

const generateVelocityData = (): VelocityData[] => [
  { sprint: 'Sprint 18', planned: 40, completed: 35 },
  { sprint: 'Sprint 19', planned: 45, completed: 42 },
  { sprint: 'Sprint 20', planned: 42, completed: 45 },
  { sprint: 'Sprint 21', planned: 50, completed: 48 },
  { sprint: 'Sprint 22', planned: 55, completed: 52 },
  { sprint: 'Sprint 23', planned: 55, completed: 34 },
];

// Burndown Chart Component (simple SVG)
function BurndownChart({ data }: { data: DailyProgress[] }) {
  const width = 400;
  const height = 200;
  const padding = 40;
  const chartWidth = width - padding * 2;
  const chartHeight = height - padding * 2;

  const maxValue = Math.max(...data.map((d) => Math.max(d.ideal, d.actual)));

  const getX = (index: number) => padding + (index / (data.length - 1)) * chartWidth;
  const getY = (value: number) => padding + chartHeight - (value / maxValue) * chartHeight;

  const idealPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.ideal)}`).join(' ');
  const actualPath = data.map((d, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getY(d.actual)}`).join(' ');

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
      {/* Grid lines */}
      {[0, 25, 50, 75, 100].map((percent) => (
        <line
          key={percent}
          x1={padding}
          y1={getY((percent / 100) * maxValue)}
          x2={width - padding}
          y2={getY((percent / 100) * maxValue)}
          stroke="rgb(63, 63, 70)"
          strokeWidth="1"
          strokeDasharray="4"
        />
      ))}

      {/* Ideal line */}
      <path d={idealPath} fill="none" stroke="rgb(147, 51, 234)" strokeWidth="2" strokeDasharray="6" />

      {/* Actual line */}
      <path d={actualPath} fill="none" stroke="rgb(34, 211, 238)" strokeWidth="2" />

      {/* Points */}
      {data.map((d, i) => (
        <circle key={i} cx={getX(i)} cy={getY(d.actual)} r="4" fill="rgb(34, 211, 238)" />
      ))}

      {/* X-axis labels */}
      {data.filter((_, i) => i % 2 === 0).map((d, i) => (
        <text
          key={i}
          x={getX(i * 2)}
          y={height - 10}
          textAnchor="middle"
          className="text-xs fill-zinc-500"
        >
          {d.date}
        </text>
      ))}

      {/* Legend */}
      <g transform={`translate(${width - 100}, 15)`}>
        <line x1="0" y1="0" x2="20" y2="0" stroke="rgb(147, 51, 234)" strokeWidth="2" strokeDasharray="4" />
        <text x="25" y="4" className="text-xs fill-zinc-400">Ideal</text>
        <line x1="0" y1="15" x2="20" y2="15" stroke="rgb(34, 211, 238)" strokeWidth="2" />
        <text x="25" y="19" className="text-xs fill-zinc-400">Actual</text>
      </g>
    </svg>
  );
}

// Velocity Chart Component
function VelocityChart({ data }: { data: VelocityData[] }) {
  const maxValue = Math.max(...data.flatMap((d) => [d.planned, d.completed]));

  return (
    <div className="flex items-end justify-between h-40 px-4">
      {data.map((d, i) => {
        const plannedHeight = (d.planned / maxValue) * 100;
        const completedHeight = (d.completed / maxValue) * 100;
        const isCurrentSprint = i === data.length - 1;

        return (
          <div key={i} className="flex flex-col items-center gap-2">
            <div className="flex items-end gap-1 h-32">
              <div
                className={`w-5 rounded-t ${isCurrentSprint ? 'bg-purple-500/40' : 'bg-purple-500/20'}`}
                style={{ height: `${plannedHeight}%` }}
                title={`Planned: ${d.planned}`}
              />
              <div
                className={`w-5 rounded-t ${
                  d.completed >= d.planned
                    ? 'bg-emerald-500'
                    : isCurrentSprint
                    ? 'bg-cyan-500'
                    : 'bg-cyan-500/70'
                }`}
                style={{ height: `${completedHeight}%` }}
                title={`Completed: ${d.completed}`}
              />
            </div>
            <span className={`text-xs ${isCurrentSprint ? 'text-purple-400 font-medium' : 'text-zinc-500'}`}>
              {d.sprint.replace('Sprint ', 'S')}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// Sprint Board Component
function SprintBoard({ sprint }: { sprint: Sprint }) {
  const columns = [
    { id: 'todo', label: 'To Do', color: 'text-zinc-400' },
    { id: 'in_progress', label: 'In Progress', color: 'text-cyan-400' },
    { id: 'done', label: 'Done', color: 'text-emerald-400' },
  ];

  const priorityColors = {
    critical: 'border-l-pink-500',
    high: 'border-l-red-500',
    medium: 'border-l-yellow-500',
    low: 'border-l-emerald-500',
  };

  return (
    <div className="grid grid-cols-3 gap-4">
      {columns.map((column) => {
        const tasks = sprint.tasks.filter((t) => t.status === column.id);
        const points = tasks.reduce((sum, t) => sum + t.story_points, 0);

        return (
          <div key={column.id}>
            <div className="flex items-center justify-between mb-3">
              <h4 className={`font-medium ${column.color}`}>{column.label}</h4>
              <span className="text-xs text-zinc-500">{points} pts</span>
            </div>
            <div className="space-y-2">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className={`p-3 glass-card rounded-lg border-l-2 ${priorityColors[task.priority]}`}
                >
                  <p className="text-sm text-zinc-200">{task.title}</p>
                  <div className="flex items-center justify-between mt-2">
                    {task.assignee ? (
                      <span className="text-xs text-zinc-500 flex items-center gap-1">
                        <Bot className="w-3 h-3" />
                        {task.assignee}
                      </span>
                    ) : (
                      <span className="text-xs text-zinc-600">Unassigned</span>
                    )}
                    <span className="text-xs text-purple-400">{task.story_points} pts</span>
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="p-4 border-2 border-dashed border-zinc-700 rounded-lg text-center">
                  <p className="text-xs text-zinc-600">No tasks</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ProjectDetail() {
  const { projectId: _projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<'overview' | 'sprint' | 'analytics'>('overview');

  // Demo data
  const sprint = generateDemoSprint();
  const burndownData = generateBurndownData();
  const velocityData = generateVelocityData();

  // Calculate stats
  const totalPoints = sprint.tasks.reduce((sum, t) => sum + t.story_points, 0);
  const completedPoints = sprint.tasks.filter((t) => t.status === 'done').reduce((sum, t) => sum + t.story_points, 0);
  const inProgressPoints = sprint.tasks.filter((t) => t.status === 'in_progress').reduce((sum, t) => sum + t.story_points, 0);
  const todoPoints = sprint.tasks.filter((t) => t.status === 'todo').reduce((sum, t) => sum + t.story_points, 0);
  const progressPercent = Math.round((completedPoints / totalPoints) * 100);

  // Average velocity
  const avgVelocity = Math.round(
    velocityData.slice(0, -1).reduce((sum, d) => sum + d.completed, 0) / (velocityData.length - 1)
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/projects"
            className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <FolderOpen className="w-6 h-6 text-purple-400" />
              GatheRing
            </h1>
            <p className="text-zinc-400 mt-1">Multi-agent collaboration framework</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="px-3 py-1 text-xs rounded-full bg-emerald-500/20 text-emerald-400">
            Active
          </span>
          <span className="flex items-center gap-1 text-sm text-zinc-400">
            <GitBranch className="w-4 h-4" />
            develop
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
        {[
          { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
          { id: 'sprint', label: 'Sprint Board', icon: <Target className="w-4 h-4" /> },
          { id: 'analytics', label: 'Analytics', icon: <TrendingUp className="w-4 h-4" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              activeTab === tab.id
                ? 'bg-purple-500/20 text-purple-400'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sprint Progress */}
          <div className="lg:col-span-2 glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-semibold text-white">{sprint.name}</h2>
                <p className="text-sm text-zinc-500 mt-1">{sprint.goal}</p>
              </div>
              <span className="px-3 py-1 text-xs rounded-full bg-cyan-500/20 text-cyan-400">
                {sprint.status}
              </span>
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-zinc-400">Sprint Progress</span>
                <span className="text-sm font-medium text-white">{progressPercent}%</span>
              </div>
              <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 transition-all duration-500"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            {/* Stats Row */}
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-3 rounded-xl bg-zinc-800/50">
                <p className="text-2xl font-bold text-white">{totalPoints}</p>
                <p className="text-xs text-zinc-500">Total Points</p>
              </div>
              <div className="text-center p-3 rounded-xl bg-emerald-500/10">
                <p className="text-2xl font-bold text-emerald-400">{completedPoints}</p>
                <p className="text-xs text-zinc-500">Done</p>
              </div>
              <div className="text-center p-3 rounded-xl bg-cyan-500/10">
                <p className="text-2xl font-bold text-cyan-400">{inProgressPoints}</p>
                <p className="text-xs text-zinc-500">In Progress</p>
              </div>
              <div className="text-center p-3 rounded-xl bg-zinc-700/50">
                <p className="text-2xl font-bold text-zinc-400">{todoPoints}</p>
                <p className="text-xs text-zinc-500">To Do</p>
              </div>
            </div>

            {/* Burndown Chart */}
            <div className="mt-6">
              <h3 className="text-sm font-medium text-zinc-400 mb-4">Burndown Chart</h3>
              <BurndownChart data={burndownData} />
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="glass-card rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4">Quick Stats</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    Avg. Velocity
                  </span>
                  <span className="font-medium text-white">{avgVelocity} pts</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-purple-400" />
                    Days Remaining
                  </span>
                  <span className="font-medium text-white">7</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <Users className="w-4 h-4 text-cyan-400" />
                    Team Size
                  </span>
                  <span className="font-medium text-white">3 agents</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" />
                    Completion Rate
                  </span>
                  <span className="font-medium text-emerald-400">{progressPercent}%</span>
                </div>
              </div>
            </div>

            {/* Team Members */}
            <div className="glass-card rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4">Team</h3>
              <div className="space-y-3">
                {[
                  { name: 'Sophie', role: 'Lead Developer', tasks: 5, status: 'online' },
                  { name: 'Olivia', role: 'API Specialist', tasks: 1, status: 'online' },
                  { name: 'Claude', role: 'Documentation', tasks: 1, status: 'idle' },
                ].map((member) => (
                  <div key={member.name} className="flex items-center gap-3 p-2 rounded-lg hover:bg-zinc-800/50">
                    <div className="relative">
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div
                        className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-zinc-900 ${
                          member.status === 'online' ? 'bg-emerald-400' : 'bg-zinc-500'
                        }`}
                      />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{member.name}</p>
                      <p className="text-xs text-zinc-500">{member.role}</p>
                    </div>
                    <span className="text-xs text-zinc-500">{member.tasks} tasks</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sprint' && (
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-semibold text-white">{sprint.name}</h2>
              <p className="text-sm text-zinc-500">{sprint.goal}</p>
            </div>
            <div className="flex items-center gap-4 text-sm text-zinc-400">
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                7 days remaining
              </span>
              <span className="flex items-center gap-1">
                <Target className="w-4 h-4" />
                {totalPoints} points
              </span>
            </div>
          </div>
          <SprintBoard sprint={sprint} />
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Velocity Trend */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="font-semibold text-white mb-6">Velocity Trend</h3>
            <VelocityChart data={velocityData} />
            <div className="flex items-center justify-center gap-6 mt-4">
              <span className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-3 h-3 bg-purple-500/40 rounded" /> Planned
              </span>
              <span className="flex items-center gap-2 text-xs text-zinc-400">
                <div className="w-3 h-3 bg-cyan-500 rounded" /> Completed
              </span>
            </div>
          </div>

          {/* Performance Metrics */}
          <div className="glass-card rounded-2xl p-6">
            <h3 className="font-semibold text-white mb-6">Performance Metrics</h3>
            <div className="space-y-4">
              {[
                { label: 'Sprint Completion Rate', value: 94, trend: 'up' },
                { label: 'On-Time Delivery', value: 87, trend: 'up' },
                { label: 'Bug Fix Rate', value: 92, trend: 'stable' },
                { label: 'Code Quality Score', value: 88, trend: 'up' },
              ].map((metric) => (
                <div key={metric.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-zinc-400">{metric.label}</span>
                    <span className="flex items-center gap-1 text-sm font-medium text-white">
                      {metric.value}%
                      {metric.trend === 'up' && <TrendingUp className="w-3 h-3 text-emerald-400" />}
                      {metric.trend === 'down' && <TrendingDown className="w-3 h-3 text-red-400" />}
                    </span>
                  </div>
                  <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        metric.value >= 90
                          ? 'bg-emerald-500'
                          : metric.value >= 70
                          ? 'bg-cyan-500'
                          : 'bg-amber-500'
                      }`}
                      style={{ width: `${metric.value}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="lg:col-span-2 glass-card rounded-2xl p-6">
            <h3 className="font-semibold text-white mb-6">Recent Activity</h3>
            <div className="space-y-4">
              {[
                { time: '2 min ago', action: 'Task completed', detail: 'Add Edit Agent modal', agent: 'Sophie', type: 'completed' },
                { time: '15 min ago', action: 'Task started', detail: 'Connect real-time data', agent: 'Sophie', type: 'started' },
                { time: '1h ago', action: 'Review approved', detail: 'API Pipelines endpoints', agent: 'Olivia', type: 'approved' },
                { time: '3h ago', action: 'Task completed', detail: 'Agent Dashboard Personal', agent: 'Sophie', type: 'completed' },
                { time: '5h ago', action: 'Sprint started', detail: 'Sprint 23 - Dashboard Enhancement', agent: 'System', type: 'info' },
              ].map((activity, i) => (
                <div key={i} className="flex items-center gap-4 p-3 rounded-xl bg-zinc-800/30">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      activity.type === 'completed'
                        ? 'bg-emerald-400'
                        : activity.type === 'started'
                        ? 'bg-cyan-400'
                        : activity.type === 'approved'
                        ? 'bg-purple-400'
                        : 'bg-zinc-400'
                    }`}
                  />
                  <div className="flex-1">
                    <p className="text-sm text-zinc-200">
                      <span className="font-medium">{activity.action}:</span> {activity.detail}
                    </p>
                    <p className="text-xs text-zinc-500 flex items-center gap-2">
                      <Bot className="w-3 h-3" />
                      {activity.agent}
                      <span>•</span>
                      {activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProjectDetail;
