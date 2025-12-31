/**
 * Git Graph Component
 *
 * Visual git graph showing commits, branches, and merges
 * Similar to `git log --graph` visualization
 */

import { useState, useEffect } from 'react';
import {
  GitCommit,
  GitBranch,
  GitMerge,
  User,
  Calendar,
  Loader2,
  RefreshCw,
  Tag,
  AlertCircle
} from 'lucide-react';
import api from '../../services/api';

interface GraphCommit {
  hash: string;
  short_hash: string;
  parents: string[];
  parent_count: number;
  author_name: string;
  author_email: string;
  timestamp: number;
  date: string;
  message: string;
  branches: string[];
  tags: string[];
  is_merge: boolean;
}

interface GitGraphProps {
  projectId: number;
  onCommitSelect?: (commitHash: string) => void;
}

export function GitGraph({ projectId, onCommitSelect }: GitGraphProps) {
  const [commits, setCommits] = useState<GraphCommit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);

  useEffect(() => {
    loadGraph();
  }, [projectId]);

  const loadGraph = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/graph`, {
        params: { limit: 100, all_branches: true }
      });

      const data = response.data as any;
      setCommits(data.commits || []);
    } catch (err: any) {
      console.error('Failed to load git graph:', err);
      setError(err.message || 'Failed to load git graph');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadGraph(true);
  };

  const handleCommitClick = (commitHash: string) => {
    setSelectedCommit(commitHash);
    if (onCommitSelect) {
      onCommitSelect(commitHash);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days}d ago`;
    if (days < 30) return `${Math.floor(days / 7)}w ago`;
    return `${Math.floor(days / 30)}mo ago`;
  };

  const getBranchColor = (branch: string) => {
    // Color coding for common branches
    if (branch === 'main' || branch === 'master') return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30';
    if (branch === 'develop' || branch === 'dev') return 'text-purple-400 bg-purple-500/10 border-purple-500/30';
    if (branch.includes('feature')) return 'text-green-400 bg-green-500/10 border-green-500/30';
    if (branch.includes('fix') || branch.includes('bugfix')) return 'text-red-400 bg-red-500/10 border-red-500/30';
    if (branch.includes('release')) return 'text-orange-400 bg-orange-500/10 border-orange-500/30';
    return 'text-zinc-400 bg-white/5 border-white/10';
  };

  // Build graph structure (simplified version)
  const buildGraph = () => {
    const graph: { commit: GraphCommit; column: number }[] = [];
    const columns = new Map<string, number>();
    let nextColumn = 0;

    commits.forEach((commit) => {
      // Assign column based on parents
      let column = 0;

      if (commit.parents.length > 0) {
        const parentColumn = columns.get(commit.parents[0]);
        column = parentColumn !== undefined ? parentColumn : nextColumn++;
      } else {
        column = nextColumn++;
      }

      columns.set(commit.hash, column);
      graph.push({ commit, column });
    });

    return graph;
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading git graph...</p>
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

  const graphData = buildGraph();

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            Project Timeline
            <span className="ml-2 text-xs text-zinc-500">
              {commits.length} commits
            </span>
          </h3>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 hover:bg-white/10 rounded transition-colors disabled:opacity-50"
            title="Refresh graph"
          >
            <RefreshCw
              className={`w-4 h-4 text-zinc-400 ${refreshing ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
        {commits.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <GitBranch className="w-12 h-12 text-zinc-600 mb-3" />
            <p className="text-zinc-500 text-sm">No commits found</p>
          </div>
        ) : (
          <div className="space-y-0">
            {graphData.map(({ commit, column }, index) => {
              const prevCommit = index > 0 ? graphData[index - 1] : null;
              const nextCommit = index < graphData.length - 1 ? graphData[index + 1] : null;

              return (
                <div
                  key={commit.hash}
                  className={`relative flex items-start gap-3 pb-4 ${
                    selectedCommit === commit.hash ? 'bg-cyan-500/5' : ''
                  }`}
                >
                  {/* Graph visualization */}
                  <div className="flex-shrink-0 w-16 relative flex items-center justify-center">
                    {/* Connecting line from previous */}
                    {prevCommit && (
                      <div
                        className="absolute top-0 h-4 w-0.5 bg-cyan-500/30"
                        style={{
                          left: `${column * 16 + 8}px`,
                        }}
                      />
                    )}

                    {/* Commit node */}
                    <div
                      className="relative z-10"
                      style={{
                        marginLeft: `${column * 16}px`,
                      }}
                    >
                      {commit.is_merge ? (
                        <div className="w-4 h-4 rounded-full bg-purple-500 border-2 border-purple-400 glow-purple" />
                      ) : (
                        <div className="w-3 h-3 rounded-full bg-cyan-500 border-2 border-cyan-400" />
                      )}
                    </div>

                    {/* Connecting line to next */}
                    {nextCommit && (
                      <div
                        className="absolute bottom-0 h-full w-0.5 bg-cyan-500/30"
                        style={{
                          left: `${column * 16 + 8}px`,
                          top: '16px',
                        }}
                      />
                    )}
                  </div>

                  {/* Commit info */}
                  <button
                    onClick={() => handleCommitClick(commit.hash)}
                    className={`flex-1 text-left rounded-lg border transition-all p-3 ${
                      selectedCommit === commit.hash
                        ? 'bg-cyan-500/10 border-cyan-500/30'
                        : 'bg-white/[0.02] border-white/10 hover:bg-white/5 hover:border-white/20'
                    }`}
                  >
                    {/* Commit header */}
                    <div className="flex items-start gap-2 mb-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          {commit.is_merge && (
                            <GitMerge className="w-3 h-3 text-purple-400 flex-shrink-0" />
                          )}
                          <code className="px-1.5 py-0.5 bg-white/5 text-cyan-400 rounded font-mono text-xs border border-white/10">
                            {commit.short_hash}
                          </code>
                          {commit.branches.map((branch) => (
                            <span
                              key={branch}
                              className={`px-2 py-0.5 rounded text-xs font-medium border flex items-center gap-1 ${getBranchColor(
                                branch
                              )}`}
                            >
                              <GitBranch className="w-3 h-3" />
                              {branch}
                            </span>
                          ))}
                          {commit.tags.map((tag) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 bg-yellow-500/10 text-yellow-400 rounded text-xs font-medium border border-yellow-500/30 flex items-center gap-1"
                            >
                              <Tag className="w-3 h-3" />
                              {tag}
                            </span>
                          ))}
                        </div>

                        <p className="text-sm text-white font-medium mb-1 line-clamp-2">
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
                          {commit.is_merge && (
                            <span className="text-purple-400">
                              Merge ({commit.parent_count} parents)
                            </span>
                          )}
                        </div>
                      </div>

                      <GitCommit className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                    </div>
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
