/**
 * Git Branch Manager Component
 *
 * Displays multi-branch information:
 * - Current branch
 * - Local branches
 * - Remote branches
 * - Branch-specific commit history
 */

import { useState, useEffect } from 'react';
import {
  GitBranch,
  GitMerge,
  Radio,
  Loader2,
  RefreshCw,
  Calendar,
  User
} from 'lucide-react';
import api from '../../services/api';

interface Branch {
  name: string;
  is_current: boolean;
  is_remote: boolean;
  last_commit?: {
    hash: string;
    author_name: string;
    date: string;
    message: string;
  };
}

interface GitBranchManagerProps {
  projectId: number;
  onBranchSelect?: (branch: string) => void;
}

export function GitBranchManager({ projectId, onBranchSelect }: GitBranchManagerProps) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [currentBranch, setCurrentBranch] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  useEffect(() => {
    loadBranches();
  }, [projectId]);

  const loadBranches = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      const response = await api.get(`/workspace/${projectId}/git/branches`);
      const data = response.data as any;

      // Handle nested branches structure
      const branchesData = data.branches || data;

      setCurrentBranch(branchesData.current || '');

      // Parse branches array
      const allBranches: Branch[] = [];

      if (branchesData.branches && Array.isArray(branchesData.branches)) {
        branchesData.branches.forEach((branch: any) => {
          allBranches.push({
            name: branch.name,
            is_current: branch.current || false,
            is_remote: branch.type === 'remote'
          });
        });
      }

      setBranches(allBranches);
    } catch (err: any) {
      console.error('Failed to load branches:', err);
      setError(err.message || 'Failed to load branches');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    loadBranches(true);
  };

  const handleBranchClick = (branchName: string) => {
    setSelectedBranch(branchName);
    if (onBranchSelect) {
      onBranchSelect(branchName);
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

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <Loader2 className="w-8 h-8 text-cyan-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading branches...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 p-4">
        <div className="text-red-400 text-4xl mb-3">⚠️</div>
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

  const localBranches = branches.filter((b) => !b.is_remote);
  const remoteBranches = branches.filter((b) => b.is_remote);

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-cyan-400" />
            Branches
            <span className="ml-2 text-xs text-zinc-500">
              {branches.length} total
            </span>
          </h3>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 hover:bg-white/10 rounded transition-colors disabled:opacity-50"
            title="Refresh branches"
          >
            <RefreshCw
              className={`w-4 h-4 text-zinc-400 ${refreshing ? 'animate-spin' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Current Branch Highlight */}
      {currentBranch && (
        <div className="px-4 py-3 border-b border-white/5 bg-gradient-to-r from-cyan-500/5 to-purple-500/5">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span className="text-xs text-zinc-400">Current branch:</span>
            <code className="px-2 py-0.5 bg-cyan-500/10 text-cyan-400 rounded font-mono text-xs border border-cyan-500/30">
              {currentBranch}
            </code>
          </div>
        </div>
      )}

      {/* Branches List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {/* Local Branches */}
        {localBranches.length > 0 && (
          <div className="p-4 border-b border-white/5">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <GitBranch className="w-3 h-3" />
              Local Branches ({localBranches.length})
            </h4>
            <div className="space-y-1">
              {localBranches.map((branch) => (
                <button
                  key={branch.name}
                  onClick={() => handleBranchClick(branch.name)}
                  className={`w-full px-3 py-2 rounded-lg border transition-all text-left ${
                    branch.is_current
                      ? 'bg-cyan-500/10 border-cyan-500/30'
                      : selectedBranch === branch.name
                      ? 'bg-purple-500/10 border-purple-500/30'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {branch.is_current ? (
                      <Radio className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                    ) : (
                      <GitBranch className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                    )}
                    <span
                      className={`text-sm font-mono flex-1 truncate ${
                        branch.is_current ? 'text-cyan-400 font-semibold' : 'text-white'
                      }`}
                    >
                      {branch.name}
                    </span>
                    {branch.is_current && (
                      <span className="px-2 py-0.5 bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded text-xs font-medium">
                        Current
                      </span>
                    )}
                  </div>

                  {branch.last_commit && (
                    <div className="mt-2 ml-6 space-y-1">
                      <p className="text-xs text-zinc-400 line-clamp-1">
                        {branch.last_commit.message}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {branch.last_commit.author_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(branch.last_commit.date)}
                        </span>
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Remote Branches */}
        {remoteBranches.length > 0 && (
          <div className="p-4">
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <GitMerge className="w-3 h-3" />
              Remote Branches ({remoteBranches.length})
            </h4>
            <div className="space-y-1">
              {remoteBranches.map((branch) => (
                <button
                  key={branch.name}
                  onClick={() => handleBranchClick(branch.name)}
                  className={`w-full px-3 py-2 rounded-lg border transition-all text-left ${
                    selectedBranch === branch.name
                      ? 'bg-purple-500/10 border-purple-500/30'
                      : 'bg-white/5 border-white/10 hover:bg-white/10'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <GitMerge className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    <span className="text-sm font-mono flex-1 truncate text-white">
                      {branch.name}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-500/10 border border-purple-500/30 text-purple-400 rounded text-xs">
                      Remote
                    </span>
                  </div>

                  {branch.last_commit && (
                    <div className="mt-2 ml-6 space-y-1">
                      <p className="text-xs text-zinc-400 line-clamp-1">
                        {branch.last_commit.message}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <User className="w-3 h-3" />
                          {branch.last_commit.author_name}
                        </span>
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(branch.last_commit.date)}
                        </span>
                      </div>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {branches.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full p-4">
            <GitBranch className="w-12 h-12 text-zinc-600 mb-3" />
            <p className="text-zinc-500 text-sm">No branches found</p>
          </div>
        )}
      </div>
    </div>
  );
}
