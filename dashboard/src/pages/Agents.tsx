// Agents management page with Web3 dark theme

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot,
  Plus,
  Trash2,
  MessageSquare,
  Brain,
  Sparkles,
  X,
  Settings,
  Cpu,
  Server,
  Thermometer,
  FileText,
  Tag,
  Languages,
  Quote,
  Users,
  User,
  LayoutDashboard,
} from 'lucide-react';
import { agents, models, providers, personas } from '../services/api';
import { StreamingChatPanel } from '../components/StreamingChatPanel';
import type { Agent } from '../types';

function AgentCard({
  agent,
  isSelected,
  onSelect,
  onDelete,
  onEdit,
}: {
  agent: Agent;
  isSelected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onEdit: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`p-3 rounded-xl cursor-pointer transition-all glass-card-hover ${
        isSelected
          ? 'glass-card border-purple-500/50 glow-purple'
          : 'glass-card'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${
              agent.status === 'busy'
                ? 'bg-gradient-to-br from-amber-500 to-orange-500'
                : 'bg-gradient-to-br from-emerald-500 to-teal-500'
            }`}>
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-[#11111b] ${
              agent.status === 'busy' ? 'bg-amber-500' : 'bg-emerald-500'
            }`} />
          </div>
          <div>
            <h3 className="font-semibold text-white text-sm">{agent.name}</h3>
            <p className="text-xs text-zinc-500">{agent.role}</p>
          </div>
        </div>
        <div className="flex items-center gap-0.5">
          <Link
            to={`/agents/${agent.id}`}
            onClick={(e) => e.stopPropagation()}
            className="p-1 text-zinc-500 hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-all"
            title="Agent Dashboard"
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
          </Link>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="p-1 text-zinc-500 hover:text-cyan-400 hover:bg-cyan-500/10 rounded-lg transition-all"
            title="Agent Settings"
          >
            <Settings className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
            title="Delete Agent"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
        <div className="flex items-center gap-1">
          <Brain className="w-3 h-3 text-purple-400" />
          <span>{agent.memory_count ?? 0}</span>
        </div>
        <div className="flex items-center gap-1">
          <MessageSquare className="w-3 h-3 text-cyan-400" />
          <span>{agent.message_count ?? 0}</span>
        </div>
      </div>
    </div>
  );
}


function CreateAgentModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  // Creation mode: from persona or custom
  const [mode, setMode] = useState<'persona' | 'custom'>('persona');

  // Persona mode
  const [selectedPersonaId, setSelectedPersonaId] = useState<number | null>(null);

  // Custom mode fields
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [basePrompt, setBasePrompt] = useState('');
  const [traits, setTraits] = useState('');
  const [specializations, setSpecializations] = useState('');
  const [communicationStyle, setCommunicationStyle] = useState('balanced');
  const [languages, setLanguages] = useState('');
  const [motto, setMotto] = useState('');

  // Common fields
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState<number | undefined>(undefined);

  const queryClient = useQueryClient();

  // Fetch providers, models, and personas
  const { data: providersData } = useQuery({
    queryKey: ['providers'],
    queryFn: providers.list,
    enabled: isOpen,
  });

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => models.list(),
    enabled: isOpen,
  });

  const { data: personasData } = useQuery({
    queryKey: ['personas'],
    queryFn: personas.list,
    enabled: isOpen,
  });

  // Filter models by selected provider
  const filteredModels = modelsData?.models.filter(
    (m) => !selectedProviderId || m.provider_id === selectedProviderId
  ) || [];

  // When persona is selected, update model defaults
  useEffect(() => {
    if (mode === 'persona' && selectedPersonaId && personasData?.personas) {
      const persona = personasData.personas.find((p) => p.id === selectedPersonaId);
      if (persona?.default_model_id) {
        setSelectedModelId(persona.default_model_id);
        // Find and set the provider
        const model = modelsData?.models.find((m) => m.id === persona.default_model_id);
        if (model) {
          setSelectedProviderId(model.provider_id);
        }
      }
    }
  }, [selectedPersonaId, personasData, modelsData, mode]);

  const createMutation = useMutation({
    mutationFn: async () => {
      if (mode === 'persona' && selectedPersonaId) {
        // Create from persona
        return agents.create({
          persona: { name: '' }, // Will use persona name
          config: {
            persona_id: selectedPersonaId,
            model_id: selectedModelId,
            temperature,
            max_tokens: maxTokens,
          } as any,
        });
      } else {
        // Create custom agent with new persona
        return agents.create({
          persona: {
            name,
            role,
            base_prompt: basePrompt,
            traits: traits.split(',').map((t) => t.trim()).filter(Boolean),
            specializations: specializations.split(',').map((s) => s.trim()).filter(Boolean),
            communication_style: communicationStyle,
            languages: languages.split(',').map((l) => l.trim()).filter(Boolean),
            motto,
          } as any,
          config: {
            model_id: selectedModelId,
            temperature,
            max_tokens: maxTokens,
          } as any,
        });
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      onClose();
      resetForm();
    },
  });

  const resetForm = () => {
    setMode('persona');
    setSelectedPersonaId(null);
    setName('');
    setRole('');
    setBasePrompt('');
    setTraits('');
    setSpecializations('');
    setCommunicationStyle('balanced');
    setLanguages('');
    setMotto('');
    setSelectedProviderId(null);
    setSelectedModelId(null);
    setTemperature(0.7);
    setMaxTokens(undefined);
  };

  if (!isOpen) return null;

  const selectedPersona = personasData?.personas.find((p) => p.id === selectedPersonaId);

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-agent-title"
    >
      <div className="glass-card rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center glow-purple">
              <Plus className="w-5 h-5 text-white" />
            </div>
            <h2 id="create-agent-title" className="text-xl font-bold text-white">Create Agent</h2>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode tabs */}
        <div className="flex gap-2 mb-6 p-1 glass-card rounded-xl">
          <button
            type="button"
            onClick={() => setMode('persona')}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'persona'
                ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <Users className="w-4 h-4" />
            From Persona
          </button>
          <button
            type="button"
            onClick={() => setMode('custom')}
            className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
              mode === 'custom'
                ? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <Settings className="w-4 h-4" />
            Custom Agent
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="space-y-5"
        >
          {mode === 'persona' ? (
            <>
              {/* Persona selection */}
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <User className="w-4 h-4 inline mr-2" />
                  Select Persona
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {personasData?.personas.map((persona) => (
                    <button
                      key={persona.id}
                      type="button"
                      onClick={() => setSelectedPersonaId(persona.id)}
                      className={`p-4 rounded-xl text-left transition-all ${
                        selectedPersonaId === persona.id
                          ? 'glass-card border-purple-500/50 glow-purple'
                          : 'glass-card hover:border-white/20'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                          <Bot className="w-5 h-5 text-white" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-white truncate">{persona.display_name}</p>
                          <p className="text-xs text-zinc-500 truncate">{persona.role}</p>
                        </div>
                      </div>
                      {persona.motto && (
                        <p className="mt-2 text-xs text-zinc-400 italic line-clamp-1">"{persona.motto}"</p>
                      )}
                    </button>
                  ))}
                </div>
                {personasData?.personas.length === 0 && (
                  <div className="text-center py-8 text-zinc-500">
                    No personas available. Create a custom agent instead.
                  </div>
                )}
              </div>

              {/* Selected persona info */}
              {selectedPersona && (
                <div className="p-4 glass-card rounded-xl space-y-2">
                  <h4 className="text-sm font-medium text-zinc-300">Persona Details</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-zinc-500">Role:</span>
                      <span className="ml-2 text-white">{selectedPersona.role}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500">Style:</span>
                      <span className="ml-2 text-white capitalize">{selectedPersona.communication_style}</span>
                    </div>
                  </div>
                  {selectedPersona.specializations?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {selectedPersona.specializations.slice(0, 5).map((spec, i) => (
                        <span key={i} className="badge px-2 py-0.5 text-xs rounded-full">
                          {spec}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              {/* Custom agent fields */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <User className="w-4 h-4 inline mr-2" />
                    Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Agent name"
                    required={mode === 'custom'}
                    className="w-full px-4 py-3 input-glass rounded-xl"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <Tag className="w-4 h-4 inline mr-2" />
                    Role
                  </label>
                  <input
                    type="text"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g., Senior Developer"
                    required={mode === 'custom'}
                    className="w-full px-4 py-3 input-glass rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <FileText className="w-4 h-4 inline mr-2" />
                  Base Prompt / System Instructions
                </label>
                <textarea
                  value={basePrompt}
                  onChange={(e) => setBasePrompt(e.target.value)}
                  placeholder="Describe the agent's personality, expertise, and how they should behave..."
                  rows={4}
                  className="w-full px-4 py-3 input-glass rounded-xl resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <Sparkles className="w-4 h-4 inline mr-2" />
                    Traits (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={traits}
                    onChange={(e) => setTraits(e.target.value)}
                    placeholder="analytical, creative, thorough"
                    className="w-full px-4 py-3 input-glass rounded-xl"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <Brain className="w-4 h-4 inline mr-2" />
                    Specializations (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={specializations}
                    onChange={(e) => setSpecializations(e.target.value)}
                    placeholder="python, architecture, testing"
                    className="w-full px-4 py-3 input-glass rounded-xl"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <MessageSquare className="w-4 h-4 inline mr-2" />
                    Communication Style
                  </label>
                  <select
                    value={communicationStyle}
                    onChange={(e) => setCommunicationStyle(e.target.value)}
                    className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
                  >
                    <option value="formal">Formal</option>
                    <option value="balanced">Balanced</option>
                    <option value="technical">Technical</option>
                    <option value="friendly">Friendly</option>
                    <option value="concise">Concise</option>
                    <option value="detailed">Detailed</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-300 mb-2">
                    <Languages className="w-4 h-4 inline mr-2" />
                    Languages (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={languages}
                    onChange={(e) => setLanguages(e.target.value)}
                    placeholder="French, English"
                    className="w-full px-4 py-3 input-glass rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Quote className="w-4 h-4 inline mr-2" />
                  Motto
                </label>
                <input
                  type="text"
                  value={motto}
                  onChange={(e) => setMotto(e.target.value)}
                  placeholder="A guiding principle or catchphrase"
                  className="w-full px-4 py-3 input-glass rounded-xl"
                />
              </div>
            </>
          )}

          {/* Common: Model selection */}
          <div className="border-t border-white/5 pt-5 space-y-4">
            <h3 className="text-sm font-medium text-zinc-300 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              Model Configuration
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Server className="w-4 h-4 inline mr-2" />
                  Provider
                </label>
                <select
                  value={selectedProviderId || ''}
                  onChange={(e) => {
                    setSelectedProviderId(e.target.value ? Number(e.target.value) : null);
                    setSelectedModelId(null);
                  }}
                  className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
                >
                  <option value="">All providers</option>
                  {providersData?.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Cpu className="w-4 h-4 inline mr-2" />
                  Model
                </label>
                <select
                  value={selectedModelId || ''}
                  onChange={(e) => setSelectedModelId(e.target.value ? Number(e.target.value) : null)}
                  required
                  className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
                >
                  <option value="">Select model...</option>
                  {filteredModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.model_alias || m.model_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Thermometer className="w-4 h-4 inline mr-2" />
                  Temperature: {temperature.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-zinc-500 mt-1">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Max Tokens (optional)
                </label>
                <input
                  type="number"
                  value={maxTokens || ''}
                  onChange={(e) => setMaxTokens(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="Default from model"
                  className="w-full px-4 py-3 input-glass rounded-xl"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-all font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={
                createMutation.isPending ||
                !selectedModelId ||
                (mode === 'persona' && !selectedPersonaId) ||
                (mode === 'custom' && (!name || !role))
              }
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {createMutation.isPending ? 'Creating...' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditAgentModal({
  agent,
  isOpen,
  onClose,
}: {
  agent: Agent | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  // Form state - initialized from agent
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [basePrompt, setBasePrompt] = useState('');
  const [traits, setTraits] = useState('');
  const [specializations, setSpecializations] = useState('');
  const [communicationStyle, setCommunicationStyle] = useState('balanced');
  const [languages, setLanguages] = useState('');
  const [motto, setMotto] = useState('');
  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<number | null>(null);
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState<number | undefined>(undefined);

  const queryClient = useQueryClient();

  // Fetch full agent details from API
  const { data: agentDetails, isLoading: isLoadingDetails } = useQuery({
    queryKey: ['agent-detail', agent?.id],
    queryFn: () => agent ? agents.get(agent.id) : null,
    enabled: isOpen && !!agent,
  });

  // Fetch providers and models
  const { data: providersData } = useQuery({
    queryKey: ['providers'],
    queryFn: providers.list,
    enabled: isOpen,
  });

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: () => models.list(),
    enabled: isOpen,
  });

  // Filter models by selected provider
  const filteredModels = modelsData?.models.filter(
    (m) => !selectedProviderId || m.provider_id === selectedProviderId
  ) || [];

  // Initialize form when agent details load
  useEffect(() => {
    if (agentDetails && isOpen) {
      // Support flat structure from DB (agent.agents_full view)
      const agentAny = agentDetails as any;
      setName(agentAny.persona_name || agentAny.name || '');
      setRole(agentAny.persona_role || agentAny.role || '');
      // Use system_prompt from agents_full view (COALESCE of full_prompt and base_prompt)
      setBasePrompt(agentAny.system_prompt || agentAny.base_prompt || '');
      setTraits(Array.isArray(agentAny.traits) ? agentAny.traits.join(', ') : '');
      setSpecializations(Array.isArray(agentAny.specializations) ? agentAny.specializations.join(', ') : '');
      setCommunicationStyle(agentAny.communication_style || 'balanced');
      setLanguages(Array.isArray(agentAny.languages) ? agentAny.languages.join(', ') : '');
      setMotto(agentAny.motto || '');

      // Find model/provider from agent - use model_id directly or search by model_alias
      if (agentAny.model_id) {
        setSelectedModelId(agentAny.model_id);
        // Find provider from model
        const model = modelsData?.models.find(m => m.id === agentAny.model_id);
        if (model) {
          setSelectedProviderId(model.provider_id);
        }
      } else if (agentAny.model_alias || agentAny.model) {
        const modelName = agentAny.model_alias || agentAny.model;
        const model = modelsData?.models.find(m =>
          m.model_name === modelName || m.model_alias === modelName
        );
        if (model) {
          setSelectedModelId(model.id);
          setSelectedProviderId(model.provider_id);
        }
      }

      setTemperature(agentAny.temperature ?? 0.7);
      setMaxTokens(agentAny.max_tokens);
    }
  }, [agentDetails, isOpen, modelsData]);

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!agent) return;
      return agents.update(agent.id, {
        persona: {
          name,
          role,
          base_prompt: basePrompt,
          traits: traits.split(',').map((t) => t.trim()).filter(Boolean),
          specializations: specializations.split(',').map((s) => s.trim()).filter(Boolean),
          communication_style: communicationStyle,
          languages: languages.split(',').map((l) => l.trim()).filter(Boolean),
          motto,
        } as any,
        config: {
          model_id: selectedModelId,
          temperature,
          max_tokens: maxTokens,
        } as any,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      onClose();
    },
  });

  if (!isOpen || !agent) return null;

  return (
    <div
      className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-agent-title"
    >
      <div className="glass-card rounded-2xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 id="edit-agent-title" className="text-xl font-bold text-white">Edit Agent</h2>
              <p className="text-sm text-zinc-500">{name || agent.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {isLoadingDetails ? (
          <div className="flex flex-col items-center justify-center py-12">
            <div className="flex gap-1 mb-4">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.1s]" />
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
            <p className="text-zinc-400">Loading agent details...</p>
          </div>
        ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            updateMutation.mutate();
          }}
          className="space-y-5"
        >
          {/* Identity */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <User className="w-4 h-4 inline mr-2" />
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Agent name"
                required
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <Tag className="w-4 h-4 inline mr-2" />
                Role
              </label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g., Senior Developer"
                required
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              <FileText className="w-4 h-4 inline mr-2" />
              Base Prompt / System Instructions
            </label>
            <textarea
              value={basePrompt}
              onChange={(e) => setBasePrompt(e.target.value)}
              placeholder="Describe the agent's personality, expertise, and how they should behave..."
              rows={4}
              className="w-full px-4 py-3 input-glass rounded-xl resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <Sparkles className="w-4 h-4 inline mr-2" />
                Traits (comma-separated)
              </label>
              <input
                type="text"
                value={traits}
                onChange={(e) => setTraits(e.target.value)}
                placeholder="analytical, creative, thorough"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <Brain className="w-4 h-4 inline mr-2" />
                Specializations (comma-separated)
              </label>
              <input
                type="text"
                value={specializations}
                onChange={(e) => setSpecializations(e.target.value)}
                placeholder="python, architecture, testing"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <MessageSquare className="w-4 h-4 inline mr-2" />
                Communication Style
              </label>
              <select
                value={communicationStyle}
                onChange={(e) => setCommunicationStyle(e.target.value)}
                className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
              >
                <option value="formal">Formal</option>
                <option value="balanced">Balanced</option>
                <option value="technical">Technical</option>
                <option value="friendly">Friendly</option>
                <option value="concise">Concise</option>
                <option value="detailed">Detailed</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <Languages className="w-4 h-4 inline mr-2" />
                Languages (comma-separated)
              </label>
              <input
                type="text"
                value={languages}
                onChange={(e) => setLanguages(e.target.value)}
                placeholder="French, English"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">
              <Quote className="w-4 h-4 inline mr-2" />
              Motto
            </label>
            <input
              type="text"
              value={motto}
              onChange={(e) => setMotto(e.target.value)}
              placeholder="A guiding principle or catchphrase"
              className="w-full px-4 py-3 input-glass rounded-xl"
            />
          </div>

          {/* Model Configuration */}
          <div className="border-t border-white/5 pt-5 space-y-4">
            <h3 className="text-sm font-medium text-zinc-300 flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              Model Configuration
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Server className="w-4 h-4 inline mr-2" />
                  Provider
                </label>
                <select
                  value={selectedProviderId || ''}
                  onChange={(e) => {
                    setSelectedProviderId(e.target.value ? Number(e.target.value) : null);
                    setSelectedModelId(null);
                  }}
                  className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
                >
                  <option value="">All providers</option>
                  {providersData?.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Cpu className="w-4 h-4 inline mr-2" />
                  Model
                </label>
                <select
                  value={selectedModelId || ''}
                  onChange={(e) => setSelectedModelId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
                >
                  <option value="">Select model...</option>
                  {filteredModels.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.model_alias || m.model_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  <Thermometer className="w-4 h-4 inline mr-2" />
                  Temperature: {temperature.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-zinc-500 mt-1">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-2">
                  Max Tokens (optional)
                </label>
                <input
                  type="number"
                  value={maxTokens || ''}
                  onChange={(e) => setMaxTokens(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="Default from model"
                  className="w-full px-4 py-3 input-glass rounded-xl"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-white/5">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-3 text-zinc-300 hover:text-white hover:bg-white/5 rounded-xl transition-all font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending || !name || !role}
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
        )}
      </div>
    </div>
  );
}

export function Agents() {
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: agents.list,
  });

  const deleteMutation = useMutation({
    mutationFn: agents.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      if (selectedAgent) {
        setSelectedAgent(null);
      }
    },
  });

  // On mobile, hide sidebar when an agent is selected
  const handleSelectAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    // Hide sidebar on small screens when selecting
    if (window.innerWidth < 768) {
      setShowSidebar(false);
    }
  };

  return (
    <div className="h-full flex flex-col md:flex-row gap-4 md:gap-6">
      {/* Mobile header with toggle */}
      <div className="md:hidden flex items-center justify-between">
        <button
          onClick={() => setShowSidebar(!showSidebar)}
          className="flex items-center gap-2 px-3 py-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
        >
          <Users className="w-4 h-4" />
          <span className="text-sm">{showSidebar ? 'Hide' : 'Show'} Agents</span>
          {selectedAgent && !showSidebar && (
            <span className="text-purple-400 font-medium ml-1">{selectedAgent.name}</span>
          )}
        </button>
        <button
          onClick={() => setShowCreateModal(true)}
          className="p-2 btn-gradient rounded-xl"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Agents list - collapsible on mobile */}
      <div className={`${showSidebar ? 'flex' : 'hidden'} md:flex w-full md:w-80 flex-shrink-0 flex-col`}>
        <div className="hidden md:flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">Agents</h1>
            <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="p-2.5 btn-gradient rounded-xl"
          >
            <Plus className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-3 pr-2 max-h-[30vh] md:max-h-none">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="flex gap-1 justify-center">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.1s]" />
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:0.2s]" />
              </div>
            </div>
          ) : data?.agents.length === 0 ? (
            <div className="empty-state p-8 text-center">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center mx-auto mb-4">
                <Bot className="w-7 h-7 text-zinc-500" />
              </div>
              <p className="text-zinc-500 mb-3">No agents yet</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="text-purple-400 hover:text-purple-300 transition-colors font-medium"
              >
                Create your first agent
              </button>
            </div>
          ) : (
            data?.agents.map((agent) => (
              <AgentCard
                key={agent.id}
                agent={agent}
                isSelected={selectedAgent?.id === agent.id}
                onSelect={() => handleSelectAgent(agent)}
                onDelete={() => deleteMutation.mutate(agent.id)}
                onEdit={() => setEditingAgent(agent)}
              />
            ))
          )}
        </div>
      </div>

      {/* Chat panel with WebSocket streaming */}
      <div className={`${!showSidebar || selectedAgent ? 'flex' : 'hidden md:flex'} flex-1 glass-card rounded-2xl overflow-hidden min-h-[50vh] md:min-h-0`}>
        {selectedAgent ? (
          <StreamingChatPanel key={selectedAgent.id} agent={selectedAgent} />
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-purple-500/20 flex items-center justify-center mx-auto mb-6">
                <MessageSquare className="w-10 h-10 text-purple-400" />
              </div>
              <p className="text-lg font-medium text-zinc-400">Select an agent to start chatting</p>
              <p className="text-sm text-zinc-600 mt-2">Choose from the list on the left</p>
            </div>
          </div>
        )}
      </div>

      <CreateAgentModal isOpen={showCreateModal} onClose={() => setShowCreateModal(false)} />
      <EditAgentModal
        agent={editingAgent}
        isOpen={editingAgent !== null}
        onClose={() => setEditingAgent(null)}
      />
    </div>
  );
}

export default Agents;
