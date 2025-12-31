/**
 * Git Commit Detail Component
 *
 * Displays comprehensive commit information:
 * - Commit metadata (author, date, message, hash)
 * - Files changed with stats
 * - Full diff with syntax highlighting
 */

import { useState, useEffect } from 'react';
import {
  GitCommit,
  User,
  Calendar,
  FileText,
  Plus,
  Minus,
  Loader2,
  ChevronRight,
  ChevronDown,
  Copy,
  Check
} from 'lucide-react';
import api from '../../services/api';

interface CommitFile {
  path: string;
  status: string;
  additions: number;
  deletions: number;
}

interface CommitDetail {
  hash: string;
  author_name: string;
  author_email: string;
  date: string;
  message: string;
  files: CommitFile[];
  stats: {
    total_insertions: number;
    total_deletions: number;
    files_changed: number;
  };
}

interface GitCommitDetailProps {
  projectId: number;
  commitHash: string;
}

export function GitCommitDetail({ projectId, commitHash }: GitCommitDetailProps) {
  const [commit, setCommit] = useState<CommitDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [diff, setDiff] = useState<string | null>(null);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    loadCommitDetail();
  }, [projectId, commitHash]);

  const loadCommitDetail = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch single commit with details
      const response = await api.get(`/workspace/${projectId}/git/commits`, {
        params: { limit: 1 }
      });

      const commits = response.data as any[];
      if (commits.length > 0) {
        const commitData = commits.find((c: any) => c.hash === commitHash) || commits[0];

        setCommit({
          hash: commitData.hash,
          author_name: commitData.author_name,
          author_email: commitData.author_email,
          date: commitData.date,
          message: commitData.message,
          files: commitData.files || [],
          stats: commitData.stats || {
            total_insertions: 0,
            total_deletions: 0,
            files_changed: 0
          }
        });
      }
    } catch (err: any) {
      console.error('Failed to load commit detail:', err);
      setError(err.message || 'Failed to load commit');
    } finally {
      setLoading(false);
    }
  };

  const loadFileDiff = async (filePath: string) => {
    if (expandedFiles.has(filePath)) {
      // Collapse file
      const newExpanded = new Set(expandedFiles);
      newExpanded.delete(filePath);
      setExpandedFiles(newExpanded);
      return;
    }

    try {
      setLoadingDiff(true);
      const response = await api.get(`/workspace/${projectId}/git/diff`, {
        params: {
          commit: commitHash,
          file_path: filePath
        }
      });

      setDiff((response.data as any)?.diff);

      // Expand file
      const newExpanded = new Set(expandedFiles);
      newExpanded.add(filePath);
      setExpandedFiles(newExpanded);
    } catch (err: any) {
      console.error('Failed to load diff:', err);
    } finally {
      setLoadingDiff(false);
    }
  };

  const copyCommitHash = () => {
    navigator.clipboard.writeText(commitHash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'added':
      case 'a':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'modified':
      case 'm':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
      case 'deleted':
      case 'd':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'renamed':
      case 'r':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
      default:
        return 'text-zinc-400 bg-white/5 border-white/10';
    }
  };

  const getFileStatusLabel = (status: string) => {
    switch (status.toLowerCase()) {
      case 'a': return 'Added';
      case 'm': return 'Modified';
      case 'd': return 'Deleted';
      case 'r': return 'Renamed';
      default: return status;
    }
  };

  const renderDiff = (diffText: string) => {
    const lines = diffText.split('\n');

    return (
      <div className="mt-2 rounded-lg overflow-hidden border border-white/10">
        <div className="bg-[#1e1e1e] p-3 max-h-96 overflow-y-auto custom-scrollbar font-mono text-xs">
          {lines.map((line, index) => {
            let className = 'whitespace-pre px-2 py-0.5';
            if (line.startsWith('+') && !line.startsWith('+++')) {
              className += ' bg-green-500/10 text-green-300';
            } else if (line.startsWith('-') && !line.startsWith('---')) {
              className += ' bg-red-500/10 text-red-300';
            } else if (line.startsWith('@@')) {
              className += ' text-cyan-400 bg-cyan-500/5';
            } else if (line.startsWith('diff')) {
              className += ' text-purple-400 font-semibold';
            } else {
              className += ' text-zinc-400';
            }
            return (
              <div key={index} className={className}>
                {line || ' '}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading commit details...</p>
      </div>
    );
  }

  if (error || !commit) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <div className="text-red-400 text-4xl mb-3">⚠️</div>
        <p className="text-red-400 text-sm text-center">{error || 'Commit not found'}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 bg-gradient-to-r from-cyan-500/5 to-purple-500/5">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0 glow-cyan">
            <GitCommit className="w-5 h-5 text-white" />
          </div>

          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-white mb-1">
              {commit.message}
            </h3>

            <div className="flex items-center gap-3 text-xs text-zinc-400 mb-2">
              <span className="flex items-center gap-1">
                <User className="w-3 h-3" />
                {commit.author_name}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDate(commit.date)}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <code className="px-2 py-1 bg-white/5 text-cyan-400 rounded font-mono text-xs border border-white/10">
                {commit.hash.substring(0, 7)}
              </code>
              <button
                onClick={copyCommitHash}
                className="p-1 hover:bg-white/10 rounded transition-colors"
                title="Copy full hash"
              >
                {copied ? (
                  <Check className="w-3 h-3 text-green-400" />
                ) : (
                  <Copy className="w-3 h-3 text-zinc-400" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="px-4 py-3 border-b border-white/5 bg-white/[0.02]">
        <div className="flex items-center gap-6 text-xs">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-zinc-400" />
            <span className="text-white font-medium">
              {commit.stats.files_changed}
            </span>
            <span className="text-zinc-500">
              file{commit.stats.files_changed !== 1 ? 's' : ''} changed
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Plus className="w-4 h-4 text-green-400" />
            <span className="text-green-400 font-medium">
              {commit.stats.total_insertions}
            </span>
            <span className="text-zinc-500">additions</span>
          </div>

          <div className="flex items-center gap-2">
            <Minus className="w-4 h-4 text-red-400" />
            <span className="text-red-400 font-medium">
              {commit.stats.total_deletions}
            </span>
            <span className="text-zinc-500">deletions</span>
          </div>
        </div>
      </div>

      {/* Files Changed */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="p-4 space-y-2">
          <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            Files Changed
          </h4>

          {commit.files.length === 0 ? (
            <p className="text-zinc-500 text-sm py-4 text-center">
              No files changed in this commit
            </p>
          ) : (
            commit.files.map((file) => (
              <div
                key={file.path}
                className="rounded-lg border border-white/10 bg-white/[0.02] overflow-hidden"
              >
                <button
                  onClick={() => loadFileDiff(file.path)}
                  className="w-full px-3 py-2 flex items-center gap-3 hover:bg-white/5 transition-colors text-left"
                >
                  {expandedFiles.has(file.path) ? (
                    <ChevronDown className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                  )}

                  <FileText className="w-4 h-4 text-zinc-400 flex-shrink-0" />

                  <span className="flex-1 text-sm text-white font-mono truncate">
                    {file.path}
                  </span>

                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium border ${getFileStatusColor(
                      file.status
                    )}`}
                  >
                    {getFileStatusLabel(file.status)}
                  </span>

                  <div className="flex items-center gap-2 text-xs">
                    {file.additions > 0 && (
                      <span className="text-green-400">+{file.additions}</span>
                    )}
                    {file.deletions > 0 && (
                      <span className="text-red-400">-{file.deletions}</span>
                    )}
                  </div>
                </button>

                {expandedFiles.has(file.path) && (
                  <div className="border-t border-white/10">
                    {loadingDiff ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="w-5 h-5 text-cyan-500 animate-spin" />
                      </div>
                    ) : diff ? (
                      renderDiff(diff)
                    ) : null}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
