// Settings page - API keys and application configuration

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Key,
  Database,
  Server,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Eye,
  EyeOff,
  RefreshCw,
  Save,
  TestTube2,
  Loader2,
  Cpu,
  Brain,
  ExternalLink,
  Layers,
  Settings2,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { settings } from '../services/api';
import type { SettingsModelInfo } from '../types';

// Provider icons/colors
const providerConfig: Record<string, { color: string; name: string }> = {
  anthropic: { color: 'text-orange-400', name: 'Anthropic (Claude)' },
  openai: { color: 'text-emerald-400', name: 'OpenAI' },
  deepseek: { color: 'text-blue-400', name: 'DeepSeek' },
  mistral: { color: 'text-amber-400', name: 'Mistral AI' },
  google: { color: 'text-red-400', name: 'Google (Gemini)' },
  ollama: { color: 'text-purple-400', name: 'Ollama (Local)' },
};

// API Key Input with visibility toggle
function ApiKeyInput({
  value,
  onChange,
  placeholder,
  isConfigured,
  providerName,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  isConfigured: boolean;
  providerName: string;
}) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isConfigured ? '••••••••••••' : placeholder}
        aria-label={`API key for ${providerName}`}
        className="w-full px-3 py-2 pr-10 input-glass rounded-lg font-mono text-sm"
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        aria-label={show ? 'Hide API key' : 'Show API key'}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-zinc-400 hover:text-white transition-colors"
      >
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  );
}

// Provider Card - Compact version
function ProviderCard({
  provider,
  data,
  onUpdate,
}: {
  provider: string;
  data: {
    api_key?: string;
    default_model?: string;
    base_url?: string;
    is_configured: boolean;
    models: SettingsModelInfo[];
  };
  onUpdate: (updates: Record<string, string>) => void;
}) {
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(data.base_url || '');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const config = providerConfig[provider];

  const handleSave = () => {
    const updates: Record<string, string> = {};
    if (apiKey) updates.api_key = apiKey;
    if (provider === 'ollama' && baseUrl !== data.base_url) updates.base_url = baseUrl;
    if (Object.keys(updates).length > 0) {
      onUpdate(updates);
      setApiKey(''); // Clear after save
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await settings.testProvider(provider);
      setTestResult(result);
    } catch (e) {
      setTestResult({ success: false, message: (e as Error).message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="glass-card rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Key className={`w-4 h-4 ${config.color}`} />
          <h3 className="font-medium text-white text-sm">{config.name}</h3>
        </div>
        {data.is_configured ? (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            OK
          </span>
        ) : (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-zinc-500/20 text-zinc-400 text-xs rounded-full">
            <AlertCircle className="w-3 h-3" />
            Not set
          </span>
        )}
      </div>

      <div className="space-y-3">
        {/* API Key (not for Ollama) */}
        {provider !== 'ollama' && (
          <div>
            <ApiKeyInput
              value={apiKey}
              onChange={setApiKey}
              placeholder={`sk-${provider}-...`}
              isConfigured={data.is_configured}
              providerName={config.name}
            />
            {data.api_key && (
              <p className="text-xs text-zinc-500 mt-1">{data.api_key}</p>
            )}
          </div>
        )}

        {/* Base URL (Ollama only) */}
        {provider === 'ollama' && (
          <input
            type="text"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://localhost:11434"
            aria-label="Ollama base URL"
            className="w-full px-3 py-2 input-glass rounded-lg text-sm"
          />
        )}

        {/* Test Result */}
        {testResult && (
          <div
            className={`p-2 rounded-lg text-xs ${
              testResult.success
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}
          >
            <div className="flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="w-3 h-3" />
              ) : (
                <XCircle className="w-3 h-3" />
              )}
              {testResult.message}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-1.5 px-2.5 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-xs transition-colors"
          >
            {testing ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <TestTube2 className="w-3 h-3" />
            )}
            Test
          </button>
          <button
            onClick={handleSave}
            disabled={!apiKey && baseUrl === data.base_url}
            className="flex items-center gap-1.5 px-2.5 py-1.5 btn-gradient rounded-lg text-xs disabled:opacity-50"
          >
            <Save className="w-3 h-3" />
            Save
          </button>
        </div>

        {/* Models from database */}
        {data.models.length > 0 && (
          <div className="pt-3 border-t border-white/5">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-zinc-500 flex items-center gap-1">
                <Cpu className="w-3 h-3" />
                {data.models.length} model{data.models.length > 1 ? 's' : ''} available
              </span>
              <Link
                to="/models"
                className="text-xs text-purple-400 hover:text-purple-300 flex items-center gap-1"
              >
                Manage
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
            <div className="flex flex-wrap gap-1">
              {data.models.slice(0, 3).map((model) => (
                <span
                  key={model.id}
                  className="px-2 py-0.5 bg-zinc-800/50 text-zinc-400 text-xs rounded flex items-center gap-1"
                  title={model.model_name}
                >
                  {model.model_alias || model.model_name.split('/').pop()?.split('-').slice(0, 2).join('-')}
                  {model.vision && <Eye className="w-3 h-3 text-emerald-400" />}
                  {model.extended_thinking && <Brain className="w-3 h-3 text-cyan-400" />}
                </span>
              ))}
              {data.models.length > 3 && (
                <span className="px-2 py-0.5 bg-zinc-800/50 text-zinc-500 text-xs rounded">
                  +{data.models.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Main Settings Page
export function Settings() {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settings.get(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ provider, updates }: { provider: string; updates: Record<string, string> }) =>
      settings.updateProvider(provider, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const updateAppMutation = useMutation({
    mutationFn: (updates: { debug?: boolean; log_level?: string }) =>
      settings.updateApplication(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const updateDbMutation = useMutation({
    mutationFn: (updates: { pool_size?: number; max_overflow?: number }) =>
      settings.updateDatabase(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card rounded-xl p-8 text-center">
        <AlertCircle className="w-8 h-8 text-red-400 mx-auto mb-4" />
        <p className="text-red-400">{(error as Error).message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-zinc-400 mt-1">Configure API providers and application settings</p>
      </div>

      {/* Providers Section */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Key className="w-5 h-5 text-purple-400" />
          LLM Providers
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {data?.providers &&
            Object.entries(data.providers).map(([provider, providerData]) => (
              <ProviderCard
                key={provider}
                provider={provider}
                data={providerData}
                onUpdate={(updates) => updateMutation.mutate({ provider, updates })}
              />
            ))}
        </div>
      </section>

      {/* Database Section */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Database className="w-5 h-5 text-purple-400" />
          Database
        </h2>
        <div className="glass-card rounded-xl p-6 space-y-6">
          {/* Connection Info */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white">PostgreSQL Connection</h3>
              {data?.database?.is_connected ? (
                <span className="flex items-center gap-1 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                  <CheckCircle2 className="w-3 h-3" />
                  Connected
                </span>
              ) : (
                <span className="flex items-center gap-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs rounded-full">
                  <XCircle className="w-3 h-3" />
                  Disconnected
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <p className="text-xs text-zinc-500">Host</p>
                <p className="text-sm text-white font-mono">{data?.database?.host}</p>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <p className="text-xs text-zinc-500">Port</p>
                <p className="text-sm text-white font-mono">{data?.database?.port}</p>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <p className="text-xs text-zinc-500">Database</p>
                <p className="text-sm text-white font-mono">{data?.database?.name}</p>
              </div>
              <div className="bg-zinc-800/50 rounded-lg p-3">
                <p className="text-xs text-zinc-500">User</p>
                <p className="text-sm text-white font-mono">{data?.database?.user}</p>
              </div>
            </div>
          </div>

          {/* Connection Pool */}
          <div className="pt-4 border-t border-white/5">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 className="w-4 h-4 text-cyan-400" />
              <h3 className="font-semibold text-white text-sm">Connection Pool</h3>
              <span className="text-xs text-zinc-500">(requires restart)</span>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Pool Size</label>
                <select
                  value={data?.database?.pool_size || 5}
                  onChange={(e) => updateDbMutation.mutate({ pool_size: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 input-glass rounded-lg text-sm"
                >
                  {[1, 2, 3, 5, 10, 15, 20, 30, 50].map((n) => (
                    <option key={n} value={n}>{n} connections</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-zinc-500 mb-1">Max Overflow</label>
                <select
                  value={data?.database?.max_overflow || 10}
                  onChange={(e) => updateDbMutation.mutate({ max_overflow: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 input-glass rounded-lg text-sm"
                >
                  {[0, 5, 10, 20, 30, 50, 100].map((n) => (
                    <option key={n} value={n}>{n} extra</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* PostgreSQL Extensions */}
          {data?.database?.extensions && data.database.extensions.length > 0 && (
            <div className="pt-4 border-t border-white/5">
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-4 h-4 text-purple-400" />
                <h3 className="font-semibold text-white text-sm">Active Extensions</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {data.database.extensions.map((ext) => (
                  <span
                    key={ext}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium ${
                      ext === 'vector' || ext === 'pgvector'
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                        : ext === 'uuid-ossp'
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                    }`}
                  >
                    {ext}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Application Section */}
      <section>
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-purple-400" />
          Application
        </h2>
        <div className="glass-card rounded-xl p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Environment */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Environment</label>
              <div className="px-3 py-2 bg-zinc-800/50 rounded-lg text-sm">
                <span
                  className={`px-2 py-0.5 rounded ${
                    data?.application?.environment === 'production'
                      ? 'bg-red-500/20 text-red-400'
                      : data?.application?.environment === 'staging'
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-emerald-500/20 text-emerald-400'
                  }`}
                >
                  {data?.application?.environment}
                </span>
              </div>
            </div>

            {/* Debug */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Debug Mode</label>
              <button
                onClick={() => updateAppMutation.mutate({ debug: !data?.application?.debug })}
                className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                  data?.application?.debug
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-700'
                }`}
              >
                {data?.application?.debug ? 'Enabled' : 'Disabled'}
              </button>
            </div>

            {/* Log Level */}
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-2">Log Level</label>
              <select
                value={data?.application?.log_level || 'INFO'}
                onChange={(e) => updateAppMutation.mutate({ log_level: e.target.value })}
                className="w-full px-3 py-2 input-glass rounded-lg text-sm"
              >
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* Info */}
      <div className="text-center text-sm text-zinc-500">
        <p>Settings are stored in the .env file and persist across restarts.</p>
        <p>Some changes may require a server restart to take effect.</p>
      </div>
    </div>
  );
}

export default Settings;
