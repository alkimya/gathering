// API Types for GatheRing Dashboard

export type AgentStatus = 'idle' | 'busy' | 'offline';
export type TaskStatus = 'pending' | 'assigned' | 'in_progress' | 'in_review' | 'review' | 'completed' | 'failed';
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';
export type CircleStatus = 'stopped' | 'starting' | 'running' | 'stopping';
export type ConversationStatus = 'pending' | 'active' | 'completed' | 'cancelled';

export interface AgentPersona {
  name: string;
  role: string;
  traits: string[];
  communication_style: string;
  specializations: string[];
  languages: string[];
}

export interface AgentConfig {
  provider: string;
  model: string;
  max_tokens: number;
  temperature: number;
  competencies: string[];
  can_review: string[];
}

export interface Agent {
  id: number;
  name: string;
  role: string;
  provider: string;
  model: string;
  status: AgentStatus;
  competencies: string[];
  can_review: string[];
  current_task: string | null;
  created_at: string;
  last_activity: string | null;
  memory_count?: number;
  message_count?: number;
}

export interface AgentDetail extends Agent {
  persona: AgentPersona;
  config: AgentConfig;
  session: {
    status: string;
    working_files: string[];
    pending_actions: string[];
    message_count: number;
    needs_resume: boolean;
    time_since: string;
  } | null;
  skills: string[];
  tools_count: number;
}

export interface Circle {
  id: string;
  name: string;
  status: CircleStatus;
  agent_count: number;
  task_count: number;
  active_tasks: number;
  require_review: boolean;
  auto_route: boolean;
  created_at: string;
  started_at: string | null;
  project_id: number | null;
  project_name: string | null;
}

export interface CircleDetail extends Circle {
  agents: Agent[];
  pending_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  conflicts: number;
}

export interface Task {
  id: number;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  assigned_agent_id: number | null;
  assigned_agent_name: string | null;
  reviewer_id: number | null;
  reviewer_name: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
}

export interface ConversationMessage {
  agent_id: number;
  agent_name: string;
  content: string;
  mentions: number[];
  timestamp: string;
}

export interface Conversation {
  id: string;
  topic: string;
  status: ConversationStatus;
  participant_names: string[];
  participant_count?: number;
  participants?: string[];
  turns_taken: number;
  max_turns: number;
  message_count?: number;
  created_at?: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface CircleMetrics {
  tasks_completed: number;
  tasks_in_progress: number;
  conflicts_resolved: number;
  uptime_seconds: number;
}

export interface ConversationDetail extends Conversation {
  messages: ConversationMessage[];
  transcript: string;
  summary: string | null;
  duration_seconds: number;
}

export interface ChatRequest {
  message: string;
  include_memories?: boolean;
  allow_tools?: boolean;
}

export interface ChatResponse {
  content: string;
  agent_id: number;
  agent_name: string;
  model: string;
  duration_ms: number;
  tool_calls: unknown[];
  tool_results: unknown[];
  tokens_used: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds: number;
  agents_count: number;
  circles_count: number;
  active_tasks: number;
}

export interface CpuMetrics {
  percent: number;
  count: number;
  frequency_mhz: number | null;
}

export interface MemoryMetrics {
  total_gb: number;
  available_gb: number;
  used_gb: number;
  percent: number;
}

export interface DiskMetrics {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

export interface LoadAverage {
  '1min': number;
  '5min': number;
  '15min': number;
}

export interface SystemMetricsResponse {
  cpu: CpuMetrics;
  memory: MemoryMetrics;
  disk: DiskMetrics;
  load_average: LoadAverage;
  uptime_seconds: number;
}

export interface ServiceHealth {
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  message?: string;
  value?: string;
  last_check: string;
}

export interface HealthChecksResponse {
  checks: ServiceHealth[];
  overall_status: 'healthy' | 'warning' | 'critical';
}

export interface WebSocketEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// RAG/Memory Types
export type MemoryType = 'fact' | 'preference' | 'context' | 'decision' | 'error' | 'feedback' | 'learning';
export type KnowledgeCategory = 'docs' | 'best_practice' | 'decision' | 'faq';

export interface Memory {
  id: number;
  key: string;
  value: string;
  memory_type: MemoryType;
  similarity?: number;
  importance: number;
}

export interface MemoryCreate {
  content: string;
  memory_type?: MemoryType;
  key?: string;
  tags?: string[];
  importance?: number;
}

export interface RecallRequest {
  query: string;
  memory_type?: MemoryType;
  tags?: string[];
  limit?: number;
  threshold?: number;
}

export interface RecallResponse {
  query: string;
  memories: Memory[];
  total: number;
}

export interface Knowledge {
  id: number;
  title: string;
  content: string;
  category?: KnowledgeCategory;
  similarity?: number;
  tags?: string[];
}

export interface KnowledgeCreate {
  title: string;
  content: string;
  category?: KnowledgeCategory;
  project_id?: number;
  circle_id?: number;
  is_global?: boolean;
  tags?: string[];
  source_url?: string;
}

export interface KnowledgeSearchRequest {
  query: string;
  project_id?: number;
  circle_id?: number;
  category?: KnowledgeCategory;
  include_global?: boolean;
  limit?: number;
  threshold?: number;
}

export interface KnowledgeSearchResponse {
  query: string;
  results: Knowledge[];
  total: number;
}

export interface KnowledgeListResponse {
  entries: Knowledge[];
  total: number;
  page: number;
  page_size: number;
}

export interface KnowledgeStatsResponse {
  total_entries: number;
  by_category: Record<string, number>;
  recent_entries: Knowledge[];
}

export interface DocumentUploadResponse {
  id: number;
  title: string;
  filename: string;
  format: string;
  char_count: number;
  chunk_count: number;
  category?: KnowledgeCategory;
  tags?: string[];
}

export interface MemoryStats {
  total_memories: number;
  active_memories: number;
  embedded_memories: number;
  avg_importance?: number;
}

// Provider & Model Types
export interface Provider {
  id: number;
  name: string;
  api_base_url: string | null;
  is_local: boolean;
  created_at: string;
  model_count?: number;
}

export interface Model {
  id: number;
  provider_id: number;
  provider_name?: string;
  model_name: string;
  model_alias: string | null;
  pricing_in: number | null;
  pricing_out: number | null;
  pricing_cache_read: number | null;
  pricing_cache_write: number | null;
  extended_thinking: boolean;
  vision: boolean;
  function_calling: boolean;
  streaming: boolean;
  context_window: number | null;
  max_output: number | null;
  release_date: string | null;
  is_deprecated: boolean;
  created_at: string;
}

export interface Persona {
  id: number;
  display_name: string;
  role: string;
  base_prompt: string | null;
  full_prompt: string | null;
  traits: string[];
  communication_style: string;
  specializations: string[];
  languages: string[];
  motto: string | null;
  work_ethic: string[];
  collaboration_notes: string | null;
  description: string | null;
  icon: string | null;
  is_builtin: boolean;
  default_model_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface PersonaCreate {
  display_name: string;
  role: string;
  base_prompt?: string;
  full_prompt?: string;
  traits?: string[];
  communication_style?: string;
  specializations?: string[];
  languages?: string[];
  motto?: string;
  description?: string;
  default_model_id?: number;
}

export interface AgentCreate {
  name: string;
  persona_id?: number;
  model_id: number;
  temperature?: number;
  max_tokens?: number;
  can_review?: string[];
  review_strictness?: number;
}

// Background Task Types
export type BackgroundTaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'timeout';

export interface BackgroundTask {
  id: number;
  agent_id: number;
  agent_name?: string;
  agent_display_name?: string;
  goal: string;
  status: BackgroundTaskStatus;
  circle_id?: number;
  circle_name?: string;
  current_step: number;
  max_steps: number;
  progress_percent: number;
  progress_summary?: string;
  last_action?: string;
  error_message?: string;
  total_llm_calls: number;
  total_tokens_used: number;
  total_tool_calls: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration_seconds: number;
}

export interface BackgroundTaskCreate {
  agent_id: number;
  goal: string;
  circle_id?: number;
  goal_context?: Record<string, unknown>;
  max_steps?: number;
  timeout_seconds?: number;
  checkpoint_interval?: number;
}

export interface BackgroundTaskStep {
  id: number;
  task_id: number;
  step_number: number;
  action_type: string;
  action_input?: string;
  action_output?: string;
  tool_name?: string;
  success: boolean;
  error_message?: string;
  tokens_input: number;
  tokens_output: number;
  duration_ms: number;
  created_at: string;
}

// Scheduled Action Types
export type ScheduleType = 'cron' | 'interval' | 'once' | 'event';
export type ScheduledActionStatus = 'active' | 'paused' | 'disabled' | 'expired';

export interface ScheduledAction {
  id: number;
  agent_id: number;
  agent_name?: string;
  circle_id?: number;
  circle_name?: string;
  name: string;
  description?: string;
  goal: string;
  schedule_type: ScheduleType;
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  status: ScheduledActionStatus;
  max_steps: number;
  timeout_seconds: number;
  retry_on_failure: boolean;
  max_retries: number;
  retry_delay_seconds: number;
  allow_concurrent: boolean;
  start_date?: string;
  end_date?: string;
  max_executions?: number;
  execution_count: number;
  last_run_at?: string;
  next_run_at?: string;
  tags: string[];
  created_at: string;
  last_run_status?: string;
  last_run_duration?: number;
  successful_runs: number;
  failed_runs: number;
}

export interface ScheduledActionCreate {
  agent_id: number;
  name: string;
  goal: string;
  schedule_type: ScheduleType;
  cron_expression?: string;
  interval_seconds?: number;
  event_trigger?: string;
  next_run_at?: string;
  circle_id?: number;
  description?: string;
  max_steps?: number;
  timeout_seconds?: number;
  retry_on_failure?: boolean;
  max_retries?: number;
  retry_delay_seconds?: number;
  allow_concurrent?: boolean;
  start_date?: string;
  end_date?: string;
  max_executions?: number;
  tags?: string[];
}

export interface ScheduledActionRun {
  id: number;
  scheduled_action_id: number;
  background_task_id?: number;
  run_number: number;
  triggered_at: string;
  triggered_by: string;
  status: BackgroundTaskStatus;
  started_at?: string;
  completed_at?: string;
  result_summary?: string;
  error_message?: string;
  retry_count: number;
  duration_ms: number;
  steps_executed: number;
}

// Goal Types
export type GoalStatus = 'pending' | 'active' | 'blocked' | 'paused' | 'completed' | 'failed' | 'cancelled';
export type GoalPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Goal {
  id: number;
  agent_id: number;
  circle_id?: number;
  parent_id?: number;
  depth: number;
  title: string;
  description: string;
  success_criteria?: string;
  status: GoalStatus;
  priority: GoalPriority;
  progress_percent: number;
  status_message?: string;
  deadline?: string;
  estimated_hours?: number;
  actual_hours: number;
  is_decomposed: boolean;
  decomposition_strategy?: string;
  background_task_id?: number;
  last_worked_at?: string;
  attempts: number;
  max_attempts: number;
  result_summary?: string;
  artifacts: Record<string, unknown>[];
  lessons_learned?: string;
  tags: string[];
  metadata?: Record<string, unknown>;
  created_by?: string;
  created_at: string;
  updated_at?: string;
  started_at?: string;
  completed_at?: string;
  agent_name?: string;
  agent_display_name?: string;
  circle_name?: string;
  subgoal_count: number;
  completed_subgoals: number;
  blocking_count: number;
}

export interface GoalCreate {
  agent_id: number;
  title: string;
  description: string;
  circle_id?: number;
  parent_id?: number;
  success_criteria?: string;
  priority?: GoalPriority;
  deadline?: string;
  estimated_hours?: number;
  tags?: string[];
  context?: Record<string, unknown>;
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  success_criteria?: string;
  priority?: GoalPriority;
  status?: GoalStatus;
  progress_percent?: number;
  status_message?: string;
  deadline?: string;
  estimated_hours?: number;
  result_summary?: string;
  lessons_learned?: string;
  tags?: string[];
}

export interface GoalActivity {
  id: number;
  goal_id: number;
  activity_type: string;
  description?: string;
  old_value?: string;
  new_value?: string;
  actor_type?: string;
  actor_id?: number;
  tokens_used: number;
  duration_ms: number;
  created_at?: string;
}

// Settings Types
export interface SettingsModelInfo {
  id: number;
  model_name: string;
  model_alias?: string;
  vision: boolean;
  extended_thinking: boolean;
}

export interface ProviderSettings {
  api_key?: string;
  default_model?: string;
  base_url?: string;
  is_configured: boolean;
  models: SettingsModelInfo[];
}

export interface DatabaseSettings {
  host: string;
  port: number;
  name: string;
  user: string;
  is_connected: boolean;
  pool_size: number;
  max_overflow: number;
  extensions: string[];
}

export interface ApplicationSettings {
  environment: string;
  debug: boolean;
  log_level: string;
}

export interface AllSettings {
  providers: Record<string, ProviderSettings>;
  database: DatabaseSettings;
  application: ApplicationSettings;
}

export interface ProviderTestResult {
  success: boolean;
  message: string;
  models?: string[];
}

// Project Types
export type ProjectStatus = 'active' | 'archived' | 'on_hold';

export interface Project {
  id: number;
  name: string;
  display_name?: string;
  path: string;
  description?: string;
  repository_url?: string;
  branch: string;
  status: ProjectStatus;
  tech_stack: string[];
  languages: string[];
  frameworks: string[];
  venv_path?: string;
  python_version?: string;
  tools: Record<string, unknown>;
  conventions: Record<string, unknown>;
  key_files: Record<string, string>;
  commands: Record<string, string>;
  notes: string[];
  circle_count: number;
  created_at: string;
  updated_at?: string;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
  auto_detect?: boolean;
}

export interface ProjectUpdate {
  name?: string;
  display_name?: string;
  description?: string;
  status?: ProjectStatus;
  venv_path?: string;
  python_version?: string;
  tools?: Record<string, unknown>;
  conventions?: Record<string, unknown>;
  key_files?: Record<string, string>;
  commands?: Record<string, string>;
  notes?: string[];
}

export interface FolderEntry {
  name: string;
  path: string;
  is_dir: boolean;
  is_project: boolean;
  size?: number;
  modified?: string;
}

export interface FolderBrowseResponse {
  current_path: string;
  parent_path?: string;
  entries: FolderEntry[];
  can_create_project: boolean;
}

export interface ProjectContext {
  project_id: number;
  project_name: string;
  prompt_context: string;
  raw: Record<string, unknown>;
}

// Pipeline Types
export type PipelineNodeType = 'trigger' | 'agent' | 'condition' | 'action' | 'parallel' | 'delay';
export type PipelineStatus = 'active' | 'paused' | 'draft';
export type PipelineRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface PipelineNodeConfig {
  trigger_type?: 'manual' | 'webhook' | 'schedule' | 'event';
  event?: string;
  cron?: string;
  agent_id?: number;
  agent_name?: string;
  task?: string;
  task_prompt?: string;
  condition?: string;
  condition_type?: 'expression' | 'output_check' | 'status_check';
  action?: string;
  action_type?: 'api_call' | 'notification' | 'webhook' | 'script';
  recipients?: string[];
  channel?: string;
  webhook_url?: string;
  delay_seconds?: number;
  parallel_nodes?: string[];
}

export interface PipelineNode {
  id: string;
  type: PipelineNodeType;
  name: string;
  config: PipelineNodeConfig;
  position: { x: number; y: number };
  next?: string[];
}

export interface PipelineEdge {
  id: string;
  from: string;
  to: string;
  condition?: string;
}

export interface Pipeline {
  id: number;
  name: string;
  description?: string;
  status: PipelineStatus;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  created_at: string;
  updated_at: string;
  last_run?: string;
  run_count: number;
  success_count: number;
  error_count: number;
}

export interface PipelineCreate {
  name: string;
  description?: string;
  nodes?: PipelineNode[];
  edges?: PipelineEdge[];
}

export interface PipelineUpdate {
  name?: string;
  description?: string;
  nodes?: PipelineNode[];
  edges?: PipelineEdge[];
}

export interface PipelineRunLog {
  timestamp: string;
  node_id: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

export interface PipelineRun {
  id: number;
  pipeline_id: number;
  status: PipelineRunStatus;
  started_at?: string;
  completed_at?: string;
  current_node?: string;
  logs: PipelineRunLog[];
  trigger_data?: Record<string, unknown>;
  error_message?: string;
  duration_seconds: number;
}

// Agent Tools/Skills Types
export interface SkillInfo {
  id: number;
  name: string;
  display_name?: string;
  description?: string;
  category: string;
  required_permissions: string[];
  is_dangerous: boolean;
  is_enabled: boolean;
  version: string;
  tools_count: number;
}

export interface AgentToolInfo {
  skill_id: number;
  skill_name: string;
  skill_display_name?: string;
  skill_category: string;
  required_permissions: string[];
  is_dangerous: boolean;
  is_enabled: boolean;
  usage_count: number;
  last_used_at?: string;
}

export interface AgentToolsResponse {
  agent_id: number;
  agent_name: string;
  tools: AgentToolInfo[];
  enabled_count: number;
  total_count: number;
}

// Agent Skills
export interface SkillDetail {
  name: string;
  description: string;
  version: string;
  tools_count: number;
  tools: string[];
}

export interface AgentSkillsResponse {
  agent_id: number;
  configured_skills: string[];
  loaded_skills: string[];
  skill_details: SkillDetail[];
  available_skills: string[];
  tools_count: number;
}
