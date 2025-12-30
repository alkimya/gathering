// Main application with routing and providers

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

import { Layout } from './components/Layout';
import { ToastProvider } from './components/Toast';
import { Dashboard } from './pages/Dashboard';
import { Agents } from './pages/Agents';
import { Models } from './pages/Models';
import { Circles } from './pages/Circles';
import { Conversations } from './pages/Conversations';
import { Knowledge } from './pages/Knowledge';
import { BackgroundTasks } from './pages/BackgroundTasks';
import { ScheduledActions } from './pages/ScheduledActions';
import { Goals } from './pages/Goals';
import { Settings } from './pages/Settings';
import { Projects } from './pages/Projects';
import { Activity } from './pages/Activity';
import { Board } from './pages/Board';
import { Monitoring } from './pages/Monitoring';
import { Pipelines } from './pages/Pipelines';
import { AgentDashboard } from './pages/AgentDashboard';
import { Calendar } from './pages/Calendar';
import { ProjectDetail } from './pages/ProjectDetail';
import { Workspace } from './pages/Workspace';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            {/* Workspace route outside Layout for full-screen experience */}
            <Route path="/workspace/:projectId" element={<Workspace />} />

            {/* All other routes use Layout */}
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="activity" element={<Activity />} />
              <Route path="board" element={<Board />} />
              <Route path="agents" element={<Agents />} />
              <Route path="agents/:agentId" element={<AgentDashboard />} />
              <Route path="models" element={<Models />} />
              <Route path="circles" element={<Circles />} />
              <Route path="conversations" element={<Conversations />} />
              <Route path="knowledge" element={<Knowledge />} />
              <Route path="tasks" element={<BackgroundTasks />} />
              <Route path="schedules" element={<ScheduledActions />} />
              <Route path="calendar" element={<Calendar />} />
              <Route path="pipelines" element={<Pipelines />} />
              <Route path="goals" element={<Goals />} />
              <Route path="projects" element={<Projects />} />
              <Route path="projects/:projectId" element={<ProjectDetail />} />
              <Route path="settings" element={<Settings />} />
              <Route path="monitoring" element={<Monitoring />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <ReactQueryDevtools initialIsOpen={false} />
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
