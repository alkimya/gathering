/**
 * Git Staging Area Component
 *
 * Displays git working directory status:
 * - Modified files (staged and unstaged)
 * - Untracked files
 * - Branch status (ahead/behind remote)
 * - Staged changes visualization
 */

import { useState, useEffect } from 'react';
import {
  GitBranch,
  Loader2,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  AlertCircle
} from 'lucide-react';
import api from '../../services/api';
import { GitActions } from './GitActions';

interface GitStatus {
  branch: string;
  ahead: number;
  behind: number;
  modified: string[];
  added: string[];
  deleted: string[];
  untracked: string[];
  staged: {
    modified: string[];
    added: string[];
    deleted: string[];
  };
}

interface GitStagingAreaProps {
  projectId: number;
}

export function GitStagingArea({ projectId }: GitStagingAreaProps) {
  const [status, setStatus] = useState<GitStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadStatus();
  }, [projectId]);

  const loadStatus = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/status`);
      const data = response.data as any;

      // Handle nested status structure
      const statusData = data.status || data;

      // Ensure staged object exists (might not be in backend response)
      if (!statusData.staged) {
        statusData.staged = {
          modified: [],
          added: [],
          deleted: []
        };
      }

      setStatus(statusData as GitStatus);
    } catch (err: any) {
      console.error('Failed to load git status:', err);
      setError(err.message || 'Failed to load git status');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadStatus(true);
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading git status...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <AlertCircle className="w-8 h-8 text-red-400 mb-3" />
        <p className="text-red-400 text-sm text-center mb-3">{error}</p>
        <button
          onClick={handleRefresh}
          className="px-3 py-1.5 bg-red-500/10 border border-red-500/30 text-red-400 rounded hover:bg-red-500/20 transition-colors text-sm"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <p className="text-zinc-500 text-sm">No git status available</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            Working Directory
          </h3>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 hover:bg-white/10 rounded transition-colors disabled:opacity-50"
            title="Refresh status"
          >
            <RefreshCw
              className={`w-4 h-4 text-zinc-400 ${refreshing ? 'animate-spin' : ''}`}
            />
          </button>
        </div>

        {/* Branch Info */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">Branch:</span>
            <code className="px-2 py-0.5 bg-white/5 text-cyan-400 rounded font-mono text-xs border border-white/10">
              {status.branch}
            </code>
          </div>

          {(status.ahead > 0 || status.behind > 0) && (
            <div className="flex items-center gap-3 text-xs">
              {status.ahead > 0 && (
                <div className="flex items-center gap-1 text-green-400">
                  <ArrowUp className="w-3 h-3" />
                  <span>{status.ahead} ahead</span>
                </div>
              )}
              {status.behind > 0 && (
                <div className="flex items-center gap-1 text-orange-400">
                  <ArrowDown className="w-3 h-3" />
                  <span>{status.behind} behind</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Git Actions */}
      <div className="flex-1 overflow-hidden">
        <GitActions
          projectId={projectId}
          status={status}
          onRefresh={() => loadStatus(true)}
        />
      </div>
    </div>
  );
}
