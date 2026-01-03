// Project Detail page - Rich project view with tasks from linked circle

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft,
  FolderOpen,
  GitBranch,
  Users,
  Target,
  TrendingUp,
  Clock,
  Bot,
  BarChart3,
  Code2,
  AlertCircle,
  Inbox,
} from 'lucide-react';
import { projects, circles } from '../services/api';
import { LoadingSpinner, EmptyState } from '../components/ui';
import type { Task, TaskPriority, TaskStatus } from '../types';

// Types for sprint board display
interface SprintTask {
  id: string;
  title: string;
  status: 'todo' | 'in_progress' | 'done';
  assignee?: string;
  priority: TaskPriority;
}

interface Sprint {
  id: string;
  name: string;
  tasks: SprintTask[];
  goal: string;
}

// Map API task status to sprint board status
function mapTaskStatus(status: TaskStatus): 'todo' | 'in_progress' | 'done' {
  switch (status) {
    case 'completed':
      return 'done';
    case 'in_progress':
    case 'in_review':
    case 'review':
      return 'in_progress';
    default:
      return 'todo';
  }
}

// Convert API tasks to sprint tasks
function convertToSprintTasks(tasks: Task[]): SprintTask[] {
  return tasks.map(task => ({
    id: String(task.id),
    title: task.title,
    status: mapTaskStatus(task.status),
    assignee: task.assigned_agent_name ?? undefined,
    priority: task.priority,
  }));
}


// Sprint Board Component
function SprintBoard({ sprint }: { sprint: Sprint }) {
  const columns = [
    { id: 'todo', label: 'To Do', color: 'text-zinc-400' },
    { id: 'in_progress', label: 'In Progress', color: 'text-cyan-400' },
    { id: 'done', label: 'Done', color: 'text-emerald-400' },
  ];

  const priorityColors: Record<TaskPriority, string> = {
    critical: 'border-l-pink-500',
    high: 'border-l-red-500',
    medium: 'border-l-yellow-500',
    low: 'border-l-emerald-500',
  };

  return (
    <div className="grid grid-cols-3 gap-4">
      {columns.map((column) => {
        const tasks = sprint.tasks.filter((t) => t.status === column.id);

        return (
          <div key={column.id}>
            <div className="flex items-center justify-between mb-3">
              <h4 className={`font-medium ${column.color}`}>{column.label}</h4>
              <span className="text-xs text-zinc-500">{tasks.length} tasks</span>
            </div>
            <div className="space-y-2">
              {tasks.map((task) => (
                <div
                  key={task.id}
                  className={`p-3 glass-card rounded-lg border-l-2 ${priorityColors[task.priority]}`}
                >
                  <p className="text-sm text-zinc-200">{task.title}</p>
                  <div className="flex items-center justify-between mt-2">
                    {task.assignee ? (
                      <span className="text-xs text-zinc-500 flex items-center gap-1">
                        <Bot className="w-3 h-3" />
                        {task.assignee}
                      </span>
                    ) : (
                      <span className="text-xs text-zinc-600">Unassigned</span>
                    )}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${
                      task.priority === 'critical' ? 'bg-pink-500/20 text-pink-400' :
                      task.priority === 'high' ? 'bg-red-500/20 text-red-400' :
                      task.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-emerald-500/20 text-emerald-400'
                    }`}>{task.priority}</span>
                  </div>
                </div>
              ))}
              {tasks.length === 0 && (
                <div className="p-4 border-2 border-dashed border-zinc-700 rounded-lg text-center">
                  <p className="text-xs text-zinc-600">No tasks</p>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const [activeTab, setActiveTab] = useState<'overview' | 'sprint'>('overview');

  // Fetch project data
  const { data: project, isLoading: projectLoading, error: projectError } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projects.get(Number(projectId)),
    enabled: !!projectId,
  });

  // Fetch linked circles for the project
  const { data: linkedCircles } = useQuery({
    queryKey: ['project-circles', projectId],
    queryFn: () => projects.listCircles(Number(projectId)),
    enabled: !!projectId,
  });

  // Get primary circle name
  const primaryCircle = linkedCircles?.circles?.find(c => c.is_primary);
  const primaryCircleName = primaryCircle?.circle_name ?? null;

  // Fetch tasks from the primary circle
  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['circle-tasks', primaryCircleName],
    queryFn: () => circles.getTasks(primaryCircleName!),
    enabled: !!primaryCircleName,
  });

  // Convert tasks to sprint format
  const sprintTasks = tasksData?.tasks ? convertToSprintTasks(tasksData.tasks) : [];

  const sprint: Sprint = {
    id: 'current',
    name: project?.name ? `${project.name} Tasks` : 'Current Tasks',
    tasks: sprintTasks,
    goal: project?.description || 'Project tasks from linked circle',
  };

  // Calculate stats from real tasks
  const totalTasks = sprint.tasks.length;
  const completedTasks = sprint.tasks.filter((t) => t.status === 'done').length;
  const inProgressTasks = sprint.tasks.filter((t) => t.status === 'in_progress').length;
  const todoTasks = sprint.tasks.filter((t) => t.status === 'todo').length;
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // Loading state
  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  // Error state
  if (projectError || !project) {
    return (
      <div className="space-y-6">
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Projects
        </Link>
        <EmptyState
          icon={<AlertCircle className="w-12 h-12" />}
          title="Project not found"
          description="The project you're looking for doesn't exist or has been deleted."
          action={
            <Link to="/projects" className="btn-primary">
              View all projects
            </Link>
          }
        />
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    active: 'bg-emerald-500/20 text-emerald-400',
    planning: 'bg-purple-500/20 text-purple-400',
    on_hold: 'bg-amber-500/20 text-amber-400',
    completed: 'bg-cyan-500/20 text-cyan-400',
    archived: 'bg-zinc-500/20 text-zinc-400',
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link
            to="/projects"
            className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              <FolderOpen className="w-6 h-6 text-purple-400" />
              {project.name}
            </h1>
            <p className="text-zinc-400 mt-1">{project.description || 'No description'}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <a
            href={`/workspace/${projectId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 glass-card rounded-xl text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <Code2 className="w-4 h-4" />
            <span className="text-sm font-medium">Open Workspace</span>
          </a>
          <span className={`px-3 py-1 text-xs rounded-full ${statusColors[project.status] || statusColors.active}`}>
            {project.status}
          </span>
          {project.branch && (
            <span className="flex items-center gap-1 text-sm text-zinc-400">
              <GitBranch className="w-4 h-4" />
              {project.branch}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-800 pb-2">
        {[
          { id: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
          { id: 'sprint', label: 'Task Board', icon: <Target className="w-4 h-4" /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as 'overview' | 'sprint')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors ${
              activeTab === tab.id
                ? 'bg-purple-500/20 text-purple-400'
                : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Task Progress */}
          <div className="lg:col-span-2 glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="font-semibold text-white">Task Progress</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  {primaryCircleName ? 'Tasks from linked circle' : 'No circle linked'}
                </p>
              </div>
              {tasksLoading && <LoadingSpinner size="sm" />}
            </div>

            {totalTasks === 0 ? (
              <EmptyState
                icon={<Inbox className="w-10 h-10" />}
                title="No tasks yet"
                description={primaryCircleName
                  ? "Create tasks in the linked circle to see them here."
                  : "Link a circle to this project to manage tasks."
                }
              />
            ) : (
              <>
                {/* Progress Bar */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-zinc-400">Overall Progress</span>
                    <span className="text-sm font-medium text-white">{progressPercent}%</span>
                  </div>
                  <div className="h-3 bg-zinc-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-500 to-cyan-500 transition-all duration-500"
                      style={{ width: `${progressPercent}%` }}
                    />
                  </div>
                </div>

                {/* Stats Row */}
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center p-3 rounded-xl bg-zinc-800/50">
                    <p className="text-2xl font-bold text-white">{totalTasks}</p>
                    <p className="text-xs text-zinc-500">Total</p>
                  </div>
                  <div className="text-center p-3 rounded-xl bg-emerald-500/10">
                    <p className="text-2xl font-bold text-emerald-400">{completedTasks}</p>
                    <p className="text-xs text-zinc-500">Done</p>
                  </div>
                  <div className="text-center p-3 rounded-xl bg-cyan-500/10">
                    <p className="text-2xl font-bold text-cyan-400">{inProgressTasks}</p>
                    <p className="text-xs text-zinc-500">In Progress</p>
                  </div>
                  <div className="text-center p-3 rounded-xl bg-zinc-700/50">
                    <p className="text-2xl font-bold text-zinc-400">{todoTasks}</p>
                    <p className="text-xs text-zinc-500">To Do</p>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="glass-card rounded-2xl p-6">
              <h3 className="font-semibold text-white mb-4">Project Info</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <Target className="w-4 h-4 text-purple-400" />
                    Total Tasks
                  </span>
                  <span className="font-medium text-white">{totalTasks}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    Completion Rate
                  </span>
                  <span className="font-medium text-emerald-400">{progressPercent}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-400 flex items-center gap-2">
                    <Users className="w-4 h-4 text-cyan-400" />
                    Linked Circles
                  </span>
                  <span className="font-medium text-white">{linkedCircles?.total || 0}</span>
                </div>
                {project.path && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-zinc-400 flex items-center gap-2">
                      <FolderOpen className="w-4 h-4 text-amber-400" />
                      Path
                    </span>
                    <span className="font-medium text-white text-xs truncate max-w-32" title={project.path}>
                      {project.path.split('/').pop()}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Linked Circles */}
            {linkedCircles && linkedCircles.circles.length > 0 && (
              <div className="glass-card rounded-2xl p-6">
                <h3 className="font-semibold text-white mb-4">Linked Circles</h3>
                <div className="space-y-3">
                  {linkedCircles.circles.map((circle) => (
                    <Link
                      key={circle.circle_id}
                      to={`/circles`}
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-zinc-800/50 transition-colors"
                    >
                      <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                        <Users className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white">{circle.circle_name}</p>
                        <p className="text-xs text-zinc-500">
                          {circle.is_primary ? 'Primary' : 'Secondary'}
                        </p>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'sprint' && (
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="font-semibold text-white">Task Board</h2>
              <p className="text-sm text-zinc-500">
                {primaryCircleName ? 'Tasks from linked circle' : 'No circle linked to this project'}
              </p>
            </div>
            {totalTasks > 0 && (
              <div className="flex items-center gap-4 text-sm text-zinc-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {inProgressTasks} in progress
                </span>
                <span className="flex items-center gap-1">
                  <Target className="w-4 h-4" />
                  {totalTasks} total
                </span>
              </div>
            )}
          </div>

          {totalTasks === 0 ? (
            <EmptyState
              icon={<Inbox className="w-12 h-12" />}
              title="No tasks"
              description={primaryCircleName
                ? "Create tasks in the linked circle to see them here."
                : "Link a circle to this project to manage tasks."
              }
            />
          ) : (
            <SprintBoard sprint={sprint} />
          )}
        </div>
      )}
    </div>
  );
}

export default ProjectDetail;
