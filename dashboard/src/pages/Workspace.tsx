/**
 * Workspace Page - IDE-like development environment for projects
 * Web3 Dark Theme Integration
 */

import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FolderTree, Activity, Terminal, Maximize2, Minimize2, GitBranch } from 'lucide-react';
import { FileExplorer } from '../components/workspace/FileExplorer';
import { CodeEditor } from '../components/workspace/CodeEditor';
import { GitTimeline } from '../components/workspace/GitTimeline';
import { ActivityFeed } from '../components/workspace/ActivityFeed';
import api from '../services/api';

interface WorkspaceInfo {
  type: string;
  path: string;
  name: string;
  file_count: number;
  size_mb: number;
  is_git_repo: boolean;
  capabilities: string[];
}

export function Workspace() {
  const { projectId } = useParams<{ projectId: string }>();
  const [workspaceInfo, setWorkspaceInfo] = useState<WorkspaceInfo | null>(null);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Layout state
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [showActivityFeed, setShowActivityFeed] = useState(true);
  const [showTerminal, setShowTerminal] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    loadWorkspaceInfo();
  }, [projectId]);

  const loadWorkspaceInfo = async () => {
    if (!projectId) return;

    try {
      setLoading(true);
      const response = await api.get(`/workspace/${projectId}/info`);
      setWorkspaceInfo(response.data);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load workspace info:', err);
      setError(err.response?.data?.detail || 'Failed to load workspace');
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (filePath: string) => {
    setSelectedFile(filePath);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-mesh">
        <div className="text-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-500 mx-auto mb-6 glow-purple"></div>
            <div className="absolute inset-0 rounded-full h-16 w-16 border-t-2 border-cyan-500 mx-auto animate-spin" style={{ animationDuration: '1.5s', animationDirection: 'reverse' }}></div>
          </div>
          <p className="text-zinc-300 text-lg">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-mesh">
        <div className="text-center glass-card p-8 rounded-xl max-w-md">
          <div className="text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-3">
            Workspace Error
          </h2>
          <p className="text-zinc-400 mb-6">{error}</p>
          <button
            onClick={loadWorkspaceInfo}
            className="btn-gradient px-6 py-3 rounded-lg"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-mesh">
      {/* Header */}
      <div className="glass-card border-b border-white/5 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to={`/projects/${projectId}`}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title="Back to Project"
          >
            <ArrowLeft className="w-5 h-5 text-zinc-400 group-hover:text-purple-400 transition-colors" />
          </Link>

          <div className="h-8 w-px bg-white/10"></div>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center glow-purple">
              <FolderTree className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">
                {workspaceInfo?.name}
              </h1>
              <p className="text-xs text-zinc-500">
                {workspaceInfo?.file_count?.toLocaleString()} files • {workspaceInfo?.size_mb?.toFixed(1)} MB
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-purple-500/10 text-purple-400 text-xs font-medium rounded-lg border border-purple-500/20">
              {workspaceInfo?.type}
            </span>
            {workspaceInfo?.is_git_repo && (
              <span className="px-3 py-1 bg-cyan-500/10 text-cyan-400 text-xs font-medium rounded-lg border border-cyan-500/20 flex items-center gap-1">
                <GitBranch className="w-3 h-3" />
                Git
              </span>
            )}
          </div>
        </div>

        {/* View toggles */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowFileExplorer(!showFileExplorer)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showFileExplorer
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <FolderTree className="w-4 h-4" />
            Files
          </button>
          <button
            onClick={() => setShowActivityFeed(!showActivityFeed)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showActivityFeed
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <Activity className="w-4 h-4" />
            Activity
          </button>
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className={`flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-all ${
              showTerminal
                ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                : 'bg-white/5 text-zinc-400 hover:bg-white/10 border border-white/5'
            }`}
          >
            <Terminal className="w-4 h-4" />
            Terminal
          </button>

          <div className="h-8 w-px bg-white/10"></div>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 hover:bg-white/5 rounded-lg transition-colors group"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400 transition-colors" />
            ) : (
              <Maximize2 className="w-4 h-4 text-zinc-400 group-hover:text-purple-400 transition-colors" />
            )}
          </button>
        </div>
      </div>

      {/* Main workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer */}
        {showFileExplorer && (
          <div className="w-80 glass-card border-r border-white/5 flex flex-col">
            <FileExplorer
              projectId={parseInt(projectId || '0')}
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
            />
          </div>
        )}

        {/* Editor */}
        <div className="flex-1 flex flex-col min-w-0">
          <CodeEditor
            projectId={parseInt(projectId || '0')}
            filePath={selectedFile}
          />
        </div>

        {/* Right Panel: Activity Feed + Git Timeline */}
        {showActivityFeed && (
          <div className="w-96 glass-card border-l border-white/5 flex flex-col">
            <div className="flex-1 overflow-hidden flex flex-col">
              <ActivityFeed projectId={parseInt(projectId || '0')} />
            </div>
            {workspaceInfo?.is_git_repo && (
              <div className="flex-1 border-t border-white/5 overflow-hidden flex flex-col">
                <GitTimeline projectId={parseInt(projectId || '0')} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Terminal */}
      {showTerminal && (
        <div className="h-64 glass-card border-t border-white/5">
          <div className="h-full flex items-center justify-center text-zinc-500">
            <Terminal className="w-8 h-8 mr-3" />
            <span>Terminal integration coming soon...</span>
          </div>
        </div>
      )}
    </div>
  );
}
