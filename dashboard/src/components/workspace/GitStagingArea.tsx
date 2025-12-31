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
  FileText,
  FilePlus,
  FileEdit,
  FileX,
  Loader2,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  AlertCircle
} from 'lucide-react';
import api from '../../services/api';

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

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'modified':
        return <FileEdit className="w-4 h-4 text-blue-400" />;
      case 'added':
        return <FilePlus className="w-4 h-4 text-green-400" />;
      case 'deleted':
        return <FileX className="w-4 h-4 text-red-400" />;
      case 'untracked':
        return <FileText className="w-4 h-4 text-zinc-400" />;
      default:
        return <FileText className="w-4 h-4 text-zinc-400" />;
    }
  };

  const renderFileList = (
    files: string[],
    type: 'modified' | 'added' | 'deleted' | 'untracked',
    label: string
  ) => {
    if (files.length === 0) return null;

    return (
      <div className="space-y-1">
        <h5 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider px-2">
          {label} ({files.length})
        </h5>
        <div className="space-y-1">
          {files.map((file) => (
            <div
              key={file}
              className="px-2 py-1.5 rounded flex items-center gap-2 hover:bg-white/5 transition-colors"
            >
              {getFileIcon(type)}
              <span className="text-sm text-white font-mono truncate flex-1">
                {file}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
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

  const hasChanges =
    status.modified.length > 0 ||
    status.added.length > 0 ||
    status.deleted.length > 0 ||
    status.untracked.length > 0 ||
    status.staged.modified.length > 0 ||
    status.staged.added.length > 0 ||
    status.staged.deleted.length > 0;

  const totalChanges =
    status.modified.length +
    status.added.length +
    status.deleted.length +
    status.untracked.length;

  const totalStaged =
    status.staged.modified.length +
    status.staged.added.length +
    status.staged.deleted.length;

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

      {/* Status Summary */}
      <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02]">
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="flex flex-col">
            <span className="text-zinc-500 mb-1">Unstaged Changes</span>
            <span className="text-white font-semibold">
              {totalChanges === 0 ? 'None' : totalChanges}
            </span>
          </div>
          <div className="flex flex-col">
            <span className="text-zinc-500 mb-1">Staged Changes</span>
            <span className="text-white font-semibold">
              {totalStaged === 0 ? 'None' : totalStaged}
            </span>
          </div>
        </div>
      </div>

      {/* File Lists */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {!hasChanges ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center mb-3">
              <FileText className="w-8 h-8 text-green-400" />
            </div>
            <p className="text-green-400 font-medium mb-1">Working tree clean</p>
            <p className="text-zinc-500 text-sm text-center">
              No changes to commit
            </p>
          </div>
        ) : (
          <>
            {/* Staged Changes */}
            {totalStaged > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <div className="h-px flex-1 bg-gradient-to-r from-green-500/30 to-transparent" />
                  <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wider">
                    Staged for Commit
                  </h4>
                  <div className="h-px flex-1 bg-gradient-to-l from-green-500/30 to-transparent" />
                </div>

                {renderFileList(status.staged.modified, 'modified', 'Modified')}
                {renderFileList(status.staged.added, 'added', 'Added')}
                {renderFileList(status.staged.deleted, 'deleted', 'Deleted')}
              </div>
            )}

            {/* Unstaged Changes */}
            {totalChanges > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 mb-2">
                  <div className="h-px flex-1 bg-gradient-to-r from-orange-500/30 to-transparent" />
                  <h4 className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
                    Unstaged Changes
                  </h4>
                  <div className="h-px flex-1 bg-gradient-to-l from-orange-500/30 to-transparent" />
                </div>

                {renderFileList(status.modified, 'modified', 'Modified')}
                {renderFileList(status.added, 'added', 'Added')}
                {renderFileList(status.deleted, 'deleted', 'Deleted')}
                {renderFileList(status.untracked, 'untracked', 'Untracked')}
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer Actions (placeholder for future git commands) */}
      {hasChanges && (
        <div className="px-4 py-3 border-t border-white/5 bg-white/[0.02]">
          <p className="text-xs text-zinc-500 text-center">
            Use git commands in Terminal to stage/commit changes
          </p>
        </div>
      )}
    </div>
  );
}
