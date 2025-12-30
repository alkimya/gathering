// Kanban Board page - Visual task management

import { useState, useEffect } from 'react';
import {
  Kanban,
  Plus,
  Filter,
  MoreHorizontal,
  Bot,
  User,
  Clock,
  CheckCircle,
  Circle,
  ArrowRight,
  ChevronDown,
  GripVertical,
} from 'lucide-react';

// Types
interface Task {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'assigned' | 'in_progress' | 'in_review' | 'completed' | 'failed';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee?: {
    id: string;
    name: string;
    type: 'agent' | 'user';
  };
  project_id?: string;
  project_name?: string;
  circle_id?: string;
  created_at: string;
  due_date?: string;
  tags?: string[];
}

type ColumnId = 'backlog' | 'in_progress' | 'in_review' | 'done';

interface Column {
  id: ColumnId;
  title: string;
  statuses: Task['status'][];
  color: string;
  bgColor: string;
}

const columns: Column[] = [
  {
    id: 'backlog',
    title: 'Backlog',
    statuses: ['pending', 'assigned'],
    color: 'text-zinc-400',
    bgColor: 'bg-zinc-500/10',
  },
  {
    id: 'in_progress',
    title: 'In Progress',
    statuses: ['in_progress'],
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/10',
  },
  {
    id: 'in_review',
    title: 'In Review',
    statuses: ['in_review'],
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
  },
  {
    id: 'done',
    title: 'Done',
    statuses: ['completed', 'failed'],
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
  },
];

const priorityConfig = {
  critical: { color: 'text-pink-400', bg: 'bg-pink-500/20', label: 'Critical' },
  high: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'High' },
  medium: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Medium' },
  low: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Low' },
};

// Données de démo
const generateDemoTasks = (): Task[] => [
  {
    id: '1',
    title: 'Implement Activity Feed',
    description: 'Create real-time activity feed with WebSocket',
    status: 'in_progress',
    priority: 'high',
    assignee: { id: 'a1', name: 'Sophie', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    tags: ['frontend', 'websocket'],
  },
  {
    id: '2',
    title: 'Review API changes',
    description: 'Review the new skill endpoints',
    status: 'in_review',
    priority: 'high',
    assignee: { id: 'a2', name: 'Olivia', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    tags: ['api', 'review'],
  },
  {
    id: '3',
    title: 'Add unit tests for skills',
    description: 'Write comprehensive tests for new skills',
    status: 'pending',
    priority: 'medium',
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    tags: ['testing'],
  },
  {
    id: '4',
    title: 'Update documentation',
    description: 'Document new dashboard features',
    status: 'assigned',
    priority: 'low',
    assignee: { id: 'a3', name: 'Claude', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    tags: ['docs'],
  },
  {
    id: '5',
    title: 'Fix authentication bug',
    description: 'Token refresh not working correctly',
    status: 'in_progress',
    priority: 'critical',
    assignee: { id: 'a1', name: 'Sophie', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    due_date: new Date(Date.now() + 86400000).toISOString(),
    tags: ['bug', 'auth'],
  },
  {
    id: '6',
    title: 'Implement PDF export',
    status: 'completed',
    priority: 'medium',
    assignee: { id: 'a1', name: 'Sophie', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date(Date.now() - 86400000).toISOString(),
    tags: ['feature'],
  },
  {
    id: '7',
    title: 'Add email notifications',
    status: 'completed',
    priority: 'medium',
    assignee: { id: 'a2', name: 'Olivia', type: 'agent' },
    project_name: 'GatheRing',
    created_at: new Date(Date.now() - 172800000).toISOString(),
    tags: ['feature', 'notifications'],
  },
  {
    id: '8',
    title: 'Optimize database queries',
    status: 'pending',
    priority: 'high',
    project_name: 'GatheRing',
    created_at: new Date().toISOString(),
    tags: ['performance', 'database'],
  },
];

function TaskCard({
  task,
  onMove,
}: {
  task: Task;
  onMove: (taskId: string, newStatus: Task['status']) => void;
}) {
  const [showMenu, setShowMenu] = useState(false);
  const priority = priorityConfig[task.priority];

  return (
    <div
      className="glass-card rounded-xl p-4 cursor-grab active:cursor-grabbing hover:bg-white/5 transition-all group"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('taskId', task.id);
        e.dataTransfer.setData('currentStatus', task.status);
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
          <GripVertical className="w-4 h-4 text-zinc-600" />
        </div>
        <h3 className="flex-1 font-medium text-zinc-200 text-sm">{task.title}</h3>
        <div className="relative">
          <button
            onClick={() => setShowMenu(!showMenu)}
            className="p-1 text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>
          {showMenu && (
            <div className="absolute right-0 top-6 z-10 w-40 glass-card rounded-xl shadow-xl border border-white/10 py-2">
              <button
                onClick={() => {
                  onMove(task.id, 'in_progress');
                  setShowMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
              >
                <ArrowRight className="w-4 h-4" />
                Start
              </button>
              <button
                onClick={() => {
                  onMove(task.id, 'in_review');
                  setShowMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
              >
                <ArrowRight className="w-4 h-4" />
                Submit for Review
              </button>
              <button
                onClick={() => {
                  onMove(task.id, 'completed');
                  setShowMenu(false);
                }}
                className="w-full px-4 py-2 text-left text-sm text-zinc-300 hover:bg-white/5 flex items-center gap-2"
              >
                <CheckCircle className="w-4 h-4" />
                Complete
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Description */}
      {task.description && (
        <p className="text-xs text-zinc-500 mt-2 line-clamp-2">{task.description}</p>
      )}

      {/* Tags */}
      {task.tags && task.tags.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3">
          {task.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs rounded-full bg-zinc-700/50 text-zinc-400"
            >
              {tag}
            </span>
          ))}
          {task.tags.length > 3 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-zinc-700/50 text-zinc-500">
              +{task.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
        {/* Priority */}
        <span className={`px-2 py-0.5 text-xs rounded-full ${priority.bg} ${priority.color}`}>
          {priority.label}
        </span>

        {/* Assignee */}
        {task.assignee ? (
          <div className="flex items-center gap-1 text-xs text-zinc-400">
            {task.assignee.type === 'agent' ? (
              <Bot className="w-3 h-3" />
            ) : (
              <User className="w-3 h-3" />
            )}
            <span>{task.assignee.name}</span>
          </div>
        ) : (
          <span className="text-xs text-zinc-600">Unassigned</span>
        )}
      </div>

      {/* Due date warning */}
      {task.due_date && new Date(task.due_date) < new Date(Date.now() + 86400000) && (
        <div className="flex items-center gap-1 mt-2 text-xs text-amber-400">
          <Clock className="w-3 h-3" />
          <span>Due soon</span>
        </div>
      )}
    </div>
  );
}

function KanbanColumn({
  column,
  tasks,
  onMove,
  onDrop,
}: {
  column: Column;
  tasks: Task[];
  onMove: (taskId: string, newStatus: Task['status']) => void;
  onDrop: (taskId: string, columnId: ColumnId) => void;
}) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const taskId = e.dataTransfer.getData('taskId');
    onDrop(taskId, column.id);
  };

  return (
    <div
      className={`flex flex-col min-w-[300px] max-w-[300px] rounded-2xl transition-colors ${
        isDragOver ? 'bg-purple-500/10 ring-2 ring-purple-500/30' : ''
      }`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Column Header */}
      <div className={`flex items-center gap-3 p-4 rounded-t-2xl ${column.bgColor}`}>
        <Circle className={`w-3 h-3 ${column.color}`} />
        <h2 className={`font-semibold ${column.color}`}>{column.title}</h2>
        <span className="ml-auto px-2 py-0.5 text-xs rounded-full bg-zinc-700/50 text-zinc-400">
          {tasks.length}
        </span>
      </div>

      {/* Tasks */}
      <div className="flex-1 p-2 space-y-3 min-h-[200px]">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onMove={onMove} />
        ))}

        {tasks.length === 0 && (
          <div className="flex items-center justify-center h-32 border-2 border-dashed border-zinc-700/50 rounded-xl">
            <p className="text-sm text-zinc-600">Drop tasks here</p>
          </div>
        )}
      </div>
    </div>
  );
}

export function Board() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filterProject, setFilterProject] = useState<string>('all');
  const [filterAssignee, setFilterAssignee] = useState<string>('all');
  const [filterPriority, setFilterPriority] = useState<string>('all');

  // Charger les tâches (démo pour l'instant)
  useEffect(() => {
    setTasks(generateDemoTasks());
  }, []);

  // Mapper les colonnes aux statuts
  const columnToStatus: Record<ColumnId, Task['status']> = {
    backlog: 'pending',
    in_progress: 'in_progress',
    in_review: 'in_review',
    done: 'completed',
  };

  // Déplacer une tâche
  const handleMove = (taskId: string, newStatus: Task['status']) => {
    setTasks((prev) =>
      prev.map((task) =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  // Drop sur une colonne
  const handleDrop = (taskId: string, columnId: ColumnId) => {
    const newStatus = columnToStatus[columnId];
    handleMove(taskId, newStatus);
  };

  // Filtrer les tâches
  const filteredTasks = tasks.filter((task) => {
    if (filterProject !== 'all' && task.project_name !== filterProject) return false;
    if (filterAssignee !== 'all' && task.assignee?.name !== filterAssignee) return false;
    if (filterPriority !== 'all' && task.priority !== filterPriority) return false;
    return true;
  });

  // Grouper par colonne
  const getColumnTasks = (column: Column) =>
    filteredTasks.filter((task) => column.statuses.includes(task.status));

  // Extraire les valeurs uniques pour les filtres
  const projects = [...new Set(tasks.map((t) => t.project_name).filter(Boolean))];
  const assignees = [...new Set(tasks.map((t) => t.assignee?.name).filter(Boolean))];

  // Stats
  const stats = {
    total: filteredTasks.length,
    inProgress: filteredTasks.filter((t) => t.status === 'in_progress').length,
    completed: filteredTasks.filter((t) => t.status === 'completed').length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <Kanban className="w-8 h-8 text-purple-400" />
            Board
          </h1>
          <p className="text-zinc-400 mt-1">
            {stats.total} tâches • {stats.inProgress} en cours • {stats.completed} complétées
          </p>
        </div>

        <button className="btn-gradient px-4 py-2 rounded-xl flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Task
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <Filter className="w-4 h-4 text-zinc-500" />

        {/* Project filter */}
        <div className="relative">
          <select
            value={filterProject}
            onChange={(e) => setFilterProject(e.target.value)}
            className="appearance-none px-4 py-2 pr-8 rounded-xl bg-zinc-800/50 text-sm text-zinc-300 border border-zinc-700 focus:border-purple-500 focus:outline-none"
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
        </div>

        {/* Assignee filter */}
        <div className="relative">
          <select
            value={filterAssignee}
            onChange={(e) => setFilterAssignee(e.target.value)}
            className="appearance-none px-4 py-2 pr-8 rounded-xl bg-zinc-800/50 text-sm text-zinc-300 border border-zinc-700 focus:border-purple-500 focus:outline-none"
          >
            <option value="all">All Assignees</option>
            {assignees.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
        </div>

        {/* Priority filter */}
        <div className="relative">
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value)}
            className="appearance-none px-4 py-2 pr-8 rounded-xl bg-zinc-800/50 text-sm text-zinc-300 border border-zinc-700 focus:border-purple-500 focus:outline-none"
          >
            <option value="all">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
        </div>

        {/* Clear filters */}
        {(filterProject !== 'all' || filterAssignee !== 'all' || filterPriority !== 'all') && (
          <button
            onClick={() => {
              setFilterProject('all');
              setFilterAssignee('all');
              setFilterPriority('all');
            }}
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Kanban Board */}
      <div className="flex gap-4 overflow-x-auto pb-6">
        {columns.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            tasks={getColumnTasks(column)}
            onMove={handleMove}
            onDrop={handleDrop}
          />
        ))}
      </div>
    </div>
  );
}

export default Board;
