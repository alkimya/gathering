/**
 * Git Graph Component - GitFlow Visualization
 *
 * Horizontal timeline showing branches as parallel lanes with merges
 * Similar to GitFlow diagram with branches flowing left to right
 */

import { useState } from 'react';
import {
  GitBranch,
  Loader2,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { useGitGraph } from '../../hooks/useGitCache';

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
  const { graph, loading, error, reload } = useGitGraph(projectId, 100);
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);

  const commits: GraphCommit[] = graph?.commits || [];

  const handleRefresh = () => {
    reload(true);
  };

  const handleCommitClick = (commitHash: string) => {
    setSelectedCommit(commitHash);
    if (onCommitSelect) {
      onCommitSelect(commitHash);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const getBranchColor = (branch: string) => {
    if (branch === 'main' || branch === 'master') return '#06b6d4'; // cyan
    if (branch === 'develop' || branch === 'dev') return '#a855f7'; // purple
    if (branch.includes('feature')) return '#22c55e'; // green
    if (branch.includes('fix') || branch.includes('bugfix')) return '#ef4444'; // red
    if (branch.includes('release')) return '#f97316'; // orange
    return '#71717a'; // zinc
  };

  const getBranchLabel = (branch: string) => {
    if (branch.startsWith('origin/')) return branch.substring(7);
    return branch;
  };

  // Build GitFlow layout
  const buildGitFlowLayout = () => {
    // 1. Identify all unique branches from commits
    const branchSet = new Set<string>();
    commits.forEach(commit => {
      commit.branches.forEach(b => branchSet.add(b));
    });

    // 2. Order branches (main/master first, develop second, then others)
    const orderedBranches = Array.from(branchSet).sort((a, b) => {
      const aMain = a === 'main' || a === 'master';
      const bMain = b === 'main' || b === 'master';
      const aDev = a === 'develop' || a === 'dev';
      const bDev = b === 'develop' || b === 'dev';

      if (aMain && !bMain) return -1;
      if (!aMain && bMain) return 1;
      if (aDev && !bDev) return -1;
      if (!aDev && bDev) return 1;
      return a.localeCompare(b);
    });

    // 3. Assign lane (row) to each branch
    const branchLanes = new Map<string, number>();
    orderedBranches.forEach((branch, index) => {
      branchLanes.set(branch, index);
    });

    // 4. Position commits horizontally by index with smart spacing, vertically by branch
    interface LayoutCommit {
      commit: GraphCommit;
      x: number; // horizontal position (index-based with spacing)
      lane: number; // vertical lane (branch)
      branch: string;
    }

    const layoutCommits: LayoutCommit[] = [];
    const commitPositions = new Map<string, { x: number; lane: number }>();

    // Sort commits by timestamp (oldest first)
    const sortedCommits = [...commits].sort((a, b) => a.timestamp - b.timestamp);

    sortedCommits.forEach((commit, index) => {
      // Determine branch (use first branch if multiple)
      const branch = commit.branches.length > 0 ? commit.branches[0] : 'unknown';
      const lane = branchLanes.get(branch) ?? orderedBranches.length;

      // Position x based on index (evenly spaced)
      // Use index instead of timestamp to ensure all commits are visible
      const x = (index / Math.max(sortedCommits.length - 1, 1)) * 100;

      layoutCommits.push({ commit, x, lane, branch });
      commitPositions.set(commit.hash, { x, lane });
    });

    // 5. Build merge paths
    interface MergePath {
      fromHash: string;
      toHash: string;
      fromX: number;
      fromLane: number;
      toX: number;
      toLane: number;
      isMerge: boolean;
    }

    const mergePaths: MergePath[] = [];
    commits.forEach((commit) => {
      const fromPos = commitPositions.get(commit.hash);
      if (!fromPos) return;

      commit.parents.forEach((parentHash, pIndex) => {
        const toPos = commitPositions.get(parentHash);
        if (toPos) {
          mergePaths.push({
            fromHash: commit.hash,
            toHash: parentHash,
            fromX: fromPos.x,
            fromLane: fromPos.lane,
            toX: toPos.x,
            toLane: toPos.lane,
            isMerge: commit.is_merge && pIndex > 0,
          });
        }
      });
    });

    return { layoutCommits, mergePaths, orderedBranches, branchLanes };
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

  const { layoutCommits, mergePaths, orderedBranches } = buildGitFlowLayout();

  const LANE_HEIGHT = 80;
  const COMMIT_RADIUS = 6;
  const SVG_WIDTH = 1200;
  const SVG_HEIGHT = (orderedBranches.length + 1) * LANE_HEIGHT;
  const BRANCH_LABEL_WIDTH = 120;

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            GitFlow Graph
            <span className="ml-2 text-xs text-zinc-500">
              {commits.length} commits • {orderedBranches.length} branches
            </span>
          </h3>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-1.5 hover:bg-white/10 rounded transition-colors disabled:opacity-50"
            title="Refresh graph"
          >
            <RefreshCw
              className={`w-4 h-4 text-zinc-400 ${loading ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* GitFlow Graph */}
      <div className="flex-1 overflow-auto custom-scrollbar p-4">
        {commits.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <GitBranch className="w-12 h-12 text-zinc-600 mb-3" />
            <p className="text-zinc-500 text-sm">No commits found</p>
          </div>
        ) : (
          <div className="relative" style={{ minWidth: `${SVG_WIDTH + BRANCH_LABEL_WIDTH}px` }}>
            {/* Branch labels on the left */}
            <div className="absolute left-0 top-0" style={{ width: `${BRANCH_LABEL_WIDTH}px` }}>
              {orderedBranches.map((branch, index) => (
                <div
                  key={branch}
                  className="flex items-center gap-2 px-3 py-2"
                  style={{
                    height: `${LANE_HEIGHT}px`,
                    top: `${index * LANE_HEIGHT + LANE_HEIGHT / 2 - 20}px`,
                    position: 'absolute',
                  }}
                >
                  <GitBranch
                    className="w-4 h-4 flex-shrink-0"
                    style={{ color: getBranchColor(branch) }}
                  />
                  <span
                    className="text-xs font-medium truncate"
                    style={{ color: getBranchColor(branch) }}
                    title={branch}
                  >
                    {getBranchLabel(branch)}
                  </span>
                </div>
              ))}
            </div>

            {/* SVG Graph */}
            <svg
              width={SVG_WIDTH}
              height={SVG_HEIGHT}
              style={{ marginLeft: `${BRANCH_LABEL_WIDTH}px` }}
              className="overflow-visible"
            >
              {/* Background lane lines */}
              {orderedBranches.map((branch, index) => (
                <line
                  key={`lane-${branch}`}
                  x1={0}
                  y1={index * LANE_HEIGHT + LANE_HEIGHT / 2}
                  x2={SVG_WIDTH}
                  y2={index * LANE_HEIGHT + LANE_HEIGHT / 2}
                  stroke={getBranchColor(branch)}
                  strokeWidth="1"
                  opacity="0.1"
                />
              ))}

              {/* Draw merge paths */}
              {mergePaths.map((path, index) => {
                const x1 = (path.fromX / 100) * SVG_WIDTH;
                const y1 = path.fromLane * LANE_HEIGHT + LANE_HEIGHT / 2;
                const x2 = (path.toX / 100) * SVG_WIDTH;
                const y2 = path.toLane * LANE_HEIGHT + LANE_HEIGHT / 2;

                // Curved path for branch/merge connections
                if (path.fromLane !== path.toLane) {
                  const controlX1 = x1 + (x2 - x1) * 0.3;
                  const controlX2 = x1 + (x2 - x1) * 0.7;
                  const pathD = `M ${x1},${y1} C ${controlX1},${y1} ${controlX2},${y2} ${x2},${y2}`;

                  return (
                    <path
                      key={`merge-${index}`}
                      d={pathD}
                      stroke={path.isMerge ? '#a855f7' : '#06b6d4'}
                      strokeWidth="2"
                      fill="none"
                      opacity="0.5"
                      strokeDasharray={path.isMerge ? '4,2' : 'none'}
                    />
                  );
                } else {
                  // Straight line for same lane
                  return (
                    <line
                      key={`line-${index}`}
                      x1={x1}
                      y1={y1}
                      x2={x2}
                      y2={y2}
                      stroke="#06b6d4"
                      strokeWidth="2"
                      opacity="0.3"
                    />
                  );
                }
              })}

              {/* Draw commits */}
              {layoutCommits.map(({ commit, x, lane, branch }) => {
                const cx = (x / 100) * SVG_WIDTH;
                const cy = lane * LANE_HEIGHT + LANE_HEIGHT / 2;
                const isSelected = selectedCommit === commit.hash;

                return (
                  <g key={commit.hash}>
                    {/* Commit circle */}
                    <circle
                      cx={cx}
                      cy={cy}
                      r={commit.is_merge ? COMMIT_RADIUS + 2 : COMMIT_RADIUS}
                      fill={isSelected ? '#22d3ee' : getBranchColor(branch)}
                      stroke={isSelected ? '#67e8f9' : '#fff'}
                      strokeWidth={isSelected ? '3' : '2'}
                      className="cursor-pointer transition-all hover:r-8"
                      onClick={() => handleCommitClick(commit.hash)}
                      style={{
                        filter: commit.is_merge
                          ? 'drop-shadow(0 0 4px rgba(168,85,247,0.5))'
                          : isSelected
                          ? 'drop-shadow(0 0 6px rgba(34,211,238,0.8))'
                          : 'none',
                      }}
                    />

                    {/* Hover tooltip area */}
                    <title>
                      {commit.message}
                      {'\n'}
                      {commit.author_name} • {formatDate(commit.date)}
                      {'\n'}
                      {commit.short_hash}
                      {commit.tags.length > 0 && '\n' + commit.tags.join(', ')}
                    </title>

                    {/* Tag labels */}
                    {commit.tags.length > 0 && (
                      <g>
                        <rect
                          x={cx - 30}
                          y={cy - LANE_HEIGHT / 2 + 5}
                          width="60"
                          height="16"
                          fill="#854d0e"
                          stroke="#fbbf24"
                          strokeWidth="1"
                          rx="3"
                        />
                        <text
                          x={cx}
                          y={cy - LANE_HEIGHT / 2 + 16}
                          textAnchor="middle"
                          fontSize="10"
                          fill="#fbbf24"
                          fontWeight="600"
                        >
                          {commit.tags[0]}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Legend */}
            <div className="mt-4 flex items-center gap-4 text-xs text-zinc-400">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-cyan-500" />
                <span>Main/Master</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-500" />
                <span>Develop</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span>Feature</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span>Bugfix</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 rounded-full bg-purple-500 border-2 border-white" />
                <span>Merge commit</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
