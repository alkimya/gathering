// Pipeline Editor - Visual workflow builder component

import { useState, useCallback, useEffect } from 'react';
import {
  X,
  Save,
  Plus,
  Trash2,
  Bot,
  Zap,
  Clock,
  GitBranch,
  Play,
  Copy,
  ArrowRight,
  ChevronDown,
  AlertCircle,
  Check,
  Link2,
  Unlink,
} from 'lucide-react';
import type {
  Pipeline,
  PipelineNode,
  PipelineEdge,
  PipelineNodeType,
  PipelineNodeConfig,
  Agent,
} from '../types';

interface PipelineEditorProps {
  pipeline: Pipeline | null;
  agents: Agent[];
  onSave: (pipeline: Partial<Pipeline>) => Promise<void>;
  onClose: () => void;
  isNew?: boolean;
}

// Node type configuration with visual styling
const nodeTypes: Record<PipelineNodeType, {
  label: string;
  icon: React.ReactNode;
  color: string;
  bg: string;
  border: string;
  description: string;
}> = {
  trigger: {
    label: 'Trigger',
    icon: <Zap className="w-4 h-4" />,
    color: 'text-amber-400',
    bg: 'bg-amber-500/20',
    border: 'border-amber-500/30',
    description: 'Start the pipeline on event or schedule',
  },
  agent: {
    label: 'Agent',
    icon: <Bot className="w-4 h-4" />,
    color: 'text-purple-400',
    bg: 'bg-purple-500/20',
    border: 'border-purple-500/30',
    description: 'Execute a task with an AI agent',
  },
  condition: {
    label: 'Condition',
    icon: <GitBranch className="w-4 h-4" />,
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/20',
    border: 'border-cyan-500/30',
    description: 'Branch based on a condition',
  },
  action: {
    label: 'Action',
    icon: <Play className="w-4 h-4" />,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/30',
    description: 'Execute an action (webhook, notification)',
  },
  parallel: {
    label: 'Parallel',
    icon: <Copy className="w-4 h-4" />,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20',
    border: 'border-blue-500/30',
    description: 'Run multiple nodes in parallel',
  },
  delay: {
    label: 'Delay',
    icon: <Clock className="w-4 h-4" />,
    color: 'text-zinc-400',
    bg: 'bg-zinc-500/20',
    border: 'border-zinc-500/30',
    description: 'Wait for a specified duration',
  },
};

// Trigger type options
const triggerTypes = [
  { value: 'manual', label: 'Manual', description: 'Triggered manually via dashboard or API' },
  { value: 'webhook', label: 'Webhook', description: 'Triggered by incoming HTTP request' },
  { value: 'schedule', label: 'Schedule', description: 'Triggered on a cron schedule' },
  { value: 'event', label: 'Event', description: 'Triggered by a system event' },
];

// Action type options
const actionTypes = [
  { value: 'notification', label: 'Send Notification', description: 'Send email or Slack message' },
  { value: 'webhook', label: 'Call Webhook', description: 'Make HTTP request to URL' },
  { value: 'api_call', label: 'API Call', description: 'Call internal API endpoint' },
  { value: 'script', label: 'Run Script', description: 'Execute a script or command' },
];

// Generate unique node ID
function generateNodeId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Node configuration panel component
function NodeConfigPanel({
  node,
  agents,
  onUpdate,
  onDelete,
  onClose,
}: {
  node: PipelineNode;
  agents: Agent[];
  onUpdate: (updates: Partial<PipelineNode>) => void;
  onDelete: () => void;
  onClose: () => void;
}) {
  const typeConfig = nodeTypes[node.type];
  const [localName, setLocalName] = useState(node.name);
  const [localConfig, setLocalConfig] = useState<PipelineNodeConfig>(node.config);

  const handleSave = () => {
    onUpdate({ name: localName, config: localConfig });
    onClose();
  };

  const updateConfig = (key: keyof PipelineNodeConfig, value: unknown) => {
    setLocalConfig(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="w-80 glass-card rounded-xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className={`px-4 py-3 ${typeConfig.bg} border-b border-white/10 flex items-center justify-between`}>
        <div className="flex items-center gap-2">
          <span className={typeConfig.color}>{typeConfig.icon}</span>
          <span className="font-medium text-white">{typeConfig.label} Configuration</span>
        </div>
        <button onClick={onClose} className="text-zinc-400 hover:text-white">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
        {/* Node Name */}
        <div>
          <label className="block text-sm font-medium text-zinc-400 mb-1">Node Name</label>
          <input
            type="text"
            value={localName}
            onChange={(e) => setLocalName(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
            placeholder="Enter node name..."
          />
        </div>

        {/* Type-specific configuration */}
        {node.type === 'trigger' && (
          <>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Trigger Type</label>
              <select
                value={localConfig.trigger_type || 'manual'}
                onChange={(e) => updateConfig('trigger_type', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              >
                {triggerTypes.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <p className="text-xs text-zinc-500 mt-1">
                {triggerTypes.find(t => t.value === (localConfig.trigger_type || 'manual'))?.description}
              </p>
            </div>

            {localConfig.trigger_type === 'schedule' && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Cron Expression</label>
                <input
                  type="text"
                  value={localConfig.cron || ''}
                  onChange={(e) => updateConfig('cron', e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none font-mono"
                  placeholder="0 9 * * * (every day at 9am)"
                />
                <p className="text-xs text-zinc-500 mt-1">
                  Format: minute hour day month weekday
                </p>
              </div>
            )}

            {localConfig.trigger_type === 'event' && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Event Name</label>
                <input
                  type="text"
                  value={localConfig.event || ''}
                  onChange={(e) => updateConfig('event', e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  placeholder="e.g., issue.created, pr.merged"
                />
              </div>
            )}
          </>
        )}

        {node.type === 'agent' && (
          <>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Select Agent</label>
              <select
                value={localConfig.agent_id || ''}
                onChange={(e) => {
                  const agentId = Number(e.target.value);
                  const agent = agents.find(a => a.id === agentId);
                  updateConfig('agent_id', agentId);
                  if (agent) {
                    updateConfig('agent_name', agent.name);
                    setLocalName(`${agent.name} - Task`);
                  }
                }}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              >
                <option value="">Select an agent...</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} ({agent.role})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Task Type</label>
              <input
                type="text"
                value={localConfig.task || ''}
                onChange={(e) => updateConfig('task', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                placeholder="e.g., code_review, analyze, summarize"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Task Prompt</label>
              <textarea
                value={localConfig.task_prompt || ''}
                onChange={(e) => updateConfig('task_prompt', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none resize-none"
                rows={3}
                placeholder="Describe what the agent should do..."
              />
            </div>
          </>
        )}

        {node.type === 'condition' && (
          <>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Condition Type</label>
              <select
                value={localConfig.condition_type || 'expression'}
                onChange={(e) => updateConfig('condition_type', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              >
                <option value="expression">Expression</option>
                <option value="output_check">Check Previous Output</option>
                <option value="status_check">Check Status</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Condition</label>
              <input
                type="text"
                value={localConfig.condition || ''}
                onChange={(e) => updateConfig('condition', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                placeholder="e.g., output.approved == true"
              />
              <p className="text-xs text-zinc-500 mt-1">
                Use output.* to access previous node output
              </p>
            </div>
          </>
        )}

        {node.type === 'action' && (
          <>
            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Action Type</label>
              <select
                value={localConfig.action_type || 'notification'}
                onChange={(e) => updateConfig('action_type', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              >
                {actionTypes.map(a => (
                  <option key={a.value} value={a.value}>{a.label}</option>
                ))}
              </select>
            </div>

            {localConfig.action_type === 'notification' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1">Channel</label>
                  <select
                    value={localConfig.channel || 'email'}
                    onChange={(e) => updateConfig('channel', e.target.value)}
                    className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  >
                    <option value="email">Email</option>
                    <option value="slack">Slack</option>
                    <option value="webhook">Webhook</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1">Recipients (comma-separated)</label>
                  <input
                    type="text"
                    value={(localConfig.recipients || []).join(', ')}
                    onChange={(e) => updateConfig('recipients', e.target.value.split(',').map(r => r.trim()).filter(Boolean))}
                    className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                    placeholder="team@example.com, user@example.com"
                  />
                </div>
              </>
            )}

            {localConfig.action_type === 'webhook' && (
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1">Webhook URL</label>
                <input
                  type="text"
                  value={localConfig.webhook_url || ''}
                  onChange={(e) => updateConfig('webhook_url', e.target.value)}
                  className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  placeholder="https://..."
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-zinc-400 mb-1">Action Name</label>
              <input
                type="text"
                value={localConfig.action || ''}
                onChange={(e) => updateConfig('action', e.target.value)}
                className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                placeholder="e.g., send_alert, merge_pr"
              />
            </div>
          </>
        )}

        {node.type === 'delay' && (
          <div>
            <label className="block text-sm font-medium text-zinc-400 mb-1">Delay (seconds)</label>
            <input
              type="number"
              value={localConfig.delay_seconds || 60}
              onChange={(e) => updateConfig('delay_seconds', Number(e.target.value))}
              className="w-full px-3 py-2 bg-zinc-800/50 border border-white/10 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              min={1}
            />
            <p className="text-xs text-zinc-500 mt-1">
              Pipeline will pause for this duration
            </p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-white/10 flex items-center justify-between gap-2">
        <button
          onClick={onDelete}
          className="flex items-center gap-1 px-3 py-1.5 text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
          Delete
        </button>
        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-zinc-400 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="flex items-center gap-1 px-3 py-1.5 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-lg transition-colors"
          >
            <Check className="w-4 h-4" />
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

// Visual node component
function NodeCard({
  node,
  isSelected,
  isConnecting,
  canConnect,
  onClick,
  onStartConnect,
  onConnect,
}: {
  node: PipelineNode;
  isSelected: boolean;
  isConnecting: boolean;
  canConnect: boolean;
  onClick: () => void;
  onStartConnect: () => void;
  onConnect: () => void;
}) {
  const typeConfig = nodeTypes[node.type];

  return (
    <div
      className={`
        relative p-4 rounded-xl border-2 cursor-pointer transition-all
        ${typeConfig.bg} ${isSelected ? 'border-purple-500 ring-2 ring-purple-500/30' : typeConfig.border}
        ${canConnect ? 'ring-2 ring-emerald-500/50' : ''}
        hover:scale-[1.02]
      `}
      onClick={onClick}
    >
      {/* Node header */}
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${typeConfig.bg}`}>
          <span className={typeConfig.color}>{typeConfig.icon}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{node.name}</p>
          <p className="text-xs text-zinc-500">{typeConfig.label}</p>
        </div>
      </div>

      {/* Node config preview */}
      <div className="text-xs text-zinc-400 space-y-1">
        {node.type === 'trigger' && node.config.trigger_type && (
          <p className="flex items-center gap-1">
            <Zap className="w-3 h-3" />
            {node.config.trigger_type}
            {node.config.cron && `: ${node.config.cron}`}
          </p>
        )}
        {node.type === 'agent' && node.config.agent_name && (
          <p className="flex items-center gap-1">
            <Bot className="w-3 h-3" />
            {node.config.agent_name}
          </p>
        )}
        {node.type === 'condition' && node.config.condition && (
          <p className="flex items-center gap-1 truncate">
            <GitBranch className="w-3 h-3" />
            {node.config.condition}
          </p>
        )}
        {node.type === 'delay' && node.config.delay_seconds && (
          <p className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {node.config.delay_seconds}s
          </p>
        )}
      </div>

      {/* Connection button */}
      {!isConnecting && node.type !== 'action' && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onStartConnect();
          }}
          className="absolute -right-2 top-1/2 -translate-y-1/2 p-1 bg-zinc-700 hover:bg-purple-500 rounded-full border border-white/10 transition-colors"
          title="Connect to another node"
        >
          <Link2 className="w-3 h-3 text-white" />
        </button>
      )}

      {/* Connect target indicator */}
      {canConnect && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onConnect();
          }}
          className="absolute -left-2 top-1/2 -translate-y-1/2 p-1.5 bg-emerald-500 rounded-full border-2 border-emerald-400 animate-pulse"
          title="Connect here"
        >
          <ArrowRight className="w-3 h-3 text-white" />
        </button>
      )}
    </div>
  );
}

// Main Pipeline Editor component
export function PipelineEditor({
  pipeline,
  agents,
  onSave,
  onClose,
}: PipelineEditorProps) {
  const [name, setName] = useState(pipeline?.name || 'New Pipeline');
  const [description, setDescription] = useState(pipeline?.description || '');
  const [nodes, setNodes] = useState<PipelineNode[]>(
    pipeline?.nodes || [
      {
        id: generateNodeId(),
        type: 'trigger',
        name: 'Start',
        config: { trigger_type: 'manual' },
        position: { x: 0, y: 0 },
      },
    ]
  );
  const [edges, setEdges] = useState<PipelineEdge[]>(pipeline?.edges || []);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [connectingFromId, setConnectingFromId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddNode, setShowAddNode] = useState(false);

  const selectedNode = nodes.find(n => n.id === selectedNodeId);

  // Add a new node
  const addNode = useCallback((type: PipelineNodeType) => {
    const typeConfig = nodeTypes[type];
    const newNode: PipelineNode = {
      id: generateNodeId(),
      type,
      name: `New ${typeConfig.label}`,
      config: type === 'trigger' ? { trigger_type: 'manual' } : {},
      position: { x: nodes.length * 50, y: nodes.length * 50 },
    };
    setNodes(prev => [...prev, newNode]);
    setSelectedNodeId(newNode.id);
    setShowAddNode(false);
  }, [nodes.length]);

  // Update a node
  const updateNode = useCallback((nodeId: string, updates: Partial<PipelineNode>) => {
    setNodes(prev => prev.map(n =>
      n.id === nodeId ? { ...n, ...updates } : n
    ));
  }, []);

  // Delete a node
  const deleteNode = useCallback((nodeId: string) => {
    setNodes(prev => prev.filter(n => n.id !== nodeId));
    setEdges(prev => prev.filter(e => e.from !== nodeId && e.to !== nodeId));
    setSelectedNodeId(null);
  }, []);

  // Start connecting nodes
  const startConnect = useCallback((fromId: string) => {
    setConnectingFromId(fromId);
    setSelectedNodeId(null);
  }, []);

  // Complete connection
  const completeConnect = useCallback((toId: string) => {
    if (!connectingFromId || connectingFromId === toId) {
      setConnectingFromId(null);
      return;
    }

    // Check if edge already exists
    const exists = edges.some(e => e.from === connectingFromId && e.to === toId);
    if (!exists) {
      const newEdge: PipelineEdge = {
        id: `edge_${Date.now()}`,
        from: connectingFromId,
        to: toId,
      };
      setEdges(prev => [...prev, newEdge]);
    }
    setConnectingFromId(null);
  }, [connectingFromId, edges]);

  // Cancel connecting
  const cancelConnect = useCallback(() => {
    setConnectingFromId(null);
  }, []);

  // Remove edge
  const removeEdge = useCallback((edgeId: string) => {
    setEdges(prev => prev.filter(e => e.id !== edgeId));
  }, []);

  // Save pipeline
  const handleSave = async () => {
    if (!name.trim()) {
      setError('Pipeline name is required');
      return;
    }

    if (nodes.length === 0) {
      setError('Pipeline must have at least one node');
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await onSave({
        name: name.trim(),
        description: description.trim() || undefined,
        nodes,
        edges,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save pipeline');
    } finally {
      setSaving(false);
    }
  };

  // Get connected nodes for visualization
  const getNodeConnections = (nodeId: string) => {
    const incoming = edges.filter(e => e.to === nodeId);
    const outgoing = edges.filter(e => e.from === nodeId);
    return { incoming, outgoing };
  };

  // Cancel connecting on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (connectingFromId) {
          cancelConnect();
        } else if (selectedNodeId) {
          setSelectedNodeId(null);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [connectingFromId, selectedNodeId, cancelConnect]);

  return (
    <div className="fixed inset-0 z-50 flex bg-black/50 backdrop-blur-sm">
      {/* Main editor area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="h-16 px-6 border-b border-white/10 bg-[#11111b] flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="p-2 text-zinc-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
            <div>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-transparent text-xl font-bold text-white focus:outline-none border-b border-transparent hover:border-white/20 focus:border-purple-500"
                placeholder="Pipeline Name"
              />
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="block bg-transparent text-sm text-zinc-400 focus:outline-none border-b border-transparent hover:border-white/20 focus:border-purple-500 w-96"
                placeholder="Add description..."
              />
            </div>
          </div>

          <div className="flex items-center gap-3">
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:opacity-50 text-white rounded-xl transition-colors"
            >
              <Save className="w-4 h-4" />
              {saving ? 'Saving...' : 'Save Pipeline'}
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="h-12 px-6 border-b border-white/10 bg-[#16161e] flex items-center gap-4">
          <div className="relative">
            <button
              onClick={() => setShowAddNode(!showAddNode)}
              className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Node
              <ChevronDown className={`w-4 h-4 transition-transform ${showAddNode ? 'rotate-180' : ''}`} />
            </button>

            {showAddNode && (
              <div className="absolute top-full left-0 mt-2 w-64 glass-card rounded-xl border border-white/10 py-2 z-50">
                {Object.entries(nodeTypes).map(([type, config]) => (
                  <button
                    key={type}
                    onClick={() => addNode(type as PipelineNodeType)}
                    className="w-full px-4 py-2 text-left hover:bg-white/5 flex items-center gap-3"
                  >
                    <div className={`p-1.5 rounded-lg ${config.bg}`}>
                      <span className={config.color}>{config.icon}</span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{config.label}</p>
                      <p className="text-xs text-zinc-500">{config.description}</p>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {connectingFromId && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg">
              <Link2 className="w-4 h-4" />
              Click a node to connect
              <button
                onClick={cancelConnect}
                className="ml-2 text-zinc-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          <div className="flex-1" />

          <span className="text-sm text-zinc-500">
            {nodes.length} nodes, {edges.length} connections
          </span>
        </div>

        {/* Canvas */}
        <div
          className="flex-1 p-8 overflow-auto bg-[#0a0a0f]"
          onClick={() => {
            if (!connectingFromId) {
              setSelectedNodeId(null);
            }
          }}
        >
          {/* Nodes grid */}
          <div className="flex flex-wrap gap-4">
            {nodes.map((node) => {
              const connections = getNodeConnections(node.id);
              const canBeTarget = connectingFromId !== null && connectingFromId !== node.id;

              return (
                <div key={node.id} className="relative">
                  <NodeCard
                    node={node}
                    isSelected={selectedNodeId === node.id}
                    isConnecting={connectingFromId === node.id}
                    canConnect={canBeTarget}
                    onClick={() => {
                      if (connectingFromId) {
                        completeConnect(node.id);
                      } else {
                        setSelectedNodeId(node.id);
                      }
                    }}
                    onStartConnect={() => startConnect(node.id)}
                    onConnect={() => completeConnect(node.id)}
                  />

                  {/* Connection indicators */}
                  {connections.incoming.length > 0 && (
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs text-zinc-500">
                      {connections.incoming.length} in
                    </div>
                  )}
                  {connections.outgoing.length > 0 && (
                    <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 text-xs text-zinc-500">
                      {connections.outgoing.length} out
                    </div>
                  )}
                </div>
              );
            })}

            {nodes.length === 0 && (
              <div className="text-center py-20 w-full">
                <GitBranch className="w-12 h-12 text-zinc-600 mx-auto mb-4" />
                <p className="text-zinc-400 mb-4">No nodes yet. Add your first node to get started.</p>
                <button
                  onClick={() => addNode('trigger')}
                  className="px-4 py-2 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-xl transition-colors"
                >
                  Add Trigger
                </button>
              </div>
            )}
          </div>

          {/* Edges list */}
          {edges.length > 0 && (
            <div className="mt-8 pt-8 border-t border-white/10">
              <h3 className="text-sm font-medium text-zinc-400 mb-4">Connections</h3>
              <div className="flex flex-wrap gap-2">
                {edges.map((edge) => {
                  const fromNode = nodes.find(n => n.id === edge.from);
                  const toNode = nodes.find(n => n.id === edge.to);
                  if (!fromNode || !toNode) return null;

                  return (
                    <div
                      key={edge.id}
                      className="flex items-center gap-2 px-3 py-2 bg-zinc-800/50 rounded-lg border border-white/5"
                    >
                      <span className="text-sm text-zinc-300">{fromNode.name}</span>
                      <ArrowRight className="w-4 h-4 text-zinc-500" />
                      <span className="text-sm text-zinc-300">{toNode.name}</span>
                      {edge.condition && (
                        <span className="text-xs px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded">
                          {edge.condition}
                        </span>
                      )}
                      <button
                        onClick={() => removeEdge(edge.id)}
                        className="p-1 text-zinc-500 hover:text-red-400 transition-colors"
                        title="Remove connection"
                      >
                        <Unlink className="w-3 h-3" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Configuration panel */}
      {selectedNode && (
        <div className="w-80 border-l border-white/10 bg-[#11111b]">
          <NodeConfigPanel
            node={selectedNode}
            agents={agents}
            onUpdate={(updates) => updateNode(selectedNode.id, updates)}
            onDelete={() => deleteNode(selectedNode.id)}
            onClose={() => setSelectedNodeId(null)}
          />
        </div>
      )}
    </div>
  );
}

export default PipelineEditor;
