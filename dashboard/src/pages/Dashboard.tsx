// Dashboard overview page with Web3 design

import { useQuery } from '@tanstack/react-query';
import {
  Bot,
  Circle,
  MessageSquare,
  CheckCircle,
  Clock,
  Zap,
  TrendingUp,
  Activity,
  ArrowUpRight,
  Sparkles,
} from 'lucide-react';
import { health, agents, circles, conversations } from '../services/api';
import { Link } from 'react-router-dom';

function StatCard({
  title,
  value,
  icon,
  gradient,
  glowClass,
  link,
  change,
}: {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  gradient: string;
  glowClass: string;
  link?: string;
  change?: string;
}) {
  const content = (
    <div className="stat-card p-6 group cursor-pointer">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-zinc-400">{title}</p>
          <p className="text-4xl font-bold text-white mt-2 gradient-text">{value}</p>
          {change && (
            <div className="flex items-center gap-1 mt-2 text-emerald-400 text-sm">
              <TrendingUp className="w-4 h-4" />
              <span>{change}</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-xl ${gradient} ${glowClass} group-hover:scale-110 transition-transform`}>
          {icon}
        </div>
      </div>
      {link && (
        <div className="mt-4 pt-4 border-t border-white/5 flex items-center gap-2 text-sm text-zinc-500 group-hover:text-purple-400 transition-colors">
          <span>View details</span>
          <ArrowUpRight className="w-4 h-4" />
        </div>
      )}
    </div>
  );

  if (link) {
    return <Link to={link}>{content}</Link>;
  }
  return content;
}

function AgentCard({ agent }: { agent: { id: number; name: string; role: string; status: string } }) {
  const statusColors: Record<string, string> = {
    busy: 'bg-amber-500',
    idle: 'bg-emerald-500',
    offline: 'bg-zinc-500',
  };

  return (
    <div className="flex items-center justify-between p-4 glass-card rounded-xl glass-card-hover">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ${statusColors[agent.status]} border-2 border-[#11111b]`} />
        </div>
        <div>
          <p className="font-semibold text-white">{agent.name}</p>
          <p className="text-sm text-zinc-500">{agent.role}</p>
        </div>
      </div>
      <span className={`
        text-xs px-3 py-1.5 rounded-full font-medium
        ${agent.status === 'busy'
          ? 'badge-warning'
          : agent.status === 'idle'
          ? 'badge-success'
          : 'badge'
        }
      `}>
        {agent.status}
      </span>
    </div>
  );
}

function CircleCard({ circle }: { circle: { id: string; name: string; status: string; agent_count: number; active_tasks: number } }) {
  const statusColors: Record<string, string> = {
    running: 'bg-emerald-500',
    starting: 'bg-amber-500',
    stopped: 'bg-zinc-500',
    stopping: 'bg-red-500',
  };

  return (
    <div className="flex items-center justify-between p-4 glass-card rounded-xl glass-card-hover">
      <div className="flex items-center gap-4">
        <div className="relative">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
            <Circle className="w-5 h-5 text-white" />
          </div>
          <div className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full ${statusColors[circle.status]} border-2 border-[#11111b]`} />
        </div>
        <div>
          <p className="font-semibold text-white">{circle.name}</p>
          <p className="text-sm text-zinc-500">
            {circle.agent_count} agents · {circle.active_tasks} tasks
          </p>
        </div>
      </div>
      <span className={`
        text-xs px-3 py-1.5 rounded-full font-medium
        ${circle.status === 'running'
          ? 'badge-success'
          : circle.status === 'starting'
          ? 'badge-warning'
          : 'badge'
        }
      `}>
        {circle.status}
      </span>
    </div>
  );
}

export function Dashboard() {
  const { data: healthData } = useQuery({
    queryKey: ['health'],
    queryFn: health.check,
    refetchInterval: 30000,
    refetchOnWindowFocus: false,
  });

  const { data: agentsData } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
    refetchOnWindowFocus: false,
  });

  const { data: circlesData } = useQuery({
    queryKey: ['circles'],
    queryFn: circles.list,
    refetchOnWindowFocus: false,
  });

  const { data: conversationsData } = useQuery({
    queryKey: ['conversations'],
    queryFn: conversations.list,
    refetchOnWindowFocus: false,
  });

  // Use real API data only
  const displayCircles = circlesData?.circles || [];
  const runningCircles = displayCircles.filter(c => c.status === 'running').length;
  const activeTasks = healthData?.active_tasks || displayCircles.reduce((sum, c) => sum + (c.active_tasks || 0), 0);
  const totalConversations = conversationsData?.total || 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-white">Dashboard</h1>
            <Sparkles className="w-6 h-6 text-purple-400 animate-pulse" />
          </div>
          <p className="text-zinc-500 mt-1">
            Overview of your GatheRing workspace
          </p>
        </div>

        <button className="btn-gradient px-6 py-3 rounded-xl flex items-center gap-2">
          <Zap className="w-5 h-5" />
          <span>Quick Action</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Agents"
          value={agentsData?.total ?? 0}
          icon={<Bot className="w-6 h-6 text-white" />}
          gradient="bg-gradient-to-br from-indigo-500 to-purple-500"
          glowClass="glow-purple"
          link="/agents"
        />
        <StatCard
          title="Active Circles"
          value={runningCircles}
          icon={<Circle className="w-6 h-6 text-white" />}
          gradient="bg-gradient-to-br from-emerald-500 to-cyan-500"
          glowClass="glow-cyan"
          link="/circles"
        />
        <StatCard
          title="Conversations"
          value={totalConversations}
          icon={<MessageSquare className="w-6 h-6 text-white" />}
          gradient="bg-gradient-to-br from-pink-500 to-rose-500"
          glowClass="glow-pink"
          link="/conversations"
        />
        <StatCard
          title="Active Tasks"
          value={activeTasks}
          icon={<CheckCircle className="w-6 h-6 text-white" />}
          gradient="bg-gradient-to-br from-amber-500 to-orange-500"
          glowClass="glow-purple"
        />
      </div>

      {/* Main content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agents panel */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <h2 className="font-semibold text-white text-lg">Agents</h2>
            </div>
            <Link to="/agents" className="text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1">
              View all
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="p-4 space-y-3">
            {agentsData?.agents.slice(0, 5).map(agent => (
              <AgentCard key={agent.id} agent={agent} />
            )) ?? (
              <div className="empty-state p-8 text-center">
                <Bot className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                <p className="text-zinc-500">No agents yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Circles panel */}
        <div className="glass-card rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
                <Circle className="w-4 h-4 text-white" />
              </div>
              <h2 className="font-semibold text-white text-lg">Circles</h2>
            </div>
            <Link to="/circles" className="text-sm text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1">
              View all
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
          <div className="p-4 space-y-3">
            {displayCircles.length === 0 ? (
              <div className="empty-state p-8 text-center">
                <Circle className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
                <p className="text-zinc-500">No circles yet</p>
              </div>
            ) : (
              displayCircles.slice(0, 5).map(circle => (
                <CircleCard key={circle.id} circle={circle} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* System info */}
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
            <Activity className="w-4 h-4 text-white" />
          </div>
          <h2 className="font-semibold text-white text-lg">System Status</h2>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-zinc-400 text-sm mb-1">
              <Clock className="w-4 h-4" />
              <span>Uptime</span>
            </div>
            <p className="text-xl font-semibold text-white">
              {Math.round(healthData?.uptime_seconds ?? 0)}s
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-zinc-400 text-sm mb-1">
              <Zap className="w-4 h-4" />
              <span>Version</span>
            </div>
            <p className="text-xl font-semibold text-white">
              {healthData?.version ?? 'unknown'}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-zinc-400 text-sm mb-1">
              <Activity className="w-4 h-4" />
              <span>Status</span>
            </div>
            <p className="text-xl font-semibold text-emerald-400">
              {healthData?.status ?? 'unknown'}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/5">
            <div className="flex items-center gap-2 text-zinc-400 text-sm mb-1">
              <Circle className="w-4 h-4" />
              <span>Total Circles</span>
            </div>
            <p className="text-xl font-semibold text-white">
              {healthData?.circles_count ?? 0}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
