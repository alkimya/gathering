/**
 * File Explorer Component - Web3 Dark Theme
 * Displays project file tree with git status indicators
 */

import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, File, Folder, FolderOpen, Loader2 } from 'lucide-react';
import api from '../../services/api';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  git_status?: string;
  children?: FileNode[];
}

interface FileExplorerProps {
  projectId: number;
  onFileSelect: (filePath: string) => void;
  selectedFile: string | null;
}

export function FileExplorer({ projectId, onFileSelect, selectedFile }: FileExplorerProps) {
  const [fileTree, setFileTree] = useState<FileNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set(['/']));

  useEffect(() => {
    loadFileTree();
  }, [projectId]);

  const loadFileTree = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await api.get(`/workspace/${projectId}/files`, {
        params: { include_git_status: true },
      });

      setFileTree(response.data as FileNode);
      setExpandedDirs(new Set(['/']));
    } catch (err: any) {
      console.error('Failed to load file tree:', err);
      setError(err.message || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const toggleDirectory = (path: string) => {
    const newExpanded = new Set(expandedDirs);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedDirs(newExpanded);
  };

  const renderGitStatus = (status?: string) => {
    if (!status) return null;

    const statusConfig: Record<string, { label: string; color: string; glow: string }> = {
      M: { label: 'M', color: 'text-amber-400', glow: 'bg-amber-500/20' },
      A: { label: 'A', color: 'text-green-400', glow: 'bg-green-500/20' },
      D: { label: 'D', color: 'text-red-400', glow: 'bg-red-500/20' },
      '??': { label: '?', color: 'text-cyan-400', glow: 'bg-cyan-500/20' },
      R: { label: 'R', color: 'text-purple-400', glow: 'bg-purple-500/20' },
    };

    const config = statusConfig[status] || { label: status, color: 'text-zinc-400', glow: 'bg-zinc-500/20' };

    return (
      <span className={`ml-2 px-1.5 py-0.5 ${config.glow} ${config.color} text-[10px] font-mono font-bold rounded border border-${config.color.split('-')[1]}-500/30`}>
        {config.label}
      </span>
    );
  };

  const getFileIcon = (node: FileNode) => {
    if (node.type === 'directory') {
      const isExpanded = expandedDirs.has(node.path);
      return isExpanded ? (
        <FolderOpen className="w-4 h-4 text-cyan-400" />
      ) : (
        <Folder className="w-4 h-4 text-cyan-500" />
      );
    }

    // File type specific icons by extension
    const ext = node.name.split('.').pop()?.toLowerCase();
    const iconColors: Record<string, string> = {
      ts: 'text-blue-400',
      tsx: 'text-blue-400',
      js: 'text-yellow-400',
      jsx: 'text-yellow-400',
      py: 'text-green-400',
      json: 'text-amber-400',
      md: 'text-purple-400',
      css: 'text-pink-400',
      html: 'text-orange-400',
    };

    const color = iconColors[ext || ''] || 'text-zinc-400';
    return <File className={`w-4 h-4 ${color}`} />;
  };

  const renderNode = (node: FileNode, depth: number = 0): React.ReactNode => {
    const isDirectory = node.type === 'directory';
    const isExpanded = expandedDirs.has(node.path);
    const isSelected = selectedFile === node.path;

    return (
      <div key={node.path}>
        <div
          className={`flex items-center py-1.5 px-2 cursor-pointer transition-all group ${
            isSelected
              ? 'bg-purple-500/20 border-l-2 border-purple-500'
              : 'hover:bg-white/5 border-l-2 border-transparent'
          }`}
          style={{ paddingLeft: `${depth * 16 + 8}px` }}
          onClick={() => {
            if (isDirectory) {
              toggleDirectory(node.path);
            } else {
              onFileSelect(node.path);
            }
          }}
        >
          {/* Chevron for directories */}
          {isDirectory && (
            <span className="mr-1 text-zinc-500">
              {isExpanded ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronRight className="w-3 h-3" />
              )}
            </span>
          )}

          {/* Icon */}
          <span className="mr-2">{getFileIcon(node)}</span>

          {/* Name */}
          <span className={`text-sm flex-1 ${isSelected ? 'text-white font-medium' : 'text-zinc-300 group-hover:text-white'}`}>
            {node.name}
          </span>

          {/* Git status */}
          {renderGitStatus(node.git_status)}
        </div>

        {/* Children */}
        {isDirectory && isExpanded && node.children && (
          <div>{node.children.map((child) => renderNode(child, depth + 1))}</div>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-purple-500 animate-spin mb-3" />
        <p className="text-zinc-400 text-sm">Loading files...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-4">
        <div className="text-red-400 text-4xl mb-3">⚠️</div>
        <p className="text-red-400 text-sm text-center mb-3">{error}</p>
        <button
          onClick={loadFileTree}
          className="px-4 py-2 bg-white/5 hover:bg-white/10 text-white text-sm rounded-lg border border-white/10 transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!fileTree) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-zinc-500 text-sm">No files found</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/5">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Folder className="w-4 h-4 text-cyan-400" />
          Files
        </h3>
      </div>

      {/* File tree */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {fileTree.children && fileTree.children.length > 0 ? (
          <div className="py-2">
            {fileTree.children.map((node) => renderNode(node, 0))}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-zinc-500 text-sm">Empty directory</p>
          </div>
        )}
      </div>
    </div>
  );
}
