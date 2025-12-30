// API Service for GatheRing Dashboard

import type {
  Agent,
  AgentDetail,
  Circle,
  CircleDetail,
  Task,
  Conversation,
  ConversationDetail,
  ChatRequest,
  ChatResponse,
  HealthResponse,
  ChatMessage,
  CircleMetrics,
  TaskPriority,
  Memory,
  MemoryCreate,
  RecallResponse,
  Knowledge,
  KnowledgeCreate,
  KnowledgeSearchResponse,
  MemoryStats,
  MemoryType,
  KnowledgeCategory,
  Provider,
  Model,
  Persona,
  PersonaCreate,
  BackgroundTask,
  BackgroundTaskCreate,
  BackgroundTaskStep,
  BackgroundTaskStatus,
  ScheduledAction,
  ScheduledActionCreate,
  ScheduledActionRun,
  ScheduledActionStatus,
  Goal,
  GoalCreate,
  GoalUpdate,
  GoalStatus,
  GoalActivity,
  AllSettings,
  ProviderSettings,
  ApplicationSettings,
  ProviderTestResult,
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectStatus,
  FolderBrowseResponse,
  ProjectContext,
  Pipeline,
  PipelineCreate,
  PipelineUpdate,
  PipelineStatus,
  PipelineRun,
  PipelineRunStatus,
} from '../types';

const API_BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// Health
export const health = {
  check: () => request<HealthResponse>('/health'),
};

// Agents (using database endpoints)
export const agents = {
  list: () => request<{ agents: Agent[]; total: number }>('/agents-db'),

  get: (id: number) => request<AgentDetail>(`/agents-db/${id}`),

  create: (data: { persona: Partial<Agent>; config?: Partial<Agent> }) =>
    request<AgentDetail>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: { persona?: Partial<Agent>; config?: Partial<Agent> }) =>
    request<AgentDetail>(`/agents/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/agents/${id}`, { method: 'DELETE' }),

  chat: (id: number, message: string) =>
    request<ChatResponse>(`/agents/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message, include_memories: true, allow_tools: true } as ChatRequest),
    }),

  getHistory: (id: number) =>
    request<{ messages: ChatMessage[] }>(`/agents/${id}/history`),

  status: (id: number) =>
    request<Record<string, unknown>>(`/agents/${id}/status`),

  remember: (id: number, content: string, memory_type = 'learning') =>
    request<{ id: number }>(`/agents/${id}/memories`, {
      method: 'POST',
      body: JSON.stringify({ content, memory_type }),
    }),

  recall: (id: number, query: string, limit = 5) =>
    request<{ memories: string[]; query: string }>(`/agents/${id}/memories/recall`, {
      method: 'POST',
      body: JSON.stringify({ query, limit }),
    }),
};

// Circles
export const circles = {
  list: () => request<{ circles: Circle[]; total: number }>('/circles'),

  get: (name: string) => request<CircleDetail>(`/circles/${name}`),

  create: (data: { name: string; require_review?: boolean; auto_route?: boolean }) =>
    request<CircleDetail>('/circles', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (name: string) =>
    request<void>(`/circles/${name}`, { method: 'DELETE' }),

  start: (name: string) =>
    request<{ status: string }>(`/circles/${name}/start`, { method: 'POST' }),

  stop: (name: string) =>
    request<{ status: string }>(`/circles/${name}/stop`, { method: 'POST' }),

  addAgent: (name: string, params: {
    agent_id: number;
    agent_name: string;
    provider?: string;
    model?: string;
    competencies?: string;
    can_review?: string;
  }) => {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) searchParams.set(key, String(value));
    });
    return request<{ status: string }>(`/circles/${name}/agents?${searchParams}`, {
      method: 'POST',
    });
  },

  removeAgent: (name: string, agentId: number) =>
    request<{ status: string }>(`/circles/${name}/agents/${agentId}`, {
      method: 'DELETE',
    }),

  listTasks: (name: string, status?: string) => {
    const path = status ? `/circles/${name}/tasks?status_filter=${status}` : `/circles/${name}/tasks`;
    return request<{ tasks: Task[]; total: number }>(path);
  },

  getTasks: (name: string) => request<{ tasks: Task[]; total: number }>(`/circles/${name}/tasks`),

  createTask: (name: string, data: {
    title: string;
    description?: string;
    required_competencies?: string[];
    priority?: TaskPriority;
  }) =>
    request<Task>(`/circles/${name}/tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getTask: (name: string, taskId: number) =>
    request<Task>(`/circles/${name}/tasks/${taskId}`),

  submitTask: (name: string, taskId: number, result: string, files_modified: string[] = []) =>
    request<Task>(`/circles/${name}/tasks/${taskId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ result, files_modified }),
    }),

  approveTask: (name: string, taskId: number, reviewerId: number, comments = '') => {
    const params = new URLSearchParams({ reviewer_id: String(reviewerId), comments });
    return request<{ status: string }>(`/circles/${name}/tasks/${taskId}/approve?${params}`, {
      method: 'POST',
    });
  },

  rejectTask: (name: string, taskId: number, reviewerId: number, reason: string) => {
    const params = new URLSearchParams({ reviewer_id: String(reviewerId), reason });
    return request<{ status: string }>(`/circles/${name}/tasks/${taskId}/reject?${params}`, {
      method: 'POST',
    });
  },

  getConflicts: (name: string) =>
    request<{ conflicts: unknown[]; total: number }>(`/circles/${name}/conflicts`),

  getMetrics: (name: string) =>
    request<CircleMetrics>(`/circles/${name}/metrics`),
};

// Conversations
export const conversations = {
  list: () => request<{ conversations: Conversation[]; total: number }>('/conversations'),

  get: (id: string) => request<ConversationDetail>(`/conversations/${id}`),

  create: (data: {
    topic: string;
    agent_ids: number[];
    max_turns?: number;
    initial_prompt?: string;
    turn_strategy?: string;
  }, circleName?: string) => {
    const path = circleName ? `/conversations?circle_name=${circleName}` : '/conversations';
    return request<ConversationDetail>(path, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  start: (id: string) =>
    request<ConversationDetail>(`/conversations/${id}/start`, { method: 'POST' }),

  cancel: (id: string) =>
    request<{ status: string }>(`/conversations/${id}/cancel`, { method: 'POST' }),

  delete: (id: string) =>
    request<void>(`/conversations/${id}`, { method: 'DELETE' }),

  getTranscript: (id: string) =>
    request<{ conversation_id: string; topic: string; transcript: string }>(`/conversations/${id}/transcript`),

  getMessages: (id: string) =>
    request<{ messages: { agent_id: number; agent_name: string; content: string; timestamp: string }[] }>(`/conversations/${id}/messages`),

  advance: (id: string, prompt?: string) =>
    request<ConversationDetail>(`/conversations/${id}/advance`, {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),

  quick: (circleName: string, data: {
    topic: string;
    agent_ids: number[];
    max_turns?: number;
    initial_prompt?: string;
  }) =>
    request<ConversationDetail>(`/conversations/quick?circle_name=${circleName}`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Memories (RAG)
export const memories = {
  // Agent memories
  remember: (agentId: number, data: MemoryCreate) =>
    request<Memory>(`/memories/agents/${agentId}/remember`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  recall: (agentId: number, query: string, options?: {
    memory_type?: MemoryType;
    tags?: string[];
    limit?: number;
    threshold?: number;
  }) =>
    request<RecallResponse>(`/memories/agents/${agentId}/recall`, {
      method: 'POST',
      body: JSON.stringify({ query, ...options }),
    }),

  forget: (agentId: number, memoryId: number) =>
    request<{ status: string; memory_id: number }>(`/memories/agents/${agentId}/memories/${memoryId}`, {
      method: 'DELETE',
    }),

  stats: (agentId: number) =>
    request<MemoryStats>(`/memories/agents/${agentId}/stats`),

  rememberBatch: (agentId: number, memories: MemoryCreate[]) =>
    request<{ created: number[]; total: number }>(`/memories/agents/${agentId}/remember/batch`, {
      method: 'POST',
      body: JSON.stringify({ memories }),
    }),

  // Knowledge base
  addKnowledge: (data: KnowledgeCreate, authorAgentId?: number) => {
    const path = authorAgentId
      ? `/memories/knowledge?author_agent_id=${authorAgentId}`
      : '/memories/knowledge';
    return request<Knowledge>(path, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  searchKnowledge: (query: string, options?: {
    project_id?: number;
    circle_id?: number;
    category?: KnowledgeCategory;
    include_global?: boolean;
    limit?: number;
    threshold?: number;
  }) =>
    request<KnowledgeSearchResponse>('/memories/knowledge/search', {
      method: 'POST',
      body: JSON.stringify({ query, ...options }),
    }),
};

// Providers
export const providers = {
  list: () => request<{ providers: Provider[]; total: number }>('/providers'),

  get: (id: number) => request<Provider>(`/providers/${id}`),

  create: (data: { name: string; api_base_url?: string; is_local?: boolean }) =>
    request<Provider>('/providers', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/providers/${id}`, { method: 'DELETE' }),
};

// Models
export const models = {
  list: (providerId?: number, includeDeprecated = false) => {
    const params = new URLSearchParams();
    if (providerId) params.set('provider_id', String(providerId));
    if (includeDeprecated) params.set('include_deprecated', 'true');
    const query = params.toString();
    return request<{ models: Model[]; total: number }>(`/models${query ? `?${query}` : ''}`);
  },

  get: (id: number) => request<Model>(`/models/${id}`),

  create: (data: Partial<Model>) =>
    request<Model>('/models', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: Partial<Model>) =>
    request<Model>(`/models/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/models/${id}`, { method: 'DELETE' }),
};

// Personas
export const personas = {
  list: () => request<{ personas: Persona[]; total: number }>('/personas'),

  get: (id: number) => request<Persona>(`/personas/${id}`),

  create: (data: PersonaCreate) =>
    request<Persona>('/personas', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: Partial<PersonaCreate>) =>
    request<Persona>(`/personas/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/personas/${id}`, { method: 'DELETE' }),
};

// Background Tasks
export const backgroundTasks = {
  list: (status?: BackgroundTaskStatus, agentId?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (agentId) params.set('agent_id', String(agentId));
    const query = params.toString();
    return request<{ tasks: BackgroundTask[]; total: number; counts: Record<string, number> }>(
      `/background-tasks${query ? `?${query}` : ''}`
    );
  },

  get: (id: number) => request<BackgroundTask>(`/background-tasks/${id}`),

  create: (data: BackgroundTaskCreate) =>
    request<BackgroundTask>('/background-tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  pause: (id: number) =>
    request<{ status: string; task_id: number }>(`/background-tasks/${id}/pause`, {
      method: 'POST',
    }),

  resume: (id: number) =>
    request<{ status: string; task_id: number }>(`/background-tasks/${id}/resume`, {
      method: 'POST',
    }),

  cancel: (id: number) =>
    request<{ status: string; task_id: number }>(`/background-tasks/${id}/cancel`, {
      method: 'POST',
    }),

  getSteps: (id: number, limit = 100, offset = 0) =>
    request<{ steps: BackgroundTaskStep[]; total: number; task_id: number }>(
      `/background-tasks/${id}/steps?limit=${limit}&offset=${offset}`
    ),

  delete: (id: number) =>
    request<void>(`/background-tasks/${id}`, { method: 'DELETE' }),
};

// Scheduled Actions
export const scheduledActions = {
  list: (status?: ScheduledActionStatus, agentId?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (agentId) params.set('agent_id', String(agentId));
    const query = params.toString();
    return request<ScheduledAction[]>(`/scheduled-actions${query ? `?${query}` : ''}`);
  },

  get: (id: number) => request<ScheduledAction>(`/scheduled-actions/${id}`),

  create: (data: ScheduledActionCreate) =>
    request<ScheduledAction>('/scheduled-actions', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: Partial<ScheduledActionCreate>) =>
    request<ScheduledAction>(`/scheduled-actions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  pause: (id: number) =>
    request<{ status: string; action_id: number }>(`/scheduled-actions/${id}/pause`, {
      method: 'POST',
    }),

  resume: (id: number) =>
    request<{ status: string; action_id: number }>(`/scheduled-actions/${id}/resume`, {
      method: 'POST',
    }),

  trigger: (id: number) =>
    request<{ status: string; action_id: number }>(`/scheduled-actions/${id}/trigger`, {
      method: 'POST',
    }),

  delete: (id: number) =>
    request<void>(`/scheduled-actions/${id}`, { method: 'DELETE' }),

  getRuns: (id: number, limit = 20, offset = 0) =>
    request<ScheduledActionRun[]>(
      `/scheduled-actions/${id}/runs?limit=${limit}&offset=${offset}`
    ),
};

// Goals
export const goals = {
  list: (status?: GoalStatus, rootOnly = false, agentId?: number, circleId?: number) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (rootOnly) params.set('root_only', 'true');
    if (agentId) params.set('agent_id', String(agentId));
    if (circleId) params.set('circle_id', String(circleId));
    const query = params.toString();
    return request<{ goals: Goal[]; total: number; counts: Record<string, number> }>(
      `/goals${query ? `?${query}` : ''}`
    );
  },

  get: (id: number) => request<Goal>(`/goals/${id}`),

  create: (data: GoalCreate) =>
    request<Goal>('/goals', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: GoalUpdate) =>
    request<Goal>(`/goals/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/goals/${id}`, { method: 'DELETE' }),

  // Status management
  start: (id: number) =>
    request<Goal>(`/goals/${id}/start`, { method: 'POST' }),

  complete: (id: number, resultSummary?: string) =>
    request<Goal>(`/goals/${id}/complete${resultSummary ? `?result_summary=${encodeURIComponent(resultSummary)}` : ''}`, {
      method: 'POST',
    }),

  fail: (id: number, reason: string, lessonsLearned?: string) => {
    const params = new URLSearchParams({ reason });
    if (lessonsLearned) params.set('lessons_learned', lessonsLearned);
    return request<Goal>(`/goals/${id}/fail?${params}`, { method: 'POST' });
  },

  pause: (id: number, reason?: string) =>
    request<Goal>(`/goals/${id}/pause${reason ? `?reason=${encodeURIComponent(reason)}` : ''}`, {
      method: 'POST',
    }),

  resume: (id: number) =>
    request<Goal>(`/goals/${id}/resume`, { method: 'POST' }),

  updateProgress: (id: number, percent: number, message?: string) => {
    const params = new URLSearchParams({ percent: String(percent) });
    if (message) params.set('message', message);
    return request<Goal>(`/goals/${id}/progress?${params}`, { method: 'POST' });
  },

  // Decomposition and hierarchy
  decompose: (id: number, maxSubgoals = 5) =>
    request<{ goal_id: number; subgoal_count: number; subgoals: Goal[] }>(
      `/goals/${id}/decompose`,
      {
        method: 'POST',
        body: JSON.stringify({ max_subgoals: maxSubgoals }),
      }
    ),

  getSubgoals: (id: number) =>
    request<{ goal_id: number; subgoals: Goal[] }>(`/goals/${id}/subgoals`),

  getTree: (id: number) =>
    request<Goal & { subgoals: Goal[] }>(`/goals/${id}/tree`),

  // Dependencies
  addDependency: (id: number, dependsOnId: number, dependencyType = 'blocks') =>
    request<{ goal_id: number; depends_on_id: number; dependency_type: string }>(
      `/goals/${id}/dependencies`,
      {
        method: 'POST',
        body: JSON.stringify({ depends_on_id: dependsOnId, dependency_type: dependencyType }),
      }
    ),

  removeDependency: (id: number, dependsOnId: number) =>
    request<void>(`/goals/${id}/dependencies/${dependsOnId}`, { method: 'DELETE' }),

  getDependencies: (id: number) =>
    request<{ goal_id: number; dependencies: Goal[] }>(`/goals/${id}/dependencies`),

  getDependents: (id: number) =>
    request<{ goal_id: number; dependents: Goal[] }>(`/goals/${id}/dependents`),

  // Activities
  getActivities: (id: number, limit = 50, offset = 0) =>
    request<{ goal_id: number; activities: GoalActivity[] }>(
      `/goals/${id}/activities?limit=${limit}&offset=${offset}`
    ),
};

// Settings
export const settings = {
  get: () => request<AllSettings>('/settings'),

  updateProvider: (provider: string, data: { api_key?: string; default_model?: string; base_url?: string }) =>
    request<ProviderSettings>(`/settings/providers/${provider}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  updateApplication: (data: { debug?: boolean; log_level?: string }) =>
    request<ApplicationSettings>('/settings/application', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  testProvider: (provider: string) =>
    request<ProviderTestResult>(`/settings/providers/${provider}/test`, {
      method: 'POST',
    }),
};

// Projects
export const projects = {
  list: (status?: ProjectStatus) => {
    const params = status ? `?status=${status}` : '';
    return request<{ projects: Project[]; total: number }>(`/projects${params}`);
  },

  get: (id: number) => request<Project>(`/projects/${id}`),

  create: (data: ProjectCreate) =>
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: ProjectUpdate) =>
    request<Project>(`/projects/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  refresh: (id: number) =>
    request<Project>(`/projects/${id}/refresh`, { method: 'POST' }),

  getContext: (id: number) =>
    request<ProjectContext>(`/projects/${id}/context`),

  // Folder browsing
  browseFolders: (path?: string, showHidden = false) => {
    const params = new URLSearchParams();
    if (path) params.set('path', path);
    if (showHidden) params.set('show_hidden', 'true');
    const query = params.toString();
    return request<FolderBrowseResponse>(`/projects/browse/folders${query ? `?${query}` : ''}`);
  },

  // Circle linking
  linkCircle: (projectId: number, circleId: number, isPrimary = false) =>
    request<{ status: string; project_id: number; circle_id: number }>(
      `/projects/${projectId}/circles/${circleId}?is_primary=${isPrimary}`,
      { method: 'POST' }
    ),

  unlinkCircle: (projectId: number, circleId: number) =>
    request<void>(`/projects/${projectId}/circles/${circleId}`, { method: 'DELETE' }),

  listCircles: (projectId: number) =>
    request<{
      project_id: number;
      project_name: string;
      circles: { circle_id: number; is_primary: boolean; linked_at: string }[];
      total: number;
    }>(`/projects/${projectId}/circles`),
};

// Pipelines
export const pipelines = {
  list: (status?: PipelineStatus) => {
    const params = status ? `?status=${status}` : '';
    return request<{ pipelines: Pipeline[]; total: number }>(`/pipelines${params}`);
  },

  get: (id: number) => request<Pipeline>(`/pipelines/${id}`),

  create: (data: PipelineCreate) =>
    request<Pipeline>('/pipelines', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: number, data: PipelineUpdate) =>
    request<Pipeline>(`/pipelines/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    request<void>(`/pipelines/${id}`, { method: 'DELETE' }),

  toggle: (id: number) =>
    request<Pipeline>(`/pipelines/${id}/toggle`, { method: 'POST' }),

  run: (id: number, triggerData?: Record<string, unknown>) =>
    request<PipelineRun>(`/pipelines/${id}/run`, {
      method: 'POST',
      body: JSON.stringify({ trigger_data: triggerData }),
    }),

  getRuns: (id: number, status?: PipelineRunStatus, limit = 20, offset = 0) => {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    params.set('limit', String(limit));
    params.set('offset', String(offset));
    return request<{ runs: PipelineRun[]; total: number }>(
      `/pipelines/${id}/runs?${params}`
    );
  },

  getRun: (pipelineId: number, runId: number) =>
    request<PipelineRun>(`/pipelines/${pipelineId}/runs/${runId}`),

  cancelRun: (pipelineId: number, runId: number) =>
    request<{ status: string }>(`/pipelines/${pipelineId}/runs/${runId}/cancel`, {
      method: 'POST',
    }),
};

// Generic HTTP methods for workspace endpoints
export const get = (path: string, options?: { params?: Record<string, any> }) => {
  let fullPath = path;
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    });
    const queryString = params.toString();
    if (queryString) {
      fullPath += `?${queryString}`;
    }
  }
  return request(fullPath, { method: 'GET' }).then(data => ({ data }));
};

export const post = (path: string, data?: any, options?: { params?: Record<string, any> }) => {
  let fullPath = path;
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    });
    const queryString = params.toString();
    if (queryString) {
      fullPath += `?${queryString}`;
    }
  }
  return request(fullPath, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  }).then(data => ({ data }));
};

export const put = (path: string, data?: any, options?: { params?: Record<string, any> }) => {
  let fullPath = path;
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    });
    const queryString = params.toString();
    if (queryString) {
      fullPath += `?${queryString}`;
    }
  }
  return request(fullPath, {
    method: 'PUT',
    body: data ? JSON.stringify(data) : undefined,
  }).then(data => ({ data }));
};

export const del = (path: string, options?: { params?: Record<string, any> }) => {
  let fullPath = path;
  if (options?.params) {
    const params = new URLSearchParams();
    Object.entries(options.params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.set(key, String(value));
      }
    });
    const queryString = params.toString();
    if (queryString) {
      fullPath += `?${queryString}`;
    }
  }
  return request(fullPath, { method: 'DELETE' }).then(data => ({ data }));
};

export default { get, post, put, delete: del, health, agents, circles, conversations, memories, providers, models, personas, backgroundTasks, scheduledActions, goals, settings, projects, pipelines };
