import { describe, it, expect } from 'vitest';
import type {
  Agent,
  AgentDetail,
  Circle,
  Task,
  Conversation,
  Memory,
  Goal,
  BackgroundTask,
  ScheduledAction,
  Project,
  Pipeline,
  PipelineNode,
  PipelineEdge,
  PipelineRun,
  AgentStatus,
  TaskStatus,
  TaskPriority,
  CircleStatus,
  ConversationStatus,
  MemoryType,
  KnowledgeCategory,
  GoalStatus,
  GoalPriority,
  BackgroundTaskStatus,
  ScheduleType,
  ScheduledActionStatus,
  ProjectStatus,
  PipelineStatus,
  PipelineNodeType,
  PipelineRunStatus,
} from './index';

describe('Type Definitions', () => {
  describe('Agent Types', () => {
    it('allows valid AgentStatus values', () => {
      const statuses: AgentStatus[] = ['idle', 'busy', 'offline'];
      expect(statuses).toHaveLength(3);
    });

    it('defines Agent interface correctly', () => {
      const agent: Agent = {
        id: 1,
        name: 'Sophie',
        role: 'Developer',
        provider: 'anthropic',
        model: 'claude-3',
        status: 'idle',
        competencies: ['python', 'typescript'],
        can_review: ['code'],
        current_task: null,
        created_at: '2024-01-01T00:00:00Z',
        last_activity: null,
      };

      expect(agent.id).toBe(1);
      expect(agent.name).toBe('Sophie');
      expect(agent.competencies).toContain('python');
    });

    it('defines AgentDetail with extended fields', () => {
      const agentDetail: AgentDetail = {
        id: 1,
        name: 'Sophie',
        role: 'Developer',
        provider: 'anthropic',
        model: 'claude-3',
        status: 'idle',
        competencies: ['python'],
        can_review: ['code'],
        current_task: null,
        created_at: '2024-01-01T00:00:00Z',
        last_activity: null,
        persona: {
          name: 'Sophie',
          role: 'Developer',
          traits: ['analytical', 'helpful'],
          communication_style: 'professional',
          specializations: ['backend'],
          languages: ['en', 'fr'],
        },
        config: {
          provider: 'anthropic',
          model: 'claude-3',
          max_tokens: 4096,
          temperature: 0.7,
          competencies: ['python'],
          can_review: ['code'],
        },
        session: null,
        skills: ['code_review', 'debugging'],
        tools_count: 5,
      };

      expect(agentDetail.persona.traits).toContain('analytical');
      expect(agentDetail.skills).toContain('code_review');
    });
  });

  describe('Circle Types', () => {
    it('allows valid CircleStatus values', () => {
      const statuses: CircleStatus[] = ['stopped', 'starting', 'running', 'stopping'];
      expect(statuses).toHaveLength(4);
    });

    it('defines Circle interface correctly', () => {
      const circle: Circle = {
        id: 'circle-1',
        name: 'dev-team',
        status: 'running',
        agent_count: 2,
        task_count: 5,
        active_tasks: 2,
        require_review: true,
        auto_route: false,
        created_at: '2024-01-01T00:00:00Z',
        started_at: '2024-01-01T01:00:00Z',
        project_id: 1,
        project_name: 'gathering',
      };

      expect(circle.name).toBe('dev-team');
      expect(circle.status).toBe('running');
      expect(circle.project_name).toBe('gathering');
    });
  });

  describe('Task Types', () => {
    it('allows valid TaskStatus values', () => {
      const statuses: TaskStatus[] = [
        'pending', 'assigned', 'in_progress', 'in_review', 'review', 'completed', 'failed'
      ];
      expect(statuses).toHaveLength(7);
    });

    it('allows valid TaskPriority values', () => {
      const priorities: TaskPriority[] = ['low', 'medium', 'high', 'critical'];
      expect(priorities).toHaveLength(4);
    });

    it('defines Task interface correctly', () => {
      const task: Task = {
        id: 1,
        title: 'Implement feature',
        description: 'Add new functionality',
        status: 'in_progress',
        priority: 'high',
        assigned_agent_id: 1,
        assigned_agent_name: 'Sophie',
        reviewer_id: null,
        reviewer_name: null,
        created_at: '2024-01-01T00:00:00Z',
        started_at: '2024-01-01T01:00:00Z',
        completed_at: null,
        result: null,
      };

      expect(task.title).toBe('Implement feature');
      expect(task.priority).toBe('high');
    });
  });

  describe('Conversation Types', () => {
    it('allows valid ConversationStatus values', () => {
      const statuses: ConversationStatus[] = ['pending', 'active', 'completed', 'cancelled'];
      expect(statuses).toHaveLength(4);
    });

    it('defines Conversation interface correctly', () => {
      const conversation: Conversation = {
        id: 'conv-1',
        topic: 'Code Review',
        status: 'active',
        participant_names: ['Sophie', 'Olivia'],
        turns_taken: 5,
        max_turns: 10,
        started_at: '2024-01-01T00:00:00Z',
        completed_at: null,
      };

      expect(conversation.topic).toBe('Code Review');
      expect(conversation.participant_names).toContain('Sophie');
    });
  });

  describe('Memory Types', () => {
    it('allows valid MemoryType values', () => {
      const types: MemoryType[] = [
        'fact', 'preference', 'context', 'decision', 'error', 'feedback', 'learning'
      ];
      expect(types).toHaveLength(7);
    });

    it('allows valid KnowledgeCategory values', () => {
      const categories: KnowledgeCategory[] = ['docs', 'best_practice', 'decision', 'faq'];
      expect(categories).toHaveLength(4);
    });

    it('defines Memory interface correctly', () => {
      const memory: Memory = {
        id: 1,
        key: 'project-setup',
        value: 'Use npm install to setup',
        memory_type: 'fact',
        importance: 0.8,
      };

      expect(memory.key).toBe('project-setup');
      expect(memory.memory_type).toBe('fact');
    });
  });

  describe('Goal Types', () => {
    it('allows valid GoalStatus values', () => {
      const statuses: GoalStatus[] = [
        'pending', 'active', 'blocked', 'paused', 'completed', 'failed', 'cancelled'
      ];
      expect(statuses).toHaveLength(7);
    });

    it('allows valid GoalPriority values', () => {
      const priorities: GoalPriority[] = ['low', 'medium', 'high', 'critical'];
      expect(priorities).toHaveLength(4);
    });

    it('defines Goal interface correctly', () => {
      const goal: Goal = {
        id: 1,
        agent_id: 1,
        depth: 0,
        title: 'Complete feature',
        description: 'Implement and test new feature',
        status: 'active',
        priority: 'high',
        progress_percent: 50,
        actual_hours: 2.5,
        is_decomposed: false,
        attempts: 1,
        max_attempts: 3,
        artifacts: [],
        tags: ['feature', 'v1'],
        created_at: '2024-01-01T00:00:00Z',
        subgoal_count: 0,
        completed_subgoals: 0,
        blocking_count: 0,
      };

      expect(goal.title).toBe('Complete feature');
      expect(goal.progress_percent).toBe(50);
    });
  });

  describe('BackgroundTask Types', () => {
    it('allows valid BackgroundTaskStatus values', () => {
      const statuses: BackgroundTaskStatus[] = [
        'pending', 'running', 'paused', 'completed', 'failed', 'cancelled', 'timeout'
      ];
      expect(statuses).toHaveLength(7);
    });

    it('defines BackgroundTask interface correctly', () => {
      const task: BackgroundTask = {
        id: 1,
        agent_id: 1,
        goal: 'Analyze codebase',
        status: 'running',
        current_step: 5,
        max_steps: 100,
        progress_percent: 5,
        total_llm_calls: 10,
        total_tokens_used: 5000,
        total_tool_calls: 15,
        created_at: '2024-01-01T00:00:00Z',
        duration_seconds: 120,
      };

      expect(task.goal).toBe('Analyze codebase');
      expect(task.status).toBe('running');
    });
  });

  describe('ScheduledAction Types', () => {
    it('allows valid ScheduleType values', () => {
      const types: ScheduleType[] = ['cron', 'interval', 'once', 'event'];
      expect(types).toHaveLength(4);
    });

    it('allows valid ScheduledActionStatus values', () => {
      const statuses: ScheduledActionStatus[] = ['active', 'paused', 'disabled', 'expired'];
      expect(statuses).toHaveLength(4);
    });

    it('defines ScheduledAction interface correctly', () => {
      const action: ScheduledAction = {
        id: 1,
        agent_id: 1,
        name: 'Daily backup',
        goal: 'Backup database',
        schedule_type: 'cron',
        cron_expression: '0 0 * * *',
        status: 'active',
        max_steps: 50,
        timeout_seconds: 300,
        retry_on_failure: true,
        max_retries: 3,
        retry_delay_seconds: 60,
        allow_concurrent: false,
        execution_count: 10,
        tags: ['backup', 'maintenance'],
        created_at: '2024-01-01T00:00:00Z',
        successful_runs: 9,
        failed_runs: 1,
      };

      expect(action.name).toBe('Daily backup');
      expect(action.schedule_type).toBe('cron');
    });
  });

  describe('Project Types', () => {
    it('allows valid ProjectStatus values', () => {
      const statuses: ProjectStatus[] = ['active', 'archived', 'on_hold'];
      expect(statuses).toHaveLength(3);
    });

    it('defines Project interface correctly', () => {
      const project: Project = {
        id: 1,
        name: 'gathering',
        path: '/home/user/gathering',
        status: 'active',
        branch: 'develop',
        tech_stack: ['python', 'react'],
        languages: ['python', 'typescript'],
        frameworks: ['fastapi', 'react'],
        tools: {},
        conventions: {},
        key_files: {},
        commands: { test: 'pytest', build: 'npm run build' },
        notes: [],
        circle_count: 1,
        created_at: '2024-01-01T00:00:00Z',
      };

      expect(project.name).toBe('gathering');
      expect(project.tech_stack).toContain('python');
    });
  });

  describe('Pipeline Types', () => {
    it('allows valid PipelineStatus values', () => {
      const statuses: PipelineStatus[] = ['active', 'paused', 'draft'];
      expect(statuses).toHaveLength(3);
    });

    it('allows valid PipelineNodeType values', () => {
      const types: PipelineNodeType[] = [
        'trigger', 'agent', 'condition', 'action', 'parallel', 'delay'
      ];
      expect(types).toHaveLength(6);
    });

    it('allows valid PipelineRunStatus values', () => {
      const statuses: PipelineRunStatus[] = [
        'pending', 'running', 'completed', 'failed', 'cancelled'
      ];
      expect(statuses).toHaveLength(5);
    });

    it('defines PipelineNode interface correctly', () => {
      const node: PipelineNode = {
        id: 'node-1',
        type: 'trigger',
        name: 'On PR Created',
        config: {
          trigger_type: 'webhook',
          event: 'pull_request.opened',
        },
        position: { x: 100, y: 50 },
      };

      expect(node.id).toBe('node-1');
      expect(node.type).toBe('trigger');
      expect(node.config.trigger_type).toBe('webhook');
    });

    it('defines PipelineNode with agent config', () => {
      const node: PipelineNode = {
        id: 'node-2',
        type: 'agent',
        name: 'Sophie - Code Review',
        config: {
          agent_id: 1,
          agent_name: 'Sophie',
          task: 'code_review',
          task_prompt: 'Review the code changes',
        },
        position: { x: 200, y: 50 },
      };

      expect(node.type).toBe('agent');
      expect(node.config.agent_id).toBe(1);
      expect(node.config.task_prompt).toBe('Review the code changes');
    });

    it('defines PipelineEdge interface correctly', () => {
      const edge: PipelineEdge = {
        id: 'edge-1',
        from: 'node-1',
        to: 'node-2',
        condition: 'approved',
      };

      expect(edge.from).toBe('node-1');
      expect(edge.to).toBe('node-2');
      expect(edge.condition).toBe('approved');
    });

    it('defines Pipeline interface correctly', () => {
      const pipeline: Pipeline = {
        id: 1,
        name: 'Code Review Workflow',
        description: 'Automated code review with multiple agents',
        status: 'active',
        nodes: [
          {
            id: 'n1',
            type: 'trigger',
            name: 'PR Created',
            config: { trigger_type: 'webhook' },
            position: { x: 50, y: 100 },
          },
          {
            id: 'n2',
            type: 'agent',
            name: 'Sophie - Review',
            config: { agent_id: 1, agent_name: 'Sophie' },
            position: { x: 250, y: 100 },
          },
        ],
        edges: [
          { id: 'e1', from: 'n1', to: 'n2' },
        ],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
        last_run: '2024-01-15T10:00:00Z',
        run_count: 25,
        success_count: 23,
        error_count: 2,
      };

      expect(pipeline.name).toBe('Code Review Workflow');
      expect(pipeline.status).toBe('active');
      expect(pipeline.nodes).toHaveLength(2);
      expect(pipeline.edges).toHaveLength(1);
      expect(pipeline.run_count).toBe(25);
    });

    it('defines PipelineRun interface correctly', () => {
      const run: PipelineRun = {
        id: 1,
        pipeline_id: 1,
        status: 'completed',
        started_at: '2024-01-15T10:00:00Z',
        completed_at: '2024-01-15T10:05:00Z',
        current_node: 'n2',
        logs: [
          {
            timestamp: '2024-01-15T10:00:00Z',
            node_id: 'n1',
            message: 'Trigger activated',
            level: 'info',
          },
          {
            timestamp: '2024-01-15T10:01:00Z',
            node_id: 'n2',
            message: 'Agent started review',
            level: 'info',
          },
        ],
        trigger_data: { pr_number: 123 },
        duration_seconds: 300,
      };

      expect(run.status).toBe('completed');
      expect(run.logs).toHaveLength(2);
      expect(run.duration_seconds).toBe(300);
    });

    it('defines PipelineRun with error state', () => {
      const run: PipelineRun = {
        id: 2,
        pipeline_id: 1,
        status: 'failed',
        started_at: '2024-01-15T11:00:00Z',
        current_node: 'n2',
        logs: [
          {
            timestamp: '2024-01-15T11:00:00Z',
            node_id: 'n2',
            message: 'Agent connection timeout',
            level: 'error',
          },
        ],
        error_message: 'Agent connection timeout after 30s',
        duration_seconds: 30,
      };

      expect(run.status).toBe('failed');
      expect(run.error_message).toBe('Agent connection timeout after 30s');
      expect(run.logs[0].level).toBe('error');
    });
  });
});
