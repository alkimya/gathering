// Projects page - Manage projects and assign agents

import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  FolderOpen,
  FolderPlus,
  ChevronRight,
  ChevronUp,
  RefreshCw,
  Trash2,
  GitBranch,
  Terminal,
  Code2,
  Settings2,
  AlertCircle,
  Eye,
  EyeOff,
  Folder,
  FileCode,
  Home,
  Loader2,
  X,
  Users,
  BarChart3,
} from 'lucide-react';
import { projects } from '../services/api';
import type { Project, FolderEntry, ProjectCreate } from '../types';

// Project Card
function ProjectCard({
  project,
  onRefresh,
  onDelete,
  onView,
}: {
  project: Project;
  onRefresh: () => void;
  onDelete: () => void;
  onView: () => void;
}) {
  const [showDetails, setShowDetails] = useState(false);

  const statusColors = {
    active: 'bg-emerald-500/20 text-emerald-400',
    archived: 'bg-zinc-500/20 text-zinc-400',
    on_hold: 'bg-amber-500/20 text-amber-400',
  };

  return (
    <div className="glass-card rounded-xl p-6 hover:bg-zinc-800/50 transition-colors">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <FolderOpen className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">{project.display_name || project.name}</h3>
            <p className="text-sm text-zinc-400 font-mono truncate max-w-xs">{project.path}</p>
          </div>
        </div>
        <span className={`px-2 py-1 text-xs rounded-full ${statusColors[project.status]}`}>
          {project.status}
        </span>
      </div>

      {project.description && (
        <p className="text-sm text-zinc-400 mb-4">{project.description}</p>
      )}

      {/* Quick Stats */}
      <div className="flex flex-wrap gap-2 mb-4">
        {project.branch && (
          <span className="flex items-center gap-1 px-2 py-1 bg-zinc-800 rounded text-xs text-zinc-300">
            <GitBranch className="w-3 h-3" />
            {project.branch}
          </span>
        )}
        {project.python_version && (
          <span className="flex items-center gap-1 px-2 py-1 bg-blue-500/20 rounded text-xs text-blue-400">
            <Code2 className="w-3 h-3" />
            Python {project.python_version}
          </span>
        )}
        {project.languages.length > 0 && (
          project.languages.map(lang => (
            <span key={lang} className="px-2 py-1 bg-zinc-700 rounded text-xs text-zinc-300">
              {lang}
            </span>
          ))
        )}
        <span className="flex items-center gap-1 px-2 py-1 bg-purple-500/20 rounded text-xs text-purple-400">
          <Users className="w-3 h-3" />
          {project.circle_count} circles
        </span>
      </div>

      {/* Expandable Details */}
      {showDetails && (
        <div className="border-t border-zinc-700 pt-4 mt-4 space-y-3">
          {Object.keys(project.tools).length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1">Tools</h4>
              <div className="flex flex-wrap gap-1">
                {Object.entries(project.tools).map(([key, value]) => (
                  <span key={key} className="px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-300">
                    {key}: {String(value)}
                  </span>
                ))}
              </div>
            </div>
          )}
          {Object.keys(project.commands).length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1">Commands</h4>
              <div className="space-y-1">
                {Object.entries(project.commands).map(([name, cmd]) => (
                  <div key={name} className="flex items-center gap-2 text-xs">
                    <Terminal className="w-3 h-3 text-zinc-500" />
                    <span className="text-purple-400">{name}:</span>
                    <code className="text-zinc-400 font-mono">{cmd}</code>
                  </div>
                ))}
              </div>
            </div>
          )}
          {project.notes.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-zinc-400 mb-1">Notes</h4>
              <ul className="list-disc list-inside text-xs text-zinc-400">
                {project.notes.map((note, i) => (
                  <li key={i}>{note}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-zinc-700">
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-sm text-zinc-400 hover:text-white transition-colors flex items-center gap-1"
        >
          {showDetails ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          {showDetails ? 'Hide' : 'Details'}
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded-lg transition-colors"
            title="Refresh project settings"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <Link
            to={`/workspace/${project.id}`}
            className="p-2 text-zinc-400 hover:text-cyan-400 hover:bg-zinc-700 rounded-lg transition-colors"
            title="Open Workspace"
          >
            <Code2 className="w-4 h-4" />
          </Link>
          <Link
            to={`/projects/${project.id}`}
            className="p-2 text-zinc-400 hover:text-purple-400 hover:bg-zinc-700 rounded-lg transition-colors"
            title="Project Dashboard"
          >
            <BarChart3 className="w-4 h-4" />
          </Link>
          <button
            onClick={onView}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings2 className="w-4 h-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-2 text-zinc-400 hover:text-red-400 hover:bg-zinc-700 rounded-lg transition-colors"
            title="Delete project"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// Folder Browser Modal
function FolderBrowser({
  isOpen,
  onClose,
  onSelect,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (path: string, name: string) => void;
}) {
  const [currentPath, setCurrentPath] = useState<string | undefined>(undefined);
  const [showHidden, setShowHidden] = useState(false);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [projectName, setProjectName] = useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['folders', currentPath, showHidden],
    queryFn: () => projects.browseFolders(currentPath, showHidden),
    enabled: isOpen,
  });

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
    setSelectedPath(null);
  };

  const handleGoUp = () => {
    if (data?.parent_path) {
      setCurrentPath(data.parent_path);
      setSelectedPath(null);
    }
  };

  const handleGoHome = () => {
    setCurrentPath(undefined);
    setSelectedPath(null);
  };

  const handleSelectFolder = (entry: FolderEntry) => {
    if (entry.is_dir) {
      if (entry.is_project) {
        setSelectedPath(entry.path);
        setProjectName(entry.name);
      } else {
        handleNavigate(entry.path);
      }
    }
  };

  const handleConfirm = () => {
    if (selectedPath && projectName) {
      onSelect(selectedPath, projectName);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-zinc-900 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-700">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <FolderOpen className="w-5 h-5 text-purple-400" />
            Browse Folders
          </h2>
          <button onClick={onClose} className="p-1 text-zinc-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <div className="flex items-center gap-2 p-4 border-b border-zinc-700">
          <button
            onClick={handleGoHome}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded-lg transition-colors"
            title="Home"
          >
            <Home className="w-4 h-4" />
          </button>
          <button
            onClick={handleGoUp}
            disabled={!data?.parent_path}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-700 rounded-lg transition-colors disabled:opacity-50"
            title="Go up"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
          <div className="flex-1 px-3 py-2 bg-zinc-800 rounded-lg text-sm text-zinc-300 font-mono truncate">
            {data?.current_path || '~'}
          </div>
          <label className="flex items-center gap-2 text-sm text-zinc-400">
            <input
              type="checkbox"
              checked={showHidden}
              onChange={(e) => setShowHidden(e.target.checked)}
              className="rounded"
            />
            Show hidden
          </label>
        </div>

        {/* Folder List */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-2" />
              <p className="text-red-400">{(error as Error).message}</p>
            </div>
          ) : (
            <div className="space-y-1">
              {data?.entries.map((entry) => (
                <button
                  key={entry.path}
                  onClick={() => handleSelectFolder(entry)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                    selectedPath === entry.path
                      ? 'bg-purple-500/20 border border-purple-500/30'
                      : 'hover:bg-zinc-800'
                  }`}
                >
                  {entry.is_dir ? (
                    entry.is_project ? (
                      <FolderOpen className="w-5 h-5 text-purple-400" />
                    ) : (
                      <Folder className="w-5 h-5 text-zinc-400" />
                    )
                  ) : (
                    <FileCode className="w-5 h-5 text-zinc-500" />
                  )}
                  <span className="flex-1 text-sm text-zinc-200">{entry.name}</span>
                  {entry.is_project && (
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">
                      Project
                    </span>
                  )}
                  {entry.is_dir && !entry.is_project && (
                    <ChevronRight className="w-4 h-4 text-zinc-500" />
                  )}
                </button>
              ))}
              {data?.entries.length === 0 && (
                <p className="text-center text-zinc-500 py-8">No folders found</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-zinc-700 space-y-3">
          {selectedPath && (
            <div className="space-y-2">
              <label className="text-sm text-zinc-400">Project Name</label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="Enter project name"
                className="w-full px-3 py-2 input-glass rounded-lg text-sm"
              />
            </div>
          )}
          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={!selectedPath || !projectName}
              className="px-4 py-2 btn-gradient rounded-xl disabled:opacity-50"
            >
              Add Project
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main Projects Page
export function Projects() {
  const queryClient = useQueryClient();
  const [showBrowser, setShowBrowser] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data, isLoading, error } = useQuery({
    queryKey: ['projects', statusFilter],
    queryFn: () => projects.list(statusFilter as 'active' | 'archived' | 'on_hold' | undefined),
  });

  const createMutation = useMutation({
    mutationFn: (data: ProjectCreate) => projects.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setShowBrowser(false);
    },
  });

  const refreshMutation = useMutation({
    mutationFn: (id: number) => projects.refresh(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => projects.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const handleAddProject = (path: string, name: string) => {
    createMutation.mutate({ path, name, auto_detect: true });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-xl p-8 text-center">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-4" />
        <p className="text-red-400">{(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Projects</h1>
          <p className="text-zinc-400 mt-1">
            Manage projects and assign agents to work on them
          </p>
        </div>
        <button
          onClick={() => setShowBrowser(true)}
          className="flex items-center gap-2 px-4 py-2 btn-gradient rounded-xl"
        >
          <FolderPlus className="w-4 h-4" />
          Add Project
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={statusFilter || ''}
          onChange={(e) => setStatusFilter(e.target.value || undefined)}
          className="px-3 py-2 input-glass rounded-lg text-sm"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
          <option value="on_hold">On Hold</option>
        </select>
        <span className="text-sm text-zinc-400">
          {data?.total || 0} project{(data?.total || 0) !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Projects Grid */}
      {data?.projects.length === 0 ? (
        <div className="glass-card rounded-xl p-12 text-center">
          <FolderOpen className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-zinc-300 mb-2">No projects yet</h3>
          <p className="text-sm text-zinc-500 mb-6">
            Add a project folder to let agents work on it
          </p>
          <button
            onClick={() => setShowBrowser(true)}
            className="inline-flex items-center gap-2 px-4 py-2 btn-gradient rounded-xl"
          >
            <FolderPlus className="w-4 h-4" />
            Browse Folders
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data?.projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onRefresh={() => refreshMutation.mutate(project.id)}
              onDelete={() => {
                if (confirm(`Delete project "${project.name}"?`)) {
                  deleteMutation.mutate(project.id);
                }
              }}
              onView={() => {
                // TODO: Open project detail modal
              }}
            />
          ))}
        </div>
      )}

      {/* Folder Browser Modal */}
      <FolderBrowser
        isOpen={showBrowser}
        onClose={() => setShowBrowser(false)}
        onSelect={handleAddProject}
      />

      {/* Loading overlay for mutations */}
      {(createMutation.isPending || refreshMutation.isPending || deleteMutation.isPending) && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-40">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      )}
    </div>
  );
}

export default Projects;
