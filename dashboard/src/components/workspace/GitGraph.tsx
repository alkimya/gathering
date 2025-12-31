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

  // Build graph structure with proper branching visualization
  const buildGraph = () => {
    interface GraphNode {
      commit: GraphCommit;
      column: number;
      paths: { from: number; to: number; isMerge?: boolean }[];
    }

    const graph: GraphNode[] = [];
    const commitColumns = new Map<string, number>();
    const branchColumns = new Map<string, number>();
    let nextColumn = 0;

    // First pass: assign columns based on branches
    commits.forEach((commit) => {
      let column = 0;

      // If commit has branches, use branch column
      if (commit.branches.length > 0) {
        const branchName = commit.branches[0];
        if (!branchColumns.has(branchName)) {
          branchColumns.set(branchName, nextColumn++);
        }
        column = branchColumns.get(branchName)!;
      } else if (commit.parents.length > 0) {
        // Use parent's column
        const parentColumn = commitColumns.get(commit.parents[0]);
        column = parentColumn !== undefined ? parentColumn : nextColumn++;
      } else {
        column = nextColumn++;
      }

      commitColumns.set(commit.hash, column);
    });

    // Second pass: build graph with paths
    commits.forEach((commit) => {
      const column = commitColumns.get(commit.hash) || 0;
      const paths: { from: number; to: number; isMerge?: boolean }[] = [];

      // Add paths to parents
      commit.parents.forEach((parentHash, pIndex) => {
        const parentColumn = commitColumns.get(parentHash);
        if (parentColumn !== undefined) {
          paths.push({
            from: column,
            to: parentColumn,
            isMerge: commit.is_merge && pIndex > 0,
          });
        }
      });

      graph.push({ commit, column, paths });
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
          <div className="relative">
            {graphData.map(({ commit, column, paths }, index) => {
              const nextNode = index < graphData.length - 1 ? graphData[index + 1] : null;
              const COLUMN_WIDTH = 24;
              const ROW_HEIGHT = 80;
              const NODE_SIZE = commit.is_merge ? 10 : 8;

              return (
                <div
                  key={commit.hash}
                  className={`relative flex items-start gap-3 ${
                    selectedCommit === commit.hash ? 'bg-cyan-500/5 rounded-lg' : ''
                  }`}
                  style={{ minHeight: `${ROW_HEIGHT}px` }}
                >
                  {/* SVG Graph visualization */}
                  <svg
                    className="flex-shrink-0"
                    width={COLUMN_WIDTH * 6}
                    height={ROW_HEIGHT}
                    style={{ position: 'relative', top: 0 }}
                  >
                    {/* Draw paths to next commits */}
                    {nextNode && (
                      <line
                        x1={column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                        y1={NODE_SIZE}
                        x2={nextNode.column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                        y2={ROW_HEIGHT}
                        stroke="rgba(34, 211, 238, 0.3)"
                        strokeWidth="2"
                      />
                    )}

                    {/* Draw merge paths (curved lines for merges) */}
                    {paths.map((path, pIndex) => {
                      const nextIndex = commits.findIndex(c => c.hash === commit.parents[pIndex]);
                      if (nextIndex === -1) return null;

                      const nextCommit = graphData[nextIndex];
                      if (!nextCommit) return null;

                      const startX = column * COLUMN_WIDTH + COLUMN_WIDTH / 2;
                      const startY = NODE_SIZE;
                      const endX = nextCommit.column * COLUMN_WIDTH + COLUMN_WIDTH / 2;
                      const endY = (nextIndex - index) * ROW_HEIGHT;

                      // Use curved path for branches/merges
                      if (path.from !== path.to) {
                        const controlY = endY / 2;
                        const pathD = `M ${startX},${startY} C ${startX},${controlY} ${endX},${controlY} ${endX},${endY}`;

                        return (
                          <path
                            key={pIndex}
                            d={pathD}
                            stroke={path.isMerge ? 'rgba(168, 85, 247, 0.5)' : 'rgba(34, 211, 238, 0.3)'}
                            strokeWidth={path.isMerge ? '2.5' : '2'}
                            fill="none"
                            strokeDasharray={path.isMerge ? '4,2' : 'none'}
                          />
                        );
                      }
                      return null;
                    })}

                    {/* Commit node */}
                    <circle
                      cx={column * COLUMN_WIDTH + COLUMN_WIDTH / 2}
                      cy={NODE_SIZE}
                      r={NODE_SIZE / 2}
                      fill={commit.is_merge ? '#a855f7' : '#06b6d4'}
                      stroke={commit.is_merge ? '#c084fc' : '#22d3ee'}
                      strokeWidth="2"
                      className={commit.is_merge ? 'drop-shadow-[0_0_4px_rgba(168,85,247,0.5)]' : ''}
                    />

                    {/* Branch label background */}
                    {commit.branches.length > 0 && (
                      <rect
                        x={column * COLUMN_WIDTH + COLUMN_WIDTH / 2 + 12}
                        y={NODE_SIZE - 8}
                        width="60"
                        height="16"
                        fill="rgba(0,0,0,0.5)"
                        rx="3"
                      />
                    )}
                  </svg>

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
