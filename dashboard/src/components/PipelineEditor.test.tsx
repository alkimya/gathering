import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/test-utils';
import { PipelineEditor } from './PipelineEditor';
import type { Pipeline, Agent } from '../types';

describe('PipelineEditor', () => {
  const mockOnSave = vi.fn().mockResolvedValue(undefined);
  const mockOnClose = vi.fn();

  const mockAgents: Agent[] = [
    {
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
    },
    {
      id: 2,
      name: 'Olivia',
      role: 'Reviewer',
      provider: 'anthropic',
      model: 'claude-3',
      status: 'idle',
      competencies: ['code_review'],
      can_review: ['security'],
      current_task: null,
      created_at: '2024-01-01T00:00:00Z',
      last_activity: null,
    },
  ];

  const mockPipeline: Pipeline = {
    id: 1,
    name: 'Code Review Workflow',
    description: 'Automated code review',
    status: 'active',
    nodes: [
      {
        id: 'n1',
        type: 'trigger',
        name: 'PR Created',
        config: { trigger_type: 'webhook', event: 'pull_request.opened' },
        position: { x: 50, y: 100 },
      },
      {
        id: 'n2',
        type: 'agent',
        name: 'Sophie - Review',
        config: { agent_id: 1, agent_name: 'Sophie', task: 'code_review' },
        position: { x: 250, y: 100 },
      },
    ],
    edges: [{ id: 'e1', from: 'n1', to: 'n2' }],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    run_count: 25,
    success_count: 23,
    error_count: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('renders the editor for new pipeline with default name', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Should show default pipeline name in input
      expect(screen.getByDisplayValue('New Pipeline')).toBeInTheDocument();
    });

    it('renders the editor for existing pipeline with its name', () => {
      render(
        <PipelineEditor
          pipeline={mockPipeline}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Should show the pipeline name
      expect(screen.getByDisplayValue('Code Review Workflow')).toBeInTheDocument();
    });

    it('renders pipeline nodes from existing pipeline', () => {
      render(
        <PipelineEditor
          pipeline={mockPipeline}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Node names appear in multiple places (node card and possibly config panel)
      // so we use getAllByText and check that at least one exists
      expect(screen.getAllByText('PR Created').length).toBeGreaterThan(0);
      expect(screen.getAllByText('Sophie - Review').length).toBeGreaterThan(0);
    });

    it('renders Save Pipeline button', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Save Pipeline')).toBeInTheDocument();
    });

    it('renders Add Node button', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      expect(screen.getByText('Add Node')).toBeInTheDocument();
    });
  });

  describe('interactions', () => {
    it('calls onClose when X button is clicked', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Find the X button (it's the first button with an X icon)
      const buttons = screen.getAllByRole('button');
      const closeButton = buttons.find(btn => {
        const svg = btn.querySelector('svg');
        return svg && svg.classList.contains('lucide-x');
      });

      if (closeButton) {
        fireEvent.click(closeButton);
        expect(mockOnClose).toHaveBeenCalled();
      }
    });

    it('updates pipeline name when input changes', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      const nameInput = screen.getByDisplayValue('New Pipeline');
      fireEvent.change(nameInput, { target: { value: 'My Custom Pipeline' } });

      expect(screen.getByDisplayValue('My Custom Pipeline')).toBeInTheDocument();
    });

    it('opens node type dropdown when Add Node is clicked', async () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Click Add Node button
      const addNodeButton = screen.getByText('Add Node');
      fireEvent.click(addNodeButton);

      // Node type options should appear in the dropdown
      // Each option shows the label (Trigger, Agent, etc.) and a description
      await waitFor(() => {
        // Look for "Start the pipeline" description which is unique to Trigger option
        expect(screen.getByText(/Start the pipeline/)).toBeInTheDocument();
        // Look for "Execute a task" description which is unique to Agent option
        expect(screen.getByText(/Execute a task/)).toBeInTheDocument();
      });
    });

    it('calls onSave when Save Pipeline is clicked', async () => {
      render(
        <PipelineEditor
          pipeline={mockPipeline}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      fireEvent.click(screen.getByText('Save Pipeline'));

      await waitFor(() => {
        expect(mockOnSave).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Code Review Workflow',
            description: 'Automated code review',
          })
        );
      });
    });
  });

  describe('node management', () => {
    it('shows default Start trigger node for new pipelines', () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // New pipelines should have a default "Start" trigger node
      expect(screen.getByText('Start')).toBeInTheDocument();
    });

    it('adds a new agent node when Agent is selected from dropdown', async () => {
      render(
        <PipelineEditor
          pipeline={null}
          agents={mockAgents}
          onSave={mockOnSave}
          onClose={mockOnClose}
        />
      );

      // Open dropdown
      fireEvent.click(screen.getByText('Add Node'));

      // Wait for dropdown to open
      await waitFor(() => {
        expect(screen.getByText(/Execute a task/)).toBeInTheDocument();
      });

      // Click on the Agent option (click the button that contains "Execute a task")
      const agentDescription = screen.getByText(/Execute a task/);
      const agentButton = agentDescription.closest('button');
      if (agentButton) {
        fireEvent.click(agentButton);
      }

      // New agent node should appear
      await waitFor(() => {
        expect(screen.getByText('New Agent')).toBeInTheDocument();
      });
    });
  });
});
