/**
 * Git Actions Component
 *
 * Provides UI for Git operations:
 * - Stage/unstage files
 * - Create commits
 * - Push/pull from remote
 */

import { useState } from 'react';
import {
  GitCommit,
  Upload,
  Download,
  Loader2,
  AlertCircle,
  CheckCircle,
  FileText,
  FileEdit,
  FilePlus,
  FileX,
  Minus
} from 'lucide-react';

interface GitActionsProps {
  projectId: number;
  status: {
    branch: string;
    ahead: number;
    behind: number;
    modified: string[];
    added: string[];
    deleted: string[];
    untracked: string[];
    staged?: {
      modified: string[];
      added: string[];
      deleted: string[];
    };
  };
  onRefresh: () => void;
}

type FileStatus = 'modified' | 'added' | 'deleted' | 'untracked';

export function GitActions({ projectId, status, onRefresh }: GitActionsProps) {
  const [commitMessage, setCommitMessage] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const unstagedFiles: Array<{ path: string; status: FileStatus }> = [
    ...status.modified.map(f => ({ path: f, status: 'modified' as FileStatus })),
    ...status.added.map(f => ({ path: f, status: 'added' as FileStatus })),
    ...status.deleted.map(f => ({ path: f, status: 'deleted' as FileStatus })),
    ...status.untracked.map(f => ({ path: f, status: 'untracked' as FileStatus })),
  ];

  const stagedFiles: Array<{ path: string; status: FileStatus }> = [
    ...(status.staged?.modified || []).map(f => ({ path: f, status: 'modified' as FileStatus })),
    ...(status.staged?.added || []).map(f => ({ path: f, status: 'added' as FileStatus })),
    ...(status.staged?.deleted || []).map(f => ({ path: f, status: 'deleted' as FileStatus })),
  ];

  const hasChanges = unstagedFiles.length > 0 || stagedFiles.length > 0;

  const handleToggleFile = (filePath: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(filePath)) {
      newSelected.delete(filePath);
    } else {
      newSelected.add(filePath);
    }
    setSelectedFiles(newSelected);
  };

  const handleSelectAll = () => {
    if (selectedFiles.size === unstagedFiles.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(unstagedFiles.map(f => f.path)));
    }
  };

  const handleStage = async () => {
    if (selectedFiles.size === 0) {
      setError('No files selected to stage');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      // Send as direct array to match FastAPI Body(...) expectation
      const response = await fetch(`/api/workspace/${projectId}/git/stage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(Array.from(selectedFiles)),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      setSuccess(`Staged ${selectedFiles.size} file(s)`);
      setSelectedFiles(new Set());

      // Refresh status
      setTimeout(() => {
        onRefresh();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to stage files:', err);
      setError(err.message || 'Failed to stage files');
    } finally {
      setLoading(false);
    }
  };

  const handleUnstage = async (filePath: string) => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`/api/workspace/${projectId}/git/unstage`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify([filePath]),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      setSuccess(`Unstaged ${filePath}`);

      // Refresh status
      setTimeout(() => {
        onRefresh();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to unstage file:', err);
      setError(err.message || 'Failed to unstage file');
    } finally {
      setLoading(false);
    }
  };

  const handleCommit = async () => {
    if (!commitMessage.trim()) {
      setError('Commit message is required');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`/api/workspace/${projectId}/git/commit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: commitMessage.trim() }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSuccess(`Commit created: ${data.hash?.substring(0, 7) || 'success'}`);
      setCommitMessage('');

      // Refresh status
      setTimeout(() => {
        onRefresh();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to commit:', err);
      setError(err.message || 'Failed to commit');
    } finally {
      setLoading(false);
    }
  };

  const handlePush = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`/api/workspace/${projectId}/git/push`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          remote: 'origin',
          branch: status.branch,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      setSuccess('Pushed to remote');

      // Refresh status
      setTimeout(() => {
        onRefresh();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to push:', err);
      setError(err.message || 'Failed to push');
    } finally {
      setLoading(false);
    }
  };

  const handlePull = async () => {
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`/api/workspace/${projectId}/git/pull`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          remote: 'origin',
          branch: status.branch,
        }),
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      setSuccess('Pulled from remote');

      // Refresh status
      setTimeout(() => {
        onRefresh();
        setSuccess(null);
      }, 1500);
    } catch (err: any) {
      console.error('Failed to pull:', err);
      setError(err.message || 'Failed to pull');
    } finally {
      setLoading(false);
    }
  };

  const getFileIcon = (type: FileStatus) => {
    switch (type) {
      case 'modified':
        return <FileEdit className="w-4 h-4 text-blue-400" />;
      case 'added':
        return <FilePlus className="w-4 h-4 text-green-400" />;
      case 'deleted':
        return <FileX className="w-4 h-4 text-red-400" />;
      case 'untracked':
        return <FileText className="w-4 h-4 text-zinc-400" />;
    }
  };

  const getFileStatusColor = (type: FileStatus) => {
    switch (type) {
      case 'modified':
        return 'text-blue-400';
      case 'added':
        return 'text-green-400';
      case 'deleted':
        return 'text-red-400';
      case 'untracked':
        return 'text-zinc-400';
    }
  };

  if (!hasChanges) {
    return (
      <div className="p-4 space-y-4">
        {/* Push/Pull Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-white mb-2">Remote Operations</h4>
          <div className="flex gap-2">
            <button
              onClick={handlePull}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded hover:bg-cyan-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" />
              Pull
            </button>
            <button
              onClick={handlePush}
              disabled={loading || status.ahead === 0}
              className="flex-1 px-3 py-2 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded hover:bg-purple-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <Upload className="w-4 h-4" />
              Push
            </button>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
        {success && (
          <div className="px-3 py-2 bg-green-500/10 border border-green-500/30 rounded flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-green-400">{success}</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {/* Staged Files */}
        {stagedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-gradient-to-r from-green-500/30 to-transparent" />
              <h4 className="text-xs font-semibold text-green-400 uppercase tracking-wider">
                Staged ({stagedFiles.length})
              </h4>
              <div className="h-px flex-1 bg-gradient-to-l from-green-500/30 to-transparent" />
            </div>

            <div className="space-y-1">
              {stagedFiles.map((file) => (
                <div
                  key={file.path}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/5 transition-colors group"
                >
                  {getFileIcon(file.status)}
                  <span className={`text-sm font-mono flex-1 truncate ${getFileStatusColor(file.status)}`}>
                    {file.path}
                  </span>
                  <button
                    onClick={() => handleUnstage(file.path)}
                    disabled={loading}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/10 rounded transition-all"
                    title="Unstage file"
                  >
                    <Minus className="w-3 h-3 text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unstaged Files */}
        {unstagedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 flex-1">
                <div className="h-px flex-1 bg-gradient-to-r from-orange-500/30 to-transparent" />
                <h4 className="text-xs font-semibold text-orange-400 uppercase tracking-wider">
                  Unstaged ({unstagedFiles.length})
                </h4>
                <div className="h-px flex-1 bg-gradient-to-l from-orange-500/30 to-transparent" />
              </div>
              <button
                onClick={handleSelectAll}
                className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors ml-2"
              >
                {selectedFiles.size === unstagedFiles.length ? 'None' : 'All'}
              </button>
            </div>

            <div className="space-y-1">
              {unstagedFiles.map((file) => (
                <label
                  key={file.path}
                  className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/5 cursor-pointer transition-colors"
                >
                  <input
                    type="checkbox"
                    checked={selectedFiles.has(file.path)}
                    onChange={() => handleToggleFile(file.path)}
                    className="rounded bg-white/10 border-white/20 text-cyan-500 focus:ring-cyan-500"
                  />
                  {getFileIcon(file.status)}
                  <span className={`text-sm font-mono flex-1 truncate ${getFileStatusColor(file.status)}`}>
                    {file.path}
                  </span>
                </label>
              ))}
            </div>

            {/* Stage Button */}
            <button
              onClick={handleStage}
              disabled={loading || selectedFiles.size === 0}
              className="w-full px-3 py-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded hover:bg-cyan-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Upload className="w-4 h-4" />
              )}
              Stage Selected ({selectedFiles.size})
            </button>
          </div>
        )}

        {/* No Changes */}
        {!hasChanges && (
          <div className="flex flex-col items-center justify-center py-8">
            <div className="w-12 h-12 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center mb-2">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
            <p className="text-sm text-green-400 font-medium">Working tree clean</p>
            <p className="text-xs text-zinc-500">No changes to commit</p>
          </div>
        )}

        {/* Commit Section */}
        {stagedFiles.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-white">Commit Message</h4>
            <textarea
              value={commitMessage}
              onChange={(e) => setCommitMessage(e.target.value)}
              placeholder="Enter commit message..."
              rows={3}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:border-cyan-500/50 resize-none"
            />
            <button
              onClick={handleCommit}
              disabled={loading || !commitMessage.trim()}
              className="w-full px-3 py-2 bg-green-500/10 border border-green-500/30 text-green-400 rounded hover:bg-green-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm font-medium"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <GitCommit className="w-4 h-4" />
              )}
              Commit
            </button>
          </div>
        )}

        {/* Push/Pull Actions */}
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-white">Remote</h4>
          <div className="flex gap-2">
            <button
              onClick={handlePull}
              disabled={loading}
              className="flex-1 px-3 py-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 rounded hover:bg-cyan-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" />
              Pull
            </button>
            <button
              onClick={handlePush}
              disabled={loading || status.ahead === 0}
              className="flex-1 px-3 py-2 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded hover:bg-purple-500/20 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
            >
              <Upload className="w-4 h-4" />
              Push {status.ahead > 0 && `(${status.ahead})`}
            </button>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="px-3 py-2 bg-red-500/10 border border-red-500/30 rounded flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}
        {success && (
          <div className="px-3 py-2 bg-green-500/10 border border-green-500/30 rounded flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-green-400">{success}</p>
          </div>
        )}
      </div>
    </div>
  );
}
