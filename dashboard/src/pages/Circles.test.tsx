import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/test-utils';
import Circles from './Circles';
import { circles as circlesApi, agents as agentsApi } from '../services/api';

// Mock the API modules
vi.mock('../services/api', () => ({
  circles: {
    list: vi.fn(),
    create: vi.fn(),
    addAgent: vi.fn(),
    delete: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    getTasks: vi.fn(),
    getMetrics: vi.fn(),
    createTask: vi.fn(),
  },
  agents: {
    list: vi.fn(),
  },
}));

describe('Circles Page', () => {
  // Use non-demo circle IDs (not starting with 'c' + single digit) to enable full functionality
  const mockCircles = [
    {
      id: 'circle-1',
      name: 'dev-team',
      status: 'running' as const,
      agent_count: 2,
      active_tasks: 5,
      task_count: 10,
      require_review: true,
      auto_route: true,
      created_at: '2024-01-01T00:00:00Z',
      started_at: '2024-01-01T00:00:00Z',
    },
    {
      id: 'circle-2',
      name: 'code-review',
      status: 'stopped' as const,
      agent_count: 1,
      active_tasks: 0,
      task_count: 3,
      require_review: false,
      auto_route: false,
      created_at: '2024-01-01T00:00:00Z',
      started_at: null,
    },
  ];

  const mockAgents = [
    {
      id: 1,
      name: 'Sophie',
      role: 'Developer',
      provider: 'anthropic',
      model: 'claude-3',
      status: 'idle' as const,
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
      status: 'idle' as const,
      competencies: ['code_review', 'security'],
      can_review: ['security'],
      current_task: null,
      created_at: '2024-01-01T00:00:00Z',
      last_activity: null,
    },
  ];

  const mockTasks = [
    {
      id: 1,
      title: 'Implement auth',
      description: 'Add authentication',
      status: 'in_progress' as const,
      priority: 'high' as const,
      assigned_agent_id: 1,
      assigned_agent_name: 'Sophie',
      reviewer_id: null,
      reviewer_name: null,
      created_at: '2024-01-01T00:00:00Z',
      started_at: '2024-01-01T00:00:00Z',
      completed_at: null,
      result: null,
    },
  ];

  const mockMetrics = {
    tasks_completed: 10,
    tasks_in_progress: 2,
    conflicts_resolved: 1,
    uptime_seconds: 3600,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (circlesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      circles: mockCircles,
      total: mockCircles.length,
    });
    (circlesApi.getTasks as ReturnType<typeof vi.fn>).mockResolvedValue({
      tasks: mockTasks,
      total: mockTasks.length,
    });
    (circlesApi.getMetrics as ReturnType<typeof vi.fn>).mockResolvedValue(mockMetrics);
    (agentsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      agents: mockAgents,
    });
  });

  describe('rendering', () => {
    it('renders the page header', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('Circles')).toBeInTheDocument();
      });
    });

    it('renders circles from API or demo data', async () => {
      render(<Circles />);

      // Wait for the page to render - will show either API data or demo data
      await waitFor(() => {
        // Both API mock and demo have 'dev-team' circle
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });
    });

    it('shows circle status indicators', async () => {
      render(<Circles />);

      await waitFor(() => {
        // At least one running circle should exist
        expect(screen.getByText('running')).toBeInTheDocument();
      });
    });

    it('shows agent count for circles', async () => {
      render(<Circles />);

      await waitFor(() => {
        // Demo data has '2 agents' for dev-team
        expect(screen.getByText('2 agents')).toBeInTheDocument();
      });
    });
  });

  describe('circle selection', () => {
    it('shows circle detail when a circle is selected', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });

      // Click on the dev-team circle
      fireEvent.click(screen.getByText('dev-team'));

      // Detail view should show metrics
      await waitFor(() => {
        expect(screen.getByText('Completed')).toBeInTheDocument();
        expect(screen.getByText('In Progress')).toBeInTheDocument();
      });
    });
  });

  describe('create circle modal', () => {
    it('opens create modal when + button is clicked', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('Circles')).toBeInTheDocument();
      });

      // Find and click the + button
      const addButtons = screen.getAllByRole('button');
      const addButton = addButtons.find(btn => btn.querySelector('.lucide-plus'));
      if (addButton) {
        fireEvent.click(addButton);
      }

      // Modal should be visible
      await waitFor(() => {
        expect(screen.getByText('Create Circle')).toBeInTheDocument();
      });
    });

    it('shows agent selection in create modal', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('Circles')).toBeInTheDocument();
      });

      // Open modal
      const addButtons = screen.getAllByRole('button');
      const addButton = addButtons.find(btn => btn.querySelector('.lucide-plus'));
      if (addButton) {
        fireEvent.click(addButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Create Circle')).toBeInTheDocument();
      });

      // Agent names should appear in the modal
      expect(screen.getByText('Sophie')).toBeInTheDocument();
      expect(screen.getByText('Olivia')).toBeInTheDocument();
    });

    it('shows Require Review and Auto Route options', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('Circles')).toBeInTheDocument();
      });

      // Open modal
      const addButtons = screen.getAllByRole('button');
      const addButton = addButtons.find(btn => btn.querySelector('.lucide-plus'));
      if (addButton) {
        fireEvent.click(addButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Require Review')).toBeInTheDocument();
        expect(screen.getByText('Auto Route')).toBeInTheDocument();
      });
    });

    it('creates circle with selected agents', async () => {
      (circlesApi.create as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 'c3',
        name: 'new-circle',
        status: 'stopped',
        agent_count: 0,
        agents: [],
      });
      (circlesApi.addAgent as ReturnType<typeof vi.fn>).mockResolvedValue({ status: 'added' });

      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('Circles')).toBeInTheDocument();
      });

      // Open modal
      const addButtons = screen.getAllByRole('button');
      const addButton = addButtons.find(btn => btn.querySelector('.lucide-plus'));
      if (addButton) {
        fireEvent.click(addButton);
      }

      await waitFor(() => {
        expect(screen.getByText('Create Circle')).toBeInTheDocument();
      });

      // Enter circle name
      const nameInput = screen.getByPlaceholderText('my-circle');
      fireEvent.change(nameInput, { target: { value: 'new-circle' } });

      // Select an agent (Sophie)
      const sophieCheckbox = screen.getByRole('checkbox', { name: /Sophie/i });
      fireEvent.click(sophieCheckbox);

      // Submit
      fireEvent.click(screen.getByText('Create'));

      await waitFor(() => {
        expect(circlesApi.create).toHaveBeenCalledWith({
          name: 'new-circle',
          require_review: true,
          auto_route: true,
        });
      });

      // Should add the selected agent
      await waitFor(() => {
        expect(circlesApi.addAgent).toHaveBeenCalledWith('new-circle', expect.objectContaining({
          agent_id: 1,
          agent_name: 'Sophie',
        }));
      });
    });
  });

  describe('task creation', () => {
    it('shows required skills button in task form', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });

      // Select a circle
      fireEvent.click(screen.getByText('dev-team'));

      await waitFor(() => {
        expect(screen.getByText('Required skills')).toBeInTheDocument();
      });
    });

    it('expands competency selector when clicked', async () => {
      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('dev-team'));

      await waitFor(() => {
        expect(screen.getByText('Required skills')).toBeInTheDocument();
      });

      // Click to expand
      fireEvent.click(screen.getByText('Required skills'));

      // Competencies should appear
      await waitFor(() => {
        expect(screen.getByText('python')).toBeInTheDocument();
        expect(screen.getByText('typescript')).toBeInTheDocument();
        expect(screen.getByText('testing')).toBeInTheDocument();
      });
    });

    it('creates task with selected competencies', async () => {
      (circlesApi.createTask as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 2,
        title: 'New Task',
        description: 'Task description',
        status: 'pending',
        priority: 'high',
        assigned_agent_id: 1,
        assigned_agent_name: 'Sophie',
      });

      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('dev-team'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Task title...')).toBeInTheDocument();
      });

      // Enter task title
      const titleInput = screen.getByPlaceholderText('Task title...');
      fireEvent.change(titleInput, { target: { value: 'New Task' } });

      // Expand and select competencies
      fireEvent.click(screen.getByText('Required skills'));

      await waitFor(() => {
        expect(screen.getByText('python')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('python'));
      fireEvent.click(screen.getByText('testing'));

      // Submit the form
      const form = titleInput.closest('form');
      if (form) {
        fireEvent.submit(form);
      }

      await waitFor(() => {
        expect(circlesApi.createTask).toHaveBeenCalledWith('dev-team', {
          title: 'New Task',
          description: '',
          required_competencies: ['python', 'testing'],
          priority: 'medium',
        });
      });
    });

    it('shows success feedback after task creation', async () => {
      (circlesApi.createTask as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 2,
        title: 'New Task',
        status: 'pending',
        assigned_agent_name: 'Sophie',
      });

      render(<Circles />);

      await waitFor(() => {
        expect(screen.getByText('dev-team')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('dev-team'));

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Task title...')).toBeInTheDocument();
      });

      // Enter and submit task
      const titleInput = screen.getByPlaceholderText('Task title...');
      fireEvent.change(titleInput, { target: { value: 'Quick Task' } });

      const form = titleInput.closest('form');
      if (form) {
        fireEvent.submit(form);
      }

      // Success message should appear
      await waitFor(() => {
        expect(screen.getByText('Task created!')).toBeInTheDocument();
      });
    });
  });
});
