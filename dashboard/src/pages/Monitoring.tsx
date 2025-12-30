// System Monitoring page - Metrics, health checks, and alerts

import { useState, useEffect } from 'react';
import {
  BarChart3,
  Cpu,
  HardDrive,
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Clock,
  Database,
  Server,
  Zap,
  MemoryStick,
} from 'lucide-react';

interface SystemMetrics {
  cpu: {
    percent: number;
    count: number;
    frequency_mhz: number | null;
  };
  memory: {
    total_gb: number;
    available_gb: number;
    used_gb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
  };
  load_average: {
    '1min': number;
    '5min': number;
    '15min': number;
  };
  uptime_seconds: number;
}

interface HealthCheck {
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  value?: number | string;
  message?: string;
  lastCheck: string;
}

// Données de démo
const generateMetrics = (): SystemMetrics => ({
  cpu: {
    percent: 35 + Math.random() * 30,
    count: 8,
    frequency_mhz: 3200,
  },
  memory: {
    total_gb: 32,
    available_gb: 12 + Math.random() * 5,
    used_gb: 15 + Math.random() * 5,
    percent: 50 + Math.random() * 20,
  },
  disk: {
    total_gb: 500,
    used_gb: 180,
    free_gb: 320,
    percent: 36,
  },
  load_average: {
    '1min': 1.5 + Math.random(),
    '5min': 1.2 + Math.random() * 0.5,
    '15min': 1.0 + Math.random() * 0.3,
  },
  uptime_seconds: 345600 + Math.random() * 10000,
});

const generateHealthChecks = (): HealthCheck[] => [
  {
    name: 'API Server',
    status: 'healthy',
    message: 'Responding normally',
    lastCheck: new Date().toISOString(),
  },
  {
    name: 'Database',
    status: 'healthy',
    message: 'PostgreSQL connected',
    lastCheck: new Date().toISOString(),
  },
  {
    name: 'Redis Cache',
    status: 'healthy',
    message: 'Connected',
    lastCheck: new Date().toISOString(),
  },
  {
    name: 'LLM Provider',
    status: 'healthy',
    message: 'Anthropic API responding',
    lastCheck: new Date().toISOString(),
  },
  {
    name: 'Memory Usage',
    status: 'warning',
    value: '68%',
    message: 'Above 60% threshold',
    lastCheck: new Date().toISOString(),
  },
  {
    name: 'Disk Space',
    status: 'healthy',
    value: '36%',
    message: 'Sufficient space',
    lastCheck: new Date().toISOString(),
  },
];

interface Alert {
  id: string;
  level: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  timestamp: string;
  acknowledged: boolean;
}

const generateAlerts = (): Alert[] => [
  {
    id: '1',
    level: 'warning',
    title: 'High Memory Usage',
    message: 'Memory usage exceeded 60% threshold',
    timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    acknowledged: false,
  },
  {
    id: '2',
    level: 'info',
    title: 'Agent Sophie Idle',
    message: 'Agent has been idle for 30 minutes',
    timestamp: new Date(Date.now() - 30 * 60000).toISOString(),
    acknowledged: true,
  },
];

function MetricCard({
  title,
  value,
  unit,
  percent,
  icon,
  color,
}: {
  title: string;
  value: number | string;
  unit?: string;
  percent?: number;
  icon: React.ReactNode;
  color: string;
}) {
  const getBarColor = (pct: number) => {
    if (pct >= 90) return 'bg-red-500';
    if (pct >= 70) return 'bg-amber-500';
    if (pct >= 50) return 'bg-yellow-500';
    return 'bg-emerald-500';
  };

  return (
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-zinc-400 text-sm">{title}</p>
          <p className="text-3xl font-bold text-white mt-1">
            {typeof value === 'number' ? value.toFixed(1) : value}
            {unit && <span className="text-lg text-zinc-500 ml-1">{unit}</span>}
          </p>
        </div>
        <div className={`p-3 rounded-xl ${color}`}>{icon}</div>
      </div>

      {percent !== undefined && (
        <div className="mt-4">
          <div className="flex justify-between text-xs text-zinc-500 mb-1">
            <span>Usage</span>
            <span>{percent.toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-zinc-700/50 rounded-full overflow-hidden">
            <div
              className={`h-full ${getBarColor(percent)} transition-all duration-500`}
              style={{ width: `${Math.min(percent, 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function HealthCheckItem({ check }: { check: HealthCheck }) {
  const statusConfig = {
    healthy: { icon: <CheckCircle className="w-5 h-5" />, color: 'text-emerald-400', bg: 'bg-emerald-500/20' },
    warning: { icon: <AlertTriangle className="w-5 h-5" />, color: 'text-amber-400', bg: 'bg-amber-500/20' },
    critical: { icon: <AlertTriangle className="w-5 h-5" />, color: 'text-red-400', bg: 'bg-red-500/20' },
  };

  const config = statusConfig[check.status];

  return (
    <div className="flex items-center justify-between p-4 glass-card rounded-xl">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${config.bg}`}>
          <span className={config.color}>{config.icon}</span>
        </div>
        <div>
          <p className="font-medium text-zinc-200">{check.name}</p>
          <p className="text-xs text-zinc-500">{check.message}</p>
        </div>
      </div>
      <div className="text-right">
        {check.value && <p className={`font-mono ${config.color}`}>{check.value}</p>}
        <p className="text-xs text-zinc-600">
          {new Date(check.lastCheck).toLocaleTimeString('fr-FR')}
        </p>
      </div>
    </div>
  );
}

function AlertItem({
  alert,
  onAcknowledge,
}: {
  alert: Alert;
  onAcknowledge: (id: string) => void;
}) {
  const levelConfig = {
    info: { icon: <Zap className="w-4 h-4" />, color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500/30' },
    warning: { icon: <AlertTriangle className="w-4 h-4" />, color: 'text-amber-400', bg: 'bg-amber-500/20', border: 'border-amber-500/30' },
    critical: { icon: <AlertTriangle className="w-4 h-4" />, color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
  };

  const config = levelConfig[alert.level];

  return (
    <div className={`p-4 rounded-xl border ${config.border} ${config.bg} ${alert.acknowledged ? 'opacity-50' : ''}`}>
      <div className="flex items-start gap-3">
        <span className={config.color}>{config.icon}</span>
        <div className="flex-1">
          <p className={`font-medium ${config.color}`}>{alert.title}</p>
          <p className="text-sm text-zinc-400 mt-1">{alert.message}</p>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-zinc-500">
              {new Date(alert.timestamp).toLocaleString('fr-FR')}
            </span>
            {!alert.acknowledged && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="text-xs text-zinc-400 hover:text-white transition-colors"
              >
                Acknowledge
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export function Monitoring() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Charger les données
  const loadData = () => {
    setMetrics(generateMetrics());
    setHealthChecks(generateHealthChecks());
    setAlerts(generateAlerts());
    setLastUpdate(new Date());
  };

  useEffect(() => {
    loadData();
  }, []);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleAcknowledge = (alertId: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === alertId ? { ...a, acknowledged: true } : a))
    );
  };

  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full" />
      </div>
    );
  }

  const activeAlerts = alerts.filter((a) => !a.acknowledged);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-purple-400" />
            Monitoring
          </h1>
          <p className="text-zinc-400 mt-1">
            System health and performance metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Auto-refresh toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-colors ${
              autoRefresh
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                : 'bg-zinc-700/50 text-zinc-400 border border-zinc-600'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                autoRefresh ? 'bg-emerald-400 animate-pulse' : 'bg-zinc-500'
              }`}
            />
            Auto-refresh
          </button>

          {/* Manual refresh */}
          <button
            onClick={loadData}
            className="p-2 glass-card rounded-xl text-zinc-400 hover:text-white transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Quick stats bar */}
      <div className="flex items-center gap-4 text-sm text-zinc-400">
        <span className="flex items-center gap-2">
          <Clock className="w-4 h-4" />
          Uptime: {formatUptime(metrics.uptime_seconds)}
        </span>
        <span>•</span>
        <span>Last update: {lastUpdate.toLocaleTimeString('fr-FR')}</span>
        {activeAlerts.length > 0 && (
          <>
            <span>•</span>
            <span className="text-amber-400 flex items-center gap-1">
              <AlertTriangle className="w-4 h-4" />
              {activeAlerts.length} active alert{activeAlerts.length > 1 ? 's' : ''}
            </span>
          </>
        )}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU"
          value={metrics.cpu.percent}
          unit="%"
          percent={metrics.cpu.percent}
          icon={<Cpu className="w-6 h-6 text-cyan-400" />}
          color="bg-cyan-500/20"
        />
        <MetricCard
          title="Memory"
          value={metrics.memory.used_gb}
          unit={`/ ${metrics.memory.total_gb} GB`}
          percent={metrics.memory.percent}
          icon={<MemoryStick className="w-6 h-6 text-purple-400" />}
          color="bg-purple-500/20"
        />
        <MetricCard
          title="Disk"
          value={metrics.disk.used_gb}
          unit={`/ ${metrics.disk.total_gb} GB`}
          percent={metrics.disk.percent}
          icon={<HardDrive className="w-6 h-6 text-blue-400" />}
          color="bg-blue-500/20"
        />
        <MetricCard
          title="Load Average"
          value={metrics.load_average['1min']}
          icon={<Activity className="w-6 h-6 text-emerald-400" />}
          color="bg-emerald-500/20"
        />
      </div>

      {/* Two columns: Health Checks & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health Checks */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-purple-400" />
              Health Checks
            </h2>
            <span className="text-xs text-zinc-500">
              {healthChecks.filter((h) => h.status === 'healthy').length}/{healthChecks.length} healthy
            </span>
          </div>
          <div className="space-y-3">
            {healthChecks.map((check) => (
              <HealthCheckItem key={check.name} check={check} />
            ))}
          </div>
        </div>

        {/* Alerts */}
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              Alerts
            </h2>
            {activeAlerts.length > 0 && (
              <span className="px-2 py-1 text-xs rounded-full bg-amber-500/20 text-amber-400">
                {activeAlerts.length} active
              </span>
            )}
          </div>
          <div className="space-y-3">
            {alerts.length === 0 ? (
              <div className="text-center py-8 text-zinc-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-2 text-emerald-400" />
                <p>No alerts</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <AlertItem
                  key={alert.id}
                  alert={alert}
                  onAcknowledge={handleAcknowledge}
                />
              ))
            )}
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="glass-card rounded-2xl p-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-purple-400" />
          System Information
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-xs text-zinc-500">CPU Cores</p>
            <p className="text-lg font-mono text-zinc-200">{metrics.cpu.count}</p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">CPU Frequency</p>
            <p className="text-lg font-mono text-zinc-200">
              {metrics.cpu.frequency_mhz ? `${metrics.cpu.frequency_mhz} MHz` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Free Memory</p>
            <p className="text-lg font-mono text-zinc-200">
              {metrics.memory.available_gb.toFixed(1)} GB
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-500">Free Disk</p>
            <p className="text-lg font-mono text-zinc-200">{metrics.disk.free_gb} GB</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Monitoring;
