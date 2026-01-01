// Activity Feed page - Real-time activity stream

import { useState } from 'react';
import {
  Bell,
  CheckCircle,
  XCircle,
  AlertTriangle,
  MessageSquare,
  Bot,
  Circle,
  Target,
  PlayCircle,
  GitBranch,
  FileText,
  RefreshCw,
  Filter,
  Clock,
  User,
  Zap,
} from 'lucide-react';
import { useWebSocket } from '../hooks/useWebSocket';

// Types d'événements d'activité
type ActivityType =
  | 'task_created'
  | 'task_started'
  | 'task_completed'
  | 'task_failed'
  | 'task_assigned'
  | 'review_requested'
  | 'review_approved'
  | 'review_rejected'
  | 'agent_joined'
  | 'agent_left'
  | 'message_sent'
  | 'goal_completed'
  | 'goal_started'
  | 'conflict_detected'
  | 'conflict_resolved'
  | 'scheduled_triggered'
  | 'system_event';

interface ActivityEvent {
  id: string;
  type: ActivityType;
  timestamp: string;
  actor: {
    id: string;
    name: string;
    type: 'agent' | 'user' | 'system';
  };
  subject: {
    type: string;
    id: string;
    name: string;
  };
  message: string;
  metadata?: Record<string, unknown>;
  project_id?: string;
  circle_id?: string;
  read?: boolean;
}

// Configuration des icônes et couleurs par type
const activityConfig: Record<ActivityType, { icon: React.ReactNode; color: string; bgColor: string }> = {
  task_created: { icon: <FileText className="w-4 h-4" />, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  task_started: { icon: <PlayCircle className="w-4 h-4" />, color: 'text-cyan-400', bgColor: 'bg-cyan-500/20' },
  task_completed: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  task_failed: { icon: <XCircle className="w-4 h-4" />, color: 'text-red-400', bgColor: 'bg-red-500/20' },
  task_assigned: { icon: <User className="w-4 h-4" />, color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  review_requested: { icon: <GitBranch className="w-4 h-4" />, color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
  review_approved: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  review_rejected: { icon: <XCircle className="w-4 h-4" />, color: 'text-red-400', bgColor: 'bg-red-500/20' },
  agent_joined: { icon: <Bot className="w-4 h-4" />, color: 'text-indigo-400', bgColor: 'bg-indigo-500/20' },
  agent_left: { icon: <Bot className="w-4 h-4" />, color: 'text-zinc-400', bgColor: 'bg-zinc-500/20' },
  message_sent: { icon: <MessageSquare className="w-4 h-4" />, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  goal_completed: { icon: <Target className="w-4 h-4" />, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  goal_started: { icon: <Target className="w-4 h-4" />, color: 'text-cyan-400', bgColor: 'bg-cyan-500/20' },
  conflict_detected: { icon: <AlertTriangle className="w-4 h-4" />, color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
  conflict_resolved: { icon: <CheckCircle className="w-4 h-4" />, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  scheduled_triggered: { icon: <Clock className="w-4 h-4" />, color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  system_event: { icon: <Zap className="w-4 h-4" />, color: 'text-zinc-400', bgColor: 'bg-zinc-500/20' },
};

function formatRelativeTime(timestamp: string): string {
  const now = new Date();
  const date = new Date(timestamp);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'À l\'instant';
  if (diffMins < 60) return `Il y a ${diffMins} min`;
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  if (diffDays < 7) return `Il y a ${diffDays}j`;
  return date.toLocaleDateString('fr-FR');
}

function ActivityItem({ event }: { event: ActivityEvent }) {
  const config = activityConfig[event.type];

  return (
    <div className="glass-card rounded-xl p-4 hover:bg-white/5 transition-colors">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className={`p-2 rounded-lg ${config.bgColor}`}>
          <span className={config.color}>{config.icon}</span>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-zinc-200">{event.message}</p>

          {/* Metadata */}
          {event.metadata && (
            <div className="mt-2 flex flex-wrap gap-2">
              {event.metadata.files_modified !== undefined && (
                <span className="px-2 py-1 text-xs rounded-full bg-zinc-700/50 text-zinc-400">
                  {String(event.metadata.files_modified)} fichiers modifiés
                </span>
              )}
              {event.metadata.duration_minutes !== undefined && (
                <span className="px-2 py-1 text-xs rounded-full bg-zinc-700/50 text-zinc-400">
                  {String(event.metadata.duration_minutes)} min
                </span>
              )}
              {event.metadata.priority !== undefined && (
                <span className={`px-2 py-1 text-xs rounded-full ${
                  event.metadata.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                  event.metadata.priority === 'critical' ? 'bg-pink-500/20 text-pink-400' :
                  'bg-zinc-700/50 text-zinc-400'
                }`}>
                  {String(event.metadata.priority)}
                </span>
              )}
              {event.metadata.status !== undefined && (
                <span className={`px-2 py-1 text-xs rounded-full ${
                  event.metadata.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' :
                  'bg-red-500/20 text-red-400'
                }`}>
                  {String(event.metadata.status)}
                </span>
              )}
            </div>
          )}

          {/* Actor & Time */}
          <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
            <span className="flex items-center gap-1">
              {event.actor.type === 'agent' ? (
                <Bot className="w-3 h-3" />
              ) : event.actor.type === 'user' ? (
                <User className="w-3 h-3" />
              ) : (
                <Zap className="w-3 h-3" />
              )}
              {event.actor.name}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatRelativeTime(event.timestamp)}
            </span>
            {event.circle_id && (
              <>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Circle className="w-3 h-3" />
                  Circle
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function Activity() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [isLive, setIsLive] = useState(true);

  // WebSocket pour les mises à jour en temps réel
  useWebSocket({
    topics: isLive ? ['activity'] : [],
    onMessage: (event) => {
      if (isLive && event.type === 'activity' && event.data) {
        const activityEvent = event.data as unknown as ActivityEvent;
        setEvents(prev => [activityEvent, ...prev].slice(0, 100)); // Garder les 100 derniers
      }
    },
  });

  // Les événements arrivent via WebSocket en temps réel
  // Plus besoin de charger des données démo

  // Filtrer les événements
  const filteredEvents = events.filter(event => {
    if (filter === 'all') return true;
    if (filter === 'tasks') return event.type.startsWith('task_');
    if (filter === 'reviews') return event.type.startsWith('review_');
    if (filter === 'goals') return event.type.startsWith('goal_');
    if (filter === 'agents') return event.type.startsWith('agent_');
    if (filter === 'conflicts') return event.type.startsWith('conflict_');
    return true;
  });

  // Stats rapides
  const stats = {
    tasks_completed: events.filter(e => e.type === 'task_completed').length,
    reviews_pending: events.filter(e => e.type === 'review_requested').length,
    conflicts: events.filter(e => e.type === 'conflict_detected').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Bell className="w-8 h-8 text-purple-400" />
            Activity Feed
          </h1>
          <p className="text-zinc-400 mt-1">Suivez l'activité en temps réel</p>
        </div>

        <div className="flex items-center gap-3">
          {/* Live indicator */}
          <button
            onClick={() => setIsLive(!isLive)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
              isLive
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-zinc-700/50 text-zinc-400 border border-zinc-600'
            }`}
          >
            <div className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'}`} />
            {isLive ? 'Live' : 'Paused'}
          </button>

          {/* Refresh */}
          <button
            onClick={() => setEvents([])}
            className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
            title="Clear events"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/20">
              <CheckCircle className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.tasks_completed}</p>
              <p className="text-xs text-zinc-500">Tâches complétées</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-500/20">
              <GitBranch className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.reviews_pending}</p>
              <p className="text-xs text-zinc-500">Reviews en attente</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/20">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.conflicts}</p>
              <p className="text-xs text-zinc-500">Conflits</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        <Filter className="w-4 h-4 text-zinc-500 flex-shrink-0" />
        {[
          { key: 'all', label: 'Tout' },
          { key: 'tasks', label: 'Tâches' },
          { key: 'reviews', label: 'Reviews' },
          { key: 'goals', label: 'Objectifs' },
          { key: 'agents', label: 'Agents' },
          { key: 'conflicts', label: 'Conflits' },
        ].map(f => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
              filter === f.key
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                : 'bg-zinc-800/50 text-zinc-400 hover:bg-zinc-700/50'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Activity List */}
      <div className="space-y-3">
        {filteredEvents.length === 0 ? (
          <div className="glass-card rounded-xl p-12 text-center">
            <Bell className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
            <p className="text-zinc-400">Aucune activité pour le moment</p>
          </div>
        ) : (
          filteredEvents.map(event => (
            <ActivityItem key={event.id} event={event} />
          ))
        )}
      </div>

      {/* Load more */}
      {filteredEvents.length > 0 && (
        <div className="text-center">
          <button className="px-6 py-2 text-sm text-zinc-400 hover:text-white transition-colors">
            Charger plus d'événements...
          </button>
        </div>
      )}
    </div>
  );
}

export default Activity;
