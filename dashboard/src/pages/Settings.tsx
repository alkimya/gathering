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
} from 'lucide-react';
import { settings } from '../services/api';

// Provider icons/colors
const providerConfig: Record<string, { color: string; name: string }> = {
  anthropic: { color: 'text-orange-400', name: 'Anthropic (Claude)' },
  openai: { color: 'text-emerald-400', name: 'OpenAI' },
  deepseek: { color: 'text-blue-400', name: 'DeepSeek' },
  ollama: { color: 'text-purple-400', name: 'Ollama (Local)' },
};

// API Key Input with visibility toggle
function ApiKeyInput({
  value,
  onChange,
  placeholder,
  isConfigured,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  isConfigured: boolean;
}) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={isConfigured ? '••••••••••••' : placeholder}
        className="w-full px-3 py-2 pr-10 input-glass rounded-lg font-mono text-sm"
      />
      <button
        type="button"
        onClick={() => setShow(!show)}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-zinc-400 hover:text-white transition-colors"
      >
        {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
      </button>
    </div>
  );
}

// Provider Card
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
  };
  onUpdate: (updates: Record<string, string>) => void;
}) {
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState(data.default_model || '');
  const [baseUrl, setBaseUrl] = useState(data.base_url || '');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const config = providerConfig[provider];

  const handleSave = () => {
    const updates: Record<string, string> = {};
    if (apiKey) updates.api_key = apiKey;
    if (model !== data.default_model) updates.default_model = model;
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
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Key className={`w-5 h-5 ${config.color}`} />
          <h3 className="font-semibold text-white">{config.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          {data.is_configured ? (
            <span className="flex items-center gap-1 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
              <CheckCircle2 className="w-3 h-3" />
              Configured
            </span>
          ) : (
            <span className="flex items-center gap-1 px-2 py-1 bg-zinc-500/20 text-zinc-400 text-xs rounded-full">
              <AlertCircle className="w-3 h-3" />
              Not configured
            </span>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {/* API Key (not for Ollama) */}
        {provider !== 'ollama' && (
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">API Key</label>
            <ApiKeyInput
              value={apiKey}
              onChange={setApiKey}
              placeholder={`sk-${provider}-...`}
              isConfigured={data.is_configured}
            />
            {data.api_key && (
              <p className="text-xs text-zinc-500 mt-1">Current: {data.api_key}</p>
            )}
          </div>
        )}

        {/* Base URL (Ollama only) */}
        {provider === 'ollama' && (
          <div>
            <label className="block text-sm font-medium text-zinc-300 mb-2">Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:11434"
              className="w-full px-3 py-2 input-glass rounded-lg text-sm"
            />
          </div>
        )}

        {/* Default Model */}
        <div>
          <label className="block text-sm font-medium text-zinc-300 mb-2">Default Model</label>
          <input
            type="text"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder={
              provider === 'anthropic'
                ? 'claude-sonnet-4-5'
                : provider === 'openai'
                ? 'gpt-4'
                : provider === 'deepseek'
                ? 'deepseek-coder'
                : 'llama3.2'
            }
            className="w-full px-3 py-2 input-glass rounded-lg text-sm"
          />
        </div>

        {/* Test Result */}
        {testResult && (
          <div
            className={`p-3 rounded-lg text-sm ${
              testResult.success
                ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                : 'bg-red-500/10 border border-red-500/20 text-red-400'
            }`}
          >
            <div className="flex items-center gap-2">
              {testResult.success ? (
                <CheckCircle2 className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )}
              {testResult.message}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-2 px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg text-sm transition-colors"
          >
            {testing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <TestTube2 className="w-4 h-4" />
            )}
            Test
          </button>
          <button
            onClick={handleSave}
            disabled={!apiKey && model === data.default_model && baseUrl === data.base_url}
            className="flex items-center gap-2 px-3 py-2 btn-gradient rounded-xl text-sm disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
        </div>
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
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
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white">PostgreSQL</h3>
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
