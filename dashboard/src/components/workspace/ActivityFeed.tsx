/**
 * Activity Feed Component - Web3 Dark Theme
 */

import { useState, useEffect } from 'react';
import { Activity, FileEdit, GitCommit, PlayCircle, CheckCircle, Loader2, RefreshCw } from 'lucide-react';
import api from '../../services/api';

interface ActivityItem {
  id: number;
  type: string;
  timestamp: string;
  details: any;
  agent_id?: number;
}

interface ActivityFeedProps {
  projectId: number;
}

export function ActivityFeed({ projectId }: ActivityFeedProps) {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    loadActivities();

    if (autoRefresh) {
      const interval = setInterval(loadActivities, 5000);
      return () => clearInterval(interval);
    }
  }, [projectId, autoRefresh]);

  const loadActivities = async () => {
    try {
      setError(null);

      const response = await api.get(`/workspace/${projectId}/activities`, {
        params: { limit: 50 },
      });

      setActivities(response.data as ActivityItem[]);
    } catch (err: any) {
      console.error('Failed to load activities:', err);
      setError(err.message || 'Failed to load activities');
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type: string) => {
    const iconMap: Record<string, { icon: any; color: string; glow: string }> = {
      file_created: { icon: FileEdit, color: 'text-green-400', glow: 'from-green-500 to-emerald-500' },
      file_edited: { icon: FileEdit, color: 'text-amber-400', glow: 'from-amber-500 to-yellow-500' },
      commit: { icon: GitCommit, color: 'text-cyan-400', glow: 'from-cyan-500 to-blue-500' },
      test_run: { icon: PlayCircle, color: 'text-purple-400', glow: 'from-purple-500 to-pink-500' },
      test_passed: { icon: CheckCircle, color: 'text-green-400', glow: 'from-green-500 to-emerald-500' },
    };

    return iconMap[type] || { icon: Activity, color: 'text-zinc-400', glow: 'from-zinc-500 to-zinc-600' };
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading activities...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Activity className="w-4 h-4 text-purple-400" />
          Activity Feed
        </h3>

        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`p-1.5 rounded transition-colors ${
            autoRefresh ? 'bg-purple-500/20 text-purple-400' : 'bg-white/5 text-zinc-500 hover:bg-white/10'
          }`}
          title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
        >
          <RefreshCw className={`w-3 h-3 ${autoRefresh ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Activities list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {error ? (
          <div className="text-center py-8">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Activity className="w-12 h-12 text-zinc-600 mb-3" />
            <p className="text-zinc-500 text-sm">No activities yet</p>
            <p className="text-zinc-600 text-xs mt-1">Activities will appear here when agents work</p>
          </div>
        ) : (
          activities.map((activity) => {
            const config = getActivityIcon(activity.type);
            const Icon = config.icon;

            return (
              <div
                key={activity.id}
                className="flex items-start gap-3 p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all"
              >
                <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${config.glow} flex items-center justify-center flex-shrink-0`}>
                  <Icon className="w-4 h-4 text-white" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium">
                    {activity.details.file_path || activity.details.message || activity.type}
                  </p>
                  <p className="text-xs text-zinc-500 mt-1">{formatTime(activity.timestamp)}</p>
                  {activity.agent_id && (
                    <p className="text-xs text-cyan-400 mt-1">Agent #{activity.agent_id}</p>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
