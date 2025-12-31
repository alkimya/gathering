/**
 * Git View Component
 *
 * Comprehensive Git interface with tabbed navigation:
 * - Timeline: Commit history with details
 * - Status: Working directory and staging area
 * - Branches: Multi-branch visualization
 */

import { useState } from 'react';
import { GitBranch, FileText, History, X, Maximize2, Minimize2 } from 'lucide-react';
import { GitTimeline } from './GitTimeline';
import { GitCommitDetail } from './GitCommitDetail';
import { GitStagingArea } from './GitStagingArea';
import { GitBranchManager } from './GitBranchManager';

interface GitViewProps {
  projectId: number;
  onClose?: () => void;
  onToggleMaximize?: () => void;
  isMaximized?: boolean;
}

type TabType = 'timeline' | 'status' | 'branches';

export function GitView({ projectId, onClose, onToggleMaximize, isMaximized = false }: GitViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('timeline');
  const [selectedCommit, setSelectedCommit] = useState<string | null>(null);
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  const tabs = [
    { id: 'timeline' as TabType, label: 'Timeline', icon: History },
    { id: 'status' as TabType, label: 'Status', icon: FileText },
    { id: 'branches' as TabType, label: 'Branches', icon: GitBranch },
  ];

  const handleCommitSelect = (commitHash: string) => {
    setSelectedCommit(commitHash);
  };

  const handleBranchSelect = (branchName: string) => {
    setSelectedBranch(branchName);
    // Could filter timeline by branch here
  };

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5 bg-gradient-to-r from-purple-500/5 to-cyan-500/5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center glow-purple">
              <GitBranch className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Git Manager</h2>
              <p className="text-xs text-zinc-500">
                Version control & collaboration
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onToggleMaximize && (
              <button
                onClick={onToggleMaximize}
                className="p-1.5 hover:bg-white/10 rounded transition-colors"
                title={isMaximized ? "Restore" : "Maximize"}
              >
                {isMaximized ? (
                  <Minimize2 className="w-4 h-4 text-zinc-400" />
                ) : (
                  <Maximize2 className="w-4 h-4 text-zinc-400" />
                )}
              </button>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-white/10 rounded transition-colors"
                title="Close Git view"
              >
                <X className="w-4 h-4 text-zinc-400" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-white/5 bg-white/[0.02]">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded flex items-center gap-2 text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                  : 'text-zinc-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'timeline' && (
          <div className="h-full flex">
            {/* Timeline List */}
            <div className={`${selectedCommit ? 'w-1/2' : 'w-full'} border-r border-white/5`}>
              <GitTimeline
                projectId={projectId}
                onCommitSelect={handleCommitSelect}
                selectedCommit={selectedCommit}
              />
            </div>

            {/* Commit Detail Panel */}
            {selectedCommit && (
              <div className="w-1/2">
                <GitCommitDetail
                  projectId={projectId}
                  commitHash={selectedCommit}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'status' && (
          <GitStagingArea projectId={projectId} />
        )}

        {activeTab === 'branches' && (
          <div className="h-full flex">
            {/* Branches List */}
            <div className={`${selectedBranch ? 'w-1/2' : 'w-full'} border-r border-white/5`}>
              <GitBranchManager
                projectId={projectId}
                onBranchSelect={handleBranchSelect}
              />
            </div>

            {/* Branch Timeline (optional - could show commits for selected branch) */}
            {selectedBranch && (
              <div className="w-1/2 p-4">
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
                  <h4 className="text-sm font-semibold text-white mb-2">
                    Branch: {selectedBranch}
                  </h4>
                  <p className="text-xs text-zinc-500">
                    Timeline for branch commits coming soon...
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
