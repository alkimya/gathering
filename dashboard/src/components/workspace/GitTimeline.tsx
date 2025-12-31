/**
 * Git Timeline Component - Web3 Dark Theme
 */

import { useState, useEffect } from 'react';
import { GitCommit, GitBranch, User, Calendar, Loader2, Eye } from 'lucide-react';
import api from '../../services/api';

interface Commit {
  hash: string;
  author_name: string;
  author_email: string;
  date: string;
  message: string;
  files?: string[];
}

interface GitTimelineProps {
  projectId: number;
  onCommitSelect?: (commitHash: string) => void;
  selectedCommit?: string | null;
}

export function GitTimeline({ projectId, onCommitSelect, selectedCommit: externalSelectedCommit }: GitTimelineProps) {
  const [commits, setCommits] = useState<Commit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);
  const [diff, setDiff] = useState<string | null>(null);
  const [loadingDiff, setLoadingDiff] = useState(false);

  // Use external selectedCommit if provided, otherwise use internal state
  const activeCommit = externalSelectedCommit !== undefined ? externalSelectedCommit : selectedCommit;

  useEffect(() => {
    loadCommits();
  }, [projectId]);

  const loadCommits = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/commits`, {
        params: { limit: 50 },
      });

      setCommits(response.data as Commit[]);
    } catch (err: any) {
      console.error('Failed to load commits:', err);
      setError(err.message || 'Failed to load commits');
    } finally {
      setLoading(false);
    }
  };

  const loadDiff = async (commitHash: string) => {
    try {
      setLoadingDiff(true);
      const response = await api.get(`/workspace/${projectId}/git/diff`, {
        params: { commit: commitHash },
      });
      setDiff((response.data as any)?.diff);
    } catch (err: any) {
      console.error('Failed to load diff:', err);
    } finally {
      setLoadingDiff(false);
    }
  };

  const handleCommitClick = (hash: string) => {
    if (onCommitSelect) {
      // If using external control, notify parent
      onCommitSelect(hash);
    } else {
      // Otherwise use internal state
      if (selectedCommit === hash) {
        setSelectedCommit(null);
        setDiff(null);
      } else {
        setSelectedCommit(hash);
        loadDiff(hash);
      }
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  const renderDiff = () => {
    if (!diff) return null;

    const lines = diff.split('\n');

    return (
      <div className="mt-3 rounded-lg overflow-hidden border border-white/10">
        <div className="bg-[#1e1e1e] p-3 max-h-96 overflow-y-auto custom-scrollbar font-mono text-xs">
          {lines.map((line, index) => {
            let className = 'whitespace-pre';
            if (line.startsWith('+') && !line.startsWith('+++')) {
              className += ' bg-green-500/10 text-green-300';
            } else if (line.startsWith('-') && !line.startsWith('---')) {
              className += ' bg-red-500/10 text-red-300';
            } else if (line.startsWith('@@')) {
              className += ' text-cyan-400';
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
      <div className="flex flex-col items-center justify-center h-full p-4">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading commits...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <div className="text-red-400 text-4xl mb-3">⚠️</div>
        <p className="text-red-400 text-sm text-center">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-cyan-400" />
          Git Timeline
          <span className="ml-auto text-xs text-zinc-500">{commits.length} commits</span>
        </h3>
      </div>

      {/* Commits list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {commits.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-500 text-sm">No commits found</p>
          </div>
        ) : (
          commits.map((commit) => (
            <div
              key={commit.hash}
              className={`p-3 rounded-lg border transition-all cursor-pointer ${
                activeCommit === commit.hash
                  ? 'bg-cyan-500/10 border-cyan-500/30'
                  : 'bg-white/5 border-white/10 hover:bg-white/10'
              }`}
              onClick={() => handleCommitClick(commit.hash)}
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center flex-shrink-0 glow-cyan">
                  <GitCommit className="w-4 h-4 text-white" />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium line-clamp-2 mb-1">
                    {commit.message}
                  </p>

                  <div className="flex items-center gap-3 text-xs text-zinc-500">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {commit.author_name}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {formatDate(commit.date)}
                    </span>
                  </div>

                  <div className="mt-2 flex items-center gap-2 text-xs">
                    <code className="px-2 py-0.5 bg-white/5 text-cyan-400 rounded font-mono">
                      {commit.hash.substring(0, 7)}
                    </code>
                    {activeCommit === commit.hash && !onCommitSelect && (
                      <span className="text-cyan-400 flex items-center gap-1">
                        <Eye className="w-3 h-3" />
                        Viewing diff
                      </span>
                    )}
                  </div>

                  {/* Only show inline diff if using internal state (not external control) */}
                  {!onCommitSelect && activeCommit === commit.hash && (
                    <>
                      {loadingDiff ? (
                        <div className="mt-3 flex items-center gap-2 text-zinc-400 text-sm">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Loading diff...
                        </div>
                      ) : (
                        renderDiff()
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
