// Main layout component with Web3 dark theme and reorganized navigation

import { Link, Outlet, useLocation } from 'react-router-dom';
import {
  Bot,
  Circle,
  MessageSquare,
  Activity,
  Settings,
  Menu,
  X,
  Brain,
  Sparkles,
  Zap,
  Cpu,
  PlayCircle,
  Calendar,
  Target,
  FolderOpen,
  LayoutDashboard,
  Kanban,
  Bell,
  ChevronDown,
  ChevronRight,
  Workflow,
  BarChart3,
  Users,
  Wrench,
  GitBranch,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

interface NavGroup {
  id: string;
  label: string;
  icon: React.ReactNode;
  items: NavItem[];
  defaultOpen?: boolean;
}

// Navigation organisée par groupes logiques
const navGroups: NavGroup[] = [
  {
    id: 'overview',
    label: 'Overview',
    icon: <LayoutDashboard className="w-4 h-4" />,
    defaultOpen: true,
    items: [
      { path: '/', label: 'Dashboard', icon: <Activity className="w-5 h-5" /> },
      { path: '/activity', label: 'Activity Feed', icon: <Bell className="w-5 h-5" /> },
    ],
  },
  {
    id: 'work',
    label: 'Work',
    icon: <Workflow className="w-4 h-4" />,
    defaultOpen: true,
    items: [
      { path: '/projects', label: 'Projects', icon: <FolderOpen className="w-5 h-5" /> },
      { path: '/calendar', label: 'Calendar', icon: <Calendar className="w-5 h-5" /> },
      { path: '/board', label: 'Board', icon: <Kanban className="w-5 h-5" /> },
      { path: '/goals', label: 'Goals', icon: <Target className="w-5 h-5" /> },
      { path: '/pipelines', label: 'Pipelines', icon: <GitBranch className="w-5 h-5" /> },
      { path: '/tasks', label: 'Background Tasks', icon: <PlayCircle className="w-5 h-5" /> },
      { path: '/schedules', label: 'Schedules', icon: <PlayCircle className="w-5 h-5" /> },
    ],
  },
  {
    id: 'agents',
    label: 'Agents & Teams',
    icon: <Users className="w-4 h-4" />,
    defaultOpen: true,
    items: [
      { path: '/agents', label: 'Agents', icon: <Bot className="w-5 h-5" /> },
      { path: '/circles', label: 'Circles', icon: <Circle className="w-5 h-5" /> },
      { path: '/conversations', label: 'Conversations', icon: <MessageSquare className="w-5 h-5" /> },
    ],
  },
  {
    id: 'intelligence',
    label: 'Intelligence',
    icon: <Brain className="w-4 h-4" />,
    defaultOpen: false,
    items: [
      { path: '/knowledge', label: 'Knowledge Base', icon: <Brain className="w-5 h-5" /> },
      { path: '/models', label: 'Models', icon: <Cpu className="w-5 h-5" /> },
    ],
  },
  {
    id: 'system',
    label: 'System',
    icon: <Wrench className="w-4 h-4" />,
    defaultOpen: false,
    items: [
      { path: '/monitoring', label: 'Monitoring', icon: <BarChart3 className="w-5 h-5" /> },
      { path: '/settings', label: 'Settings', icon: <Settings className="w-5 h-5" /> },
    ],
  },
];

export function Layout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    navGroups.forEach(group => {
      initial[group.id] = group.defaultOpen ?? false;
    });
    return initial;
  });
  // WebSocket connection for real-time updates
  // Note: Toast notifications for WS status are disabled to avoid spam in dev
  // The status indicator in the sidebar shows connection state
  const { isConnected } = useWebSocket({
    topics: ['agents', 'circles', 'tasks'],
    autoReconnect: true,
    reconnectInterval: 10000,
    maxReconnectAttempts: 3,
  });

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => ({
      ...prev,
      [groupId]: !prev[groupId],
    }));
  };

  // Vérifier si un groupe contient l'item actif
  const isGroupActive = (group: NavGroup) => {
    return group.items.some(item =>
      location.pathname === item.path ||
      (item.path !== '/' && location.pathname.startsWith(item.path))
    );
  };

  return (
    <div className="flex h-screen bg-mesh overflow-hidden">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 modal-overlay lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed inset-y-0 left-0 z-30 w-72 sidebar
          transform transition-transform duration-300 ease-out
          lg:translate-x-0 lg:static lg:inset-auto
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-20 px-6 border-b border-white/5">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center glow-purple">
                <span className="text-xl font-bold text-white">䷬</span>
              </div>
              <Sparkles className="w-3 h-3 text-purple-400 absolute -top-1 -right-1 animate-pulse" />
            </div>
            <div>
              <span className="text-xl font-bold gradient-text">
                GatheRing
              </span>
              <div className="flex items-center gap-1 text-xs text-zinc-500">
                <Zap className="w-3 h-3 text-purple-400" />
                <span>v0.15.0</span>
              </div>
            </div>
          </Link>
          <button
            className="lg:hidden text-zinc-400 hover:text-white transition-colors"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Navigation avec groupes */}
        <nav className="p-4 space-y-2 overflow-y-auto h-[calc(100vh-180px)]">
          {navGroups.map((group) => {
            const isExpanded = expandedGroups[group.id];
            const hasActiveItem = isGroupActive(group);

            return (
              <div key={group.id} className="space-y-1">
                {/* Group header */}
                <button
                  onClick={() => toggleGroup(group.id)}
                  className={`
                    w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider
                    rounded-lg transition-colors cursor-pointer
                    ${hasActiveItem ? 'text-purple-400 bg-purple-500/10' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}
                  `}
                >
                  {group.icon}
                  <span className="flex-1 text-left">{group.label}</span>
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                {/* Group items */}
                {isExpanded && (
                  <div className="ml-2 space-y-1 border-l border-white/5 pl-2">
                    {group.items.map((item) => {
                      const isActive = location.pathname === item.path ||
                        (item.path !== '/' && location.pathname.startsWith(item.path));

                      return (
                        <Link
                          key={item.path}
                          to={item.path}
                          className={`
                            sidebar-link flex items-center gap-3 px-4 py-2.5
                            ${isActive ? 'active' : ''}
                          `}
                          onClick={() => setSidebarOpen(false)}
                        >
                          <span className={isActive ? 'text-purple-400' : ''}>{item.icon}</span>
                          <span className="font-medium text-sm">{item.label}</span>
                          {isActive && (
                            <div className="ml-auto w-1.5 h-1.5 rounded-full bg-purple-400 pulse-dot" />
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/5 bg-[#11111b]">
          {/* Status indicator */}
          <div className="px-4 py-3 glass-card rounded-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-zinc-500'} pulse-dot`} />
                <span className="text-zinc-400">System {isConnected ? 'Online' : 'Offline'}</span>
              </div>
              <div className="flex items-center gap-1.5">
                {isConnected ? (
                  <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <WifiOff className="w-3.5 h-3.5 text-zinc-500" />
                )}
                <span className={`text-xs ${isConnected ? 'text-emerald-400' : 'text-zinc-500'}`}>
                  {isConnected ? 'Live' : 'Offline'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-20 glass-card border-b border-white/5 flex items-center px-6 sticky top-0 z-10">
          <button
            className="lg:hidden text-zinc-400 hover:text-white transition-colors mr-4"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="w-6 h-6" />
          </button>

          {/* Search bar */}
          <div className="hidden md:flex flex-1 max-w-md">
            <div className="relative w-full">
              <input
                type="text"
                placeholder="Search agents, projects, tasks..."
                className="w-full px-4 py-2.5 pl-10 input-glass rounded-xl text-sm"
              />
              <svg
                className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </div>

          <div className="flex-1" />

          {/* Right side */}
          <div className="flex items-center gap-4">
            {/* Activity indicator - links to activity feed */}
            <Link
              to="/activity"
              className="relative p-2 text-zinc-400 hover:text-white transition-colors"
            >
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-pink-500 rounded-full animate-pulse" />
            </Link>

            {/* Connection status */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 glass-card rounded-full">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-xs text-zinc-400">Connected</span>
            </div>

            {/* Profile */}
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center cursor-pointer hover:scale-105 transition-transform">
              <span className="text-sm font-bold text-white">A</span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
