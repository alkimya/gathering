// Models & Providers management page with Web3 dark theme

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Server,
  Cpu,
  Plus,
  Trash2,
  DollarSign,
  Zap,
  Eye,
  Brain,
  Loader2,
  X,
  ChevronDown,
  ChevronRight,
  Globe,
  HardDrive,
  Sparkles,
} from 'lucide-react';
import { providers, models } from '../services/api';
import type { Provider, Model } from '../types';

function ProviderCard({
  provider,
  isExpanded,
  onToggle,
  modelCount,
  onDelete,
}: {
  provider: Provider;
  isExpanded: boolean;
  onToggle: () => void;
  modelCount: number;
  onDelete: () => void;
}) {
  const providerColors: Record<string, string> = {
    anthropic: 'from-orange-500 to-amber-500',
    openai: 'from-emerald-500 to-teal-500',
    deepseek: 'from-blue-500 to-cyan-500',
    mistral: 'from-purple-500 to-pink-500',
    google: 'from-red-500 to-orange-500',
    ollama: 'from-zinc-500 to-zinc-600',
  };

  const gradient = providerColors[provider.name] || 'from-indigo-500 to-purple-500';

  return (
    <div className="glass-card rounded-xl overflow-hidden">
      <div
        onClick={onToggle}
        className="p-4 cursor-pointer hover:bg-white/5 transition-all flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center`}>
            {provider.is_local ? (
              <HardDrive className="w-5 h-5 text-white" />
            ) : (
              <Globe className="w-5 h-5 text-white" />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white capitalize">{provider.name}</h3>
            <p className="text-xs text-zinc-500">
              {modelCount} model{modelCount !== 1 ? 's' : ''} • {provider.is_local ? 'Local' : 'Cloud'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          {isExpanded ? (
            <ChevronDown className="w-5 h-5 text-zinc-500" />
          ) : (
            <ChevronRight className="w-5 h-5 text-zinc-500" />
          )}
        </div>
      </div>
    </div>
  );
}

function ModelRow({ model, onDelete }: { model: Model; onDelete: () => void }) {
  return (
    <tr className="border-b border-white/5 hover:bg-white/5 transition-all">
      <td className="px-4 py-3">
        <div>
          <p className="font-medium text-white">{model.model_alias || model.model_name}</p>
          <p className="text-xs text-zinc-500">{model.model_name}</p>
        </div>
      </td>
      <td className="px-4 py-3 text-sm text-zinc-400">
        {model.context_window ? `${(model.context_window / 1000).toFixed(0)}K` : '-'}
      </td>
      <td className="px-4 py-3 text-sm text-zinc-400">
        {model.max_output ? `${(model.max_output / 1000).toFixed(0)}K` : '-'}
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          {model.pricing_in != null && (
            <span className="text-xs text-emerald-400">${Number(model.pricing_in).toFixed(2)}</span>
          )}
          <span className="text-zinc-600">/</span>
          {model.pricing_out != null && (
            <span className="text-xs text-amber-400">${Number(model.pricing_out).toFixed(2)}</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          {model.extended_thinking && (
            <span className="badge-info px-2 py-0.5 text-xs rounded-full flex items-center gap-1">
              <Brain className="w-3 h-3" />
              Think
            </span>
          )}
          {model.vision && (
            <span className="badge-success px-2 py-0.5 text-xs rounded-full flex items-center gap-1">
              <Eye className="w-3 h-3" />
              Vision
            </span>
          )}
          {model.function_calling && (
            <span className="badge px-2 py-0.5 text-xs rounded-full flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Tools
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <button
          onClick={onDelete}
          className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </td>
    </tr>
  );
}

function AddProviderModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [name, setName] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('');
  const [isLocal, setIsLocal] = useState(false);
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: () => providers.create({ name, api_base_url: apiBaseUrl || undefined, is_local: isLocal }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      onClose();
      setName('');
      setApiBaseUrl('');
      setIsLocal(false);
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="glass-card rounded-2xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center glow-purple">
              <Server className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Add Provider</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="space-y-5"
        >
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Provider Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., anthropic, openai"
              required
              className="w-full px-4 py-3 input-glass rounded-xl"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">API Base URL</label>
            <input
              type="url"
              value={apiBaseUrl}
              onChange={(e) => setApiBaseUrl(e.target.value)}
              placeholder="https://api.example.com"
              className="w-full px-4 py-3 input-glass rounded-xl"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="isLocal"
              checked={isLocal}
              onChange={(e) => setIsLocal(e.target.checked)}
              className="w-4 h-4 rounded bg-zinc-800 border-zinc-700"
            />
            <label htmlFor="isLocal" className="text-sm text-zinc-300">
              Local provider (e.g., Ollama)
            </label>
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
              disabled={createMutation.isPending}
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {createMutation.isPending ? 'Adding...' : 'Add Provider'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AddModelModal({
  isOpen,
  onClose,
  providersList,
}: {
  isOpen: boolean;
  onClose: () => void;
  providersList: Provider[];
}) {
  const [providerId, setProviderId] = useState<number>(0);
  const [modelName, setModelName] = useState('');
  const [modelAlias, setModelAlias] = useState('');
  const [pricingIn, setPricingIn] = useState('');
  const [pricingOut, setPricingOut] = useState('');
  const [contextWindow, setContextWindow] = useState('');
  const [maxOutput, setMaxOutput] = useState('');
  const [extendedThinking, setExtendedThinking] = useState(false);
  const [vision, setVision] = useState(false);
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: () =>
      models.create({
        provider_id: providerId,
        model_name: modelName,
        model_alias: modelAlias || undefined,
        pricing_in: pricingIn ? parseFloat(pricingIn) : undefined,
        pricing_out: pricingOut ? parseFloat(pricingOut) : undefined,
        context_window: contextWindow ? parseInt(contextWindow) : undefined,
        max_output: maxOutput ? parseInt(maxOutput) : undefined,
        extended_thinking: extendedThinking,
        vision: vision,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
      onClose();
      setModelName('');
      setModelAlias('');
      setPricingIn('');
      setPricingOut('');
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50 p-4">
      <div className="glass-card rounded-2xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center glow-blue">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <h2 className="text-xl font-bold text-white">Add Model</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-lg transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="space-y-5"
        >
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Provider</label>
            <select
              value={providerId}
              onChange={(e) => setProviderId(Number(e.target.value))}
              required
              className="w-full px-4 py-3 input-glass rounded-xl appearance-none cursor-pointer"
            >
              <option value={0}>Select provider...</option>
              {providersList.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Model Name (API)</label>
              <input
                type="text"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                placeholder="claude-sonnet-4-5-20250514"
                required
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Display Alias</label>
              <input
                type="text"
                value={modelAlias}
                onChange={(e) => setModelAlias(e.target.value)}
                placeholder="Sonnet 4.5"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <DollarSign className="w-3 h-3 inline mr-1" />
                Price In ($/1M)
              </label>
              <input
                type="number"
                step="0.01"
                value={pricingIn}
                onChange={(e) => setPricingIn(e.target.value)}
                placeholder="3.00"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">
                <DollarSign className="w-3 h-3 inline mr-1" />
                Price Out ($/1M)
              </label>
              <input
                type="number"
                step="0.01"
                value={pricingOut}
                onChange={(e) => setPricingOut(e.target.value)}
                placeholder="15.00"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Context Window</label>
              <input
                type="number"
                value={contextWindow}
                onChange={(e) => setContextWindow(e.target.value)}
                placeholder="200000"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Max Output</label>
              <input
                type="number"
                value={maxOutput}
                onChange={(e) => setMaxOutput(e.target.value)}
                placeholder="16000"
                className="w-full px-4 py-3 input-glass rounded-xl"
              />
            </div>
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={extendedThinking}
                onChange={(e) => setExtendedThinking(e.target.checked)}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700"
              />
              <Brain className="w-4 h-4 text-cyan-400" />
              <span className="text-sm text-zinc-300">Extended Thinking</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={vision}
                onChange={(e) => setVision(e.target.checked)}
                className="w-4 h-4 rounded bg-zinc-800 border-zinc-700"
              />
              <Eye className="w-4 h-4 text-emerald-400" />
              <span className="text-sm text-zinc-300">Vision</span>
            </label>
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
              disabled={createMutation.isPending || !providerId}
              className="flex-1 btn-gradient px-4 py-3 rounded-xl disabled:opacity-50 font-medium"
            >
              {createMutation.isPending ? 'Adding...' : 'Add Model'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function Models() {
  const [expandedProvider, setExpandedProvider] = useState<number | null>(null);
  const [showAddProvider, setShowAddProvider] = useState(false);
  const [showAddModel, setShowAddModel] = useState(false);
  const [includeDeprecated, setIncludeDeprecated] = useState(false);
  const queryClient = useQueryClient();

  const { data: providersData, isLoading: loadingProviders } = useQuery({
    queryKey: ['providers'],
    queryFn: providers.list,
  });

  const { data: modelsData, isLoading: loadingModels } = useQuery({
    queryKey: ['models', includeDeprecated],
    queryFn: () => models.list(undefined, includeDeprecated),
  });

  const deleteProviderMutation = useMutation({
    mutationFn: providers.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] });
    },
  });

  const deleteModelMutation = useMutation({
    mutationFn: models.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
  });

  const getModelsForProvider = (providerId: number) => {
    return modelsData?.models.filter((m) => m.provider_id === providerId) || [];
  };

  const isLoading = loadingProviders || loadingModels;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Models & Providers</h1>
          <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-zinc-400">
            <input
              type="checkbox"
              checked={includeDeprecated}
              onChange={(e) => setIncludeDeprecated(e.target.checked)}
              className="w-4 h-4 rounded bg-zinc-800 border-zinc-700"
            />
            Show deprecated
          </label>
          <button
            onClick={() => setShowAddProvider(true)}
            className="px-4 py-2.5 glass-card hover:bg-white/10 rounded-xl text-sm font-medium text-zinc-300 flex items-center gap-2 transition-all"
          >
            <Server className="w-4 h-4" />
            Add Provider
          </button>
          <button
            onClick={() => setShowAddModel(true)}
            className="px-4 py-2.5 btn-gradient rounded-xl text-sm font-medium flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Model
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
              <Server className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{providersData?.total || 0}</p>
              <p className="text-xs text-zinc-500">Providers</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{modelsData?.total || 0}</p>
              <p className="text-xs text-zinc-500">Models</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {modelsData?.models.filter((m) => m.extended_thinking).length || 0}
              </p>
              <p className="text-xs text-zinc-500">With Thinking</p>
            </div>
          </div>
        </div>
        <div className="glass-card rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
              <Eye className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {modelsData?.models.filter((m) => m.vision).length || 0}
              </p>
              <p className="text-xs text-zinc-500">With Vision</p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {providersData?.providers.map((provider) => {
            const providerModels = getModelsForProvider(provider.id);
            const isExpanded = expandedProvider === provider.id;
            // Use model_count from API (from provider table) or filtered models length
            const modelCount = provider.model_count ?? providerModels.length;

            return (
              <div key={provider.id} className="space-y-2">
                <ProviderCard
                  provider={provider}
                  isExpanded={isExpanded}
                  onToggle={() => setExpandedProvider(isExpanded ? null : provider.id)}
                  modelCount={modelCount}
                  onDelete={() => deleteProviderMutation.mutate(provider.id)}
                />

                {isExpanded && providerModels.length > 0 && (
                  <div className="ml-6 glass-card rounded-xl overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-white/10 bg-white/5">
                          <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                            Model
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                            Context
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                            Max Out
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                            Price (In/Out)
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-zinc-400 uppercase tracking-wider">
                            Capabilities
                          </th>
                          <th className="px-4 py-3 w-12"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {providerModels.map((model) => (
                          <ModelRow
                            key={model.id}
                            model={model}
                            onDelete={() => deleteModelMutation.mutate(model.id)}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {isExpanded && providerModels.length === 0 && (
                  <div className="ml-6 glass-card rounded-xl p-8 text-center">
                    <p className="text-zinc-500">No models for this provider</p>
                    <button
                      onClick={() => setShowAddModel(true)}
                      className="mt-2 text-purple-400 hover:text-purple-300 text-sm font-medium"
                    >
                      Add a model
                    </button>
                  </div>
                )}
              </div>
            );
          })}

          {providersData?.providers.length === 0 && (
            <div className="glass-card rounded-2xl p-12 text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-zinc-700 to-zinc-800 flex items-center justify-center mx-auto mb-4">
                <Server className="w-8 h-8 text-zinc-500" />
              </div>
              <p className="text-zinc-400 mb-3">No providers configured</p>
              <button
                onClick={() => setShowAddProvider(true)}
                className="text-purple-400 hover:text-purple-300 font-medium"
              >
                Add your first provider
              </button>
            </div>
          )}
        </div>
      )}

      <AddProviderModal isOpen={showAddProvider} onClose={() => setShowAddProvider(false)} />
      <AddModelModal
        isOpen={showAddModel}
        onClose={() => setShowAddModel(false)}
        providersList={providersData?.providers || []}
      />
    </div>
  );
}

export default Models;
