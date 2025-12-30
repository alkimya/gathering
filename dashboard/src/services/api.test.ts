import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { agents, circles, health, conversations, memories, backgroundTasks, goals, settings, projects, pipelines } from './api';

// Mock fetch globally
const mockFetch = vi.fn();
(globalThis as unknown as { fetch: typeof fetch }).fetch = mockFetch;

describe('API Service', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('health', () => {
    it('checks health status', async () => {
      const mockResponse = {
        status: 'healthy',
        version: '0.15.0',
        uptime_seconds: 3600,
        agents_count: 2,
        circles_count: 1,
        active_tasks: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await health.check();

      expect(mockFetch).toHaveBeenCalledWith('/api/health', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('agents', () => {
    it('lists all agents', async () => {
      const mockResponse = {
        agents: [
          { id: 1, name: 'Sophie', role: 'Developer', status: 'idle' },
          { id: 2, name: 'Olivia', role: 'Reviewer', status: 'idle' },
        ],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await agents.list();

      expect(mockFetch).toHaveBeenCalledWith('/api/agents-db', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.agents).toHaveLength(2);
      expect(result.agents[0].name).toBe('Sophie');
    });

    it('gets agent by id', async () => {
      const mockAgent = {
        id: 1,
        name: 'Sophie',
        role: 'Developer',
        status: 'idle',
        persona: { name: 'Sophie', role: 'Developer' },
        config: { provider: 'anthropic', model: 'claude-3' },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockAgent),
      });

      const result = await agents.get(1);

      expect(mockFetch).toHaveBeenCalledWith('/api/agents-db/1', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.name).toBe('Sophie');
    });

    it('sends chat message to agent', async () => {
      const mockResponse = {
        content: 'Hello! How can I help?',
        agent_id: 1,
        agent_name: 'Sophie',
        model: 'claude-3',
        duration_ms: 1500,
        tool_calls: [],
        tool_results: [],
        tokens_used: 150,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await agents.chat(1, 'Hello');

      expect(mockFetch).toHaveBeenCalledWith('/api/agents/1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: 'Hello',
          include_memories: true,
          allow_tools: true,
        }),
      });
      expect(result.content).toBe('Hello! How can I help?');
    });

    it('handles error responses', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ detail: 'Agent not found' }),
      });

      await expect(agents.get(999)).rejects.toThrow('Agent not found');
    });
  });

  describe('circles', () => {
    it('lists all circles', async () => {
      const mockResponse = {
        circles: [
          { id: 'circle-1', name: 'dev-team', status: 'running', agent_count: 2 },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await circles.list();

      expect(result.circles).toHaveLength(1);
      expect(result.circles[0].name).toBe('dev-team');
    });

    it('creates a circle', async () => {
      const mockCircle = {
        id: 'circle-2',
        name: 'new-circle',
        status: 'stopped',
        require_review: true,
        auto_route: false,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockCircle),
      });

      const result = await circles.create({
        name: 'new-circle',
        require_review: true,
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/circles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'new-circle', require_review: true }),
      });
      expect(result.name).toBe('new-circle');
    });

    it('starts a circle', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'started' }),
      });

      const result = await circles.start('dev-team');

      expect(mockFetch).toHaveBeenCalledWith('/api/circles/dev-team/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.status).toBe('started');
    });
  });

  describe('conversations', () => {
    it('lists conversations', async () => {
      const mockResponse = {
        conversations: [
          { id: 'conv-1', topic: 'Code Review', status: 'active' },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await conversations.list();

      expect(result.conversations).toHaveLength(1);
      expect(result.conversations[0].topic).toBe('Code Review');
    });

    it('creates a conversation', async () => {
      const mockConversation = {
        id: 'conv-2',
        topic: 'Architecture Discussion',
        status: 'pending',
        participant_names: ['Sophie', 'Olivia'],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockConversation),
      });

      const result = await conversations.create({
        topic: 'Architecture Discussion',
        agent_ids: [1, 2],
        max_turns: 10,
      });

      expect(result.topic).toBe('Architecture Discussion');
    });
  });

  describe('memories', () => {
    it('stores a memory for an agent', async () => {
      const mockMemory = {
        id: 1,
        key: 'test-key',
        value: 'Important information',
        memory_type: 'fact',
        importance: 0.8,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockMemory),
      });

      const result = await memories.remember(1, {
        content: 'Important information',
        memory_type: 'fact',
      });

      expect(result.value).toBe('Important information');
    });

    it('recalls memories for an agent', async () => {
      const mockRecall = {
        query: 'project setup',
        memories: [
          { id: 1, key: 'setup', value: 'Use npm install', memory_type: 'fact', importance: 0.7 },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockRecall),
      });

      const result = await memories.recall(1, 'project setup');

      expect(result.memories).toHaveLength(1);
      expect(result.query).toBe('project setup');
    });
  });

  describe('goals', () => {
    it('lists goals', async () => {
      const mockResponse = {
        goals: [
          { id: 1, title: 'Implement feature', status: 'active', progress_percent: 50 },
        ],
        total: 1,
        counts: { active: 1, pending: 0, completed: 0 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await goals.list();

      expect(result.goals).toHaveLength(1);
      expect(result.goals[0].title).toBe('Implement feature');
    });

    it('creates a goal', async () => {
      const mockGoal = {
        id: 1,
        title: 'New Feature',
        description: 'Implement a new feature',
        status: 'pending',
        priority: 'high',
        progress_percent: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockGoal),
      });

      const result = await goals.create({
        agent_id: 1,
        title: 'New Feature',
        description: 'Implement a new feature',
        priority: 'high',
      });

      expect(result.title).toBe('New Feature');
      expect(result.status).toBe('pending');
    });

    it('updates goal progress', async () => {
      const mockGoal = {
        id: 1,
        title: 'Feature',
        progress_percent: 75,
        status: 'active',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockGoal),
      });

      const result = await goals.updateProgress(1, 75, 'Almost done');

      // URLSearchParams uses + for spaces, not %20
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/goals/1/progress?percent=75&message=Almost+done',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }
      );
      expect(result.progress_percent).toBe(75);
    });
  });

  describe('backgroundTasks', () => {
    it('lists background tasks', async () => {
      const mockResponse = {
        tasks: [
          { id: 1, goal: 'Run tests', status: 'running', progress_percent: 50 },
        ],
        total: 1,
        counts: { running: 1, pending: 0, completed: 0 },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await backgroundTasks.list();

      expect(result.tasks).toHaveLength(1);
      expect(result.tasks[0].status).toBe('running');
    });

    it('creates a background task', async () => {
      const mockTask = {
        id: 1,
        agent_id: 1,
        goal: 'Analyze codebase',
        status: 'pending',
        progress_percent: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTask),
      });

      const result = await backgroundTasks.create({
        agent_id: 1,
        goal: 'Analyze codebase',
        max_steps: 100,
      });

      expect(result.goal).toBe('Analyze codebase');
    });
  });

  describe('projects', () => {
    it('lists projects', async () => {
      const mockResponse = {
        projects: [
          { id: 1, name: 'gathering', path: '/home/user/gathering', status: 'active' },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await projects.list();

      expect(result.projects).toHaveLength(1);
      expect(result.projects[0].name).toBe('gathering');
    });

    it('creates a project', async () => {
      const mockProject = {
        id: 1,
        name: 'new-project',
        path: '/home/user/new-project',
        status: 'active',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockProject),
      });

      const result = await projects.create({
        name: 'new-project',
        path: '/home/user/new-project',
        auto_detect: true,
      });

      expect(result.name).toBe('new-project');
    });

    it('browses folders', async () => {
      const mockResponse = {
        current_path: '/home/user',
        parent_path: '/home',
        entries: [
          { name: 'projects', path: '/home/user/projects', is_dir: true, is_project: false },
        ],
        can_create_project: true,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await projects.browseFolders('/home/user');

      expect(result.entries).toHaveLength(1);
      expect(result.current_path).toBe('/home/user');
    });
  });

  describe('settings', () => {
    it('gets all settings', async () => {
      const mockSettings = {
        providers: {
          anthropic: { is_configured: true },
          openai: { is_configured: false },
        },
        database: { host: 'localhost', port: 5432, is_connected: true },
        application: { environment: 'development', debug: true, log_level: 'INFO' },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSettings),
      });

      const result = await settings.get();

      expect(result.providers.anthropic.is_configured).toBe(true);
      expect(result.database.is_connected).toBe(true);
    });

    it('tests a provider', async () => {
      const mockResult = {
        success: true,
        message: 'Connected successfully',
        models: ['claude-3-sonnet', 'claude-3-opus'],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResult),
      });

      const result = await settings.testProvider('anthropic');

      expect(result.success).toBe(true);
      expect(result.models).toContain('claude-3-sonnet');
    });
  });

  describe('pipelines', () => {
    it('lists all pipelines', async () => {
      const mockResponse = {
        pipelines: [
          {
            id: 1,
            name: 'Code Review Workflow',
            status: 'active',
            run_count: 25,
            success_count: 23,
            error_count: 2,
          },
        ],
        total: 1,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await pipelines.list();

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.pipelines).toHaveLength(1);
      expect(result.pipelines[0].name).toBe('Code Review Workflow');
    });

    it('lists pipelines by status', async () => {
      const mockResponse = { pipelines: [], total: 0 };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await pipelines.list('active');

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines?status=active', {
        headers: { 'Content-Type': 'application/json' },
      });
    });

    it('gets a pipeline by id', async () => {
      const mockPipeline = {
        id: 1,
        name: 'Code Review Workflow',
        status: 'active',
        nodes: [
          { id: 'n1', type: 'trigger', name: 'PR Created', config: {}, position: { x: 50, y: 100 } },
        ],
        edges: [],
        run_count: 25,
        success_count: 23,
        error_count: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPipeline),
      });

      const result = await pipelines.get(1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.name).toBe('Code Review Workflow');
      expect(result.nodes).toHaveLength(1);
    });

    it('creates a pipeline', async () => {
      const mockPipeline = {
        id: 1,
        name: 'New Pipeline',
        status: 'draft',
        nodes: [],
        edges: [],
        run_count: 0,
        success_count: 0,
        error_count: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPipeline),
      });

      const result = await pipelines.create({
        name: 'New Pipeline',
        description: 'A test pipeline',
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'New Pipeline',
          description: 'A test pipeline',
        }),
      });
      expect(result.name).toBe('New Pipeline');
      expect(result.status).toBe('draft');
    });

    it('updates a pipeline', async () => {
      const mockPipeline = {
        id: 1,
        name: 'Updated Pipeline',
        status: 'active',
        nodes: [
          { id: 'n1', type: 'trigger', name: 'Webhook', config: {}, position: { x: 50, y: 100 } },
        ],
        edges: [],
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPipeline),
      });

      const result = await pipelines.update(1, {
        name: 'Updated Pipeline',
        nodes: [
          { id: 'n1', type: 'trigger', name: 'Webhook', config: {}, position: { x: 50, y: 100 } },
        ],
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: expect.any(String),
      });
      expect(result.name).toBe('Updated Pipeline');
    });

    it('deletes a pipeline', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      await pipelines.delete(1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
    });

    it('toggles pipeline status', async () => {
      const mockPipeline = {
        id: 1,
        name: 'Test Pipeline',
        status: 'paused',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockPipeline),
      });

      const result = await pipelines.toggle(1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.status).toBe('paused');
    });

    it('runs a pipeline', async () => {
      const mockRun = {
        id: 1,
        pipeline_id: 1,
        status: 'pending',
        logs: [],
        duration_seconds: 0,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockRun),
      });

      const result = await pipelines.run(1, { pr_number: 123 });

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trigger_data: { pr_number: 123 } }),
      });
      expect(result.status).toBe('pending');
    });

    it('gets pipeline runs', async () => {
      const mockResponse = {
        runs: [
          { id: 1, pipeline_id: 1, status: 'completed', duration_seconds: 120 },
          { id: 2, pipeline_id: 1, status: 'running', duration_seconds: 30 },
        ],
        total: 2,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await pipelines.getRuns(1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/runs?limit=20&offset=0', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.runs).toHaveLength(2);
    });

    it('gets pipeline runs with filters', async () => {
      const mockResponse = { runs: [], total: 0 };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await pipelines.getRuns(1, 'completed', 10, 5);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/runs?status=completed&limit=10&offset=5', {
        headers: { 'Content-Type': 'application/json' },
      });
    });

    it('gets a specific run', async () => {
      const mockRun = {
        id: 1,
        pipeline_id: 1,
        status: 'completed',
        logs: [
          { timestamp: '2024-01-15T10:00:00Z', node_id: 'n1', message: 'Started', level: 'info' },
        ],
        duration_seconds: 120,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockRun),
      });

      const result = await pipelines.getRun(1, 1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/runs/1', {
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.logs).toHaveLength(1);
    });

    it('cancels a run', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'cancelled' }),
      });

      const result = await pipelines.cancelRun(1, 1);

      expect(mockFetch).toHaveBeenCalledWith('/api/pipelines/1/runs/1/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      expect(result.status).toBe('cancelled');
    });
  });

  describe('error handling', () => {
    it('handles network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(health.check()).rejects.toThrow('Network error');
    });

    it('handles 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 204,
      });

      const result = await agents.delete(1);

      expect(result).toBeUndefined();
    });

    it('handles unknown error format', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });

      await expect(health.check()).rejects.toThrow('Unknown error');
    });
  });
});
