import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '../test/test-utils';
import Pipelines from './Pipelines';
import { pipelines as pipelinesApi, agents as agentsApi } from '../services/api';

// Mock the API
vi.mock('../services/api', () => ({
  pipelines: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    toggle: vi.fn(),
    run: vi.fn(),
    getRuns: vi.fn(),
  },
  agents: {
    list: vi.fn(),
  },
}));

const mockPipelines = [
  {
    id: 1,
    name: 'Code Review Workflow',
    description: 'Automated code review with multiple agents',
    status: 'active' as const,
    nodes: [
      { id: 'n1', type: 'trigger' as const, name: 'PR Created', config: {}, position: { x: 50, y: 100 } },
      { id: 'n2', type: 'agent' as const, name: 'Sophie - Review', config: { agent_id: 1 }, position: { x: 250, y: 100 } },
    ],
    edges: [{ id: 'e1', from: 'n1', to: 'n2' }],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-15T00:00:00Z',
    last_run: '2024-01-15T10:00:00Z',
    run_count: 25,
    success_count: 23,
    error_count: 2,
  },
  {
    id: 2,
    name: 'Daily Report',
    description: 'Generate daily reports',
    status: 'paused' as const,
    nodes: [
      { id: 'n1', type: 'trigger' as const, name: 'Schedule', config: {}, position: { x: 50, y: 100 } },
    ],
    edges: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-10T00:00:00Z',
    run_count: 10,
    success_count: 10,
    error_count: 0,
  },
];

const mockAgents = [
  {
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
  },
];

describe('Pipelines Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (pipelinesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      pipelines: mockPipelines,
      total: 2,
    });
    (agentsApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
      agents: mockAgents,
      total: 1,
    });
  });

  describe('rendering', () => {
    it('renders the page title', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Pipelines')).toBeInTheDocument();
      });
    });

    it('renders stats cards', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Total Pipelines')).toBeInTheDocument();
      });
    });

    it('renders pipeline cards', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Code Review Workflow')).toBeInTheDocument();
        expect(screen.getByText('Daily Report')).toBeInTheDocument();
      });
    });

    it('renders filter buttons', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('All')).toBeInTheDocument();
      });
    });

    it('renders New Pipeline button', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('New Pipeline')).toBeInTheDocument();
      });
    });
  });

  describe('demo data fallback', () => {
    it('shows demo banner when API returns empty', async () => {
      (pipelinesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
        pipelines: [],
        total: 0,
      });

      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Demo Mode')).toBeInTheDocument();
      });
    });

    it('shows demo pipelines when API returns empty', async () => {
      (pipelinesApi.list as ReturnType<typeof vi.fn>).mockResolvedValue({
        pipelines: [],
        total: 0,
      });

      render(<Pipelines />);

      // Demo pipelines should be displayed
      await waitFor(() => {
        // The demo data includes "Code Review Workflow"
        expect(screen.getByText(/Code Review Workflow/)).toBeInTheDocument();
      });
    });
  });

  describe('interactions', () => {
    it('opens pipeline editor when New Pipeline is clicked', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('New Pipeline')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('New Pipeline'));

      // Pipeline editor should be visible (shows default name input)
      await waitFor(() => {
        expect(screen.getByDisplayValue('New Pipeline')).toBeInTheDocument();
      });
    });

    it('runs a pipeline when Run Now is clicked', async () => {
      (pipelinesApi.run as ReturnType<typeof vi.fn>).mockResolvedValue({
        id: 1,
        pipeline_id: 1,
        status: 'pending',
        logs: [],
        duration_seconds: 0,
      });

      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Code Review Workflow')).toBeInTheDocument();
      });

      // Find and click Run Now button for the first (active) pipeline
      const runButtons = screen.getAllByText('Run Now');
      fireEvent.click(runButtons[0]);

      await waitFor(() => {
        expect(pipelinesApi.run).toHaveBeenCalledWith(1);
      });
    });
  });

  describe('error handling', () => {
    it('shows error state when API fails', async () => {
      (pipelinesApi.list as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed to fetch')
      );

      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Failed to load pipelines')).toBeInTheDocument();
      });
    });

    it('shows retry button on error', async () => {
      (pipelinesApi.list as ReturnType<typeof vi.fn>).mockRejectedValue(
        new Error('Failed')
      );

      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });
  });

  describe('pipeline card display', () => {
    it('shows pipeline status badge', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('active')).toBeInTheDocument();
        expect(screen.getByText('paused')).toBeInTheDocument();
      });
    });

    it('shows run statistics', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        // First pipeline has "25 runs"
        expect(screen.getByText(/25/)).toBeInTheDocument();
      });
    });

    it('shows node preview in pipeline card', async () => {
      render(<Pipelines />);

      await waitFor(() => {
        expect(screen.getByText('PR Created')).toBeInTheDocument();
        expect(screen.getByText('Sophie - Review')).toBeInTheDocument();
      });
    });
  });
});
