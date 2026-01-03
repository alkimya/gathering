import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Wrench,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Filter,
  Search,
  Zap,
  Terminal,
  Globe,
  Cpu,
  MessageSquare,
  FileText,
  Image,
  Cloud,
  LayoutGrid,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { tools } from '../services/api';
import { Badge } from './ui/Badge';
import { Card } from './ui/Card';
import type { AgentToolInfo } from '../types';

interface AgentToolsPanelProps {
  agentId: number;
  agentName?: string;
}

// Category icons and colors
const categoryConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; label: string }> = {
  core: { icon: Zap, color: 'text-purple-400', label: 'Core' },
  code: { icon: Terminal, color: 'text-cyan-400', label: 'Code' },
  system: { icon: Cpu, color: 'text-red-400', label: 'System' },
  web: { icon: Globe, color: 'text-blue-400', label: 'Web' },
  ai: { icon: Cpu, color: 'text-emerald-400', label: 'AI/ML' },
  communication: { icon: MessageSquare, color: 'text-amber-400', label: 'Communication' },
  productivity: { icon: FileText, color: 'text-pink-400', label: 'Productivity' },
  media: { icon: Image, color: 'text-orange-400', label: 'Media' },
  cloud: { icon: Cloud, color: 'text-sky-400', label: 'Cloud' },
  gathering: { icon: LayoutGrid, color: 'text-violet-400', label: 'GatheRing' },
};

function getCategoryConfig(category: string) {
  return categoryConfig[category] || { icon: Wrench, color: 'text-zinc-400', label: category };
}

export function AgentToolsPanel({ agentId }: AgentToolsPanelProps) {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set(['core', 'code']));

  // Fetch agent tools
  const { data: toolsData, isLoading, error } = useQuery({
    queryKey: ['agent-tools', agentId],
    queryFn: () => tools.getAgentTools(agentId),
    enabled: !!agentId,
  });

  // Toggle tool mutation
  const toggleMutation = useMutation({
    mutationFn: ({ skillName, isEnabled }: { skillName: string; isEnabled: boolean }) =>
      tools.toggleTool(agentId, skillName, isEnabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-tools', agentId] });
    },
  });

  // Enable/disable all mutations
  const enableAllMutation = useMutation({
    mutationFn: (category?: string) => tools.enableAll(agentId, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-tools', agentId] });
    },
  });

  const disableAllMutation = useMutation({
    mutationFn: (category?: string) => tools.disableAll(agentId, category),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-tools', agentId] });
    },
  });

  // Group tools by category
  const toolsByCategory = useMemo(() => {
    if (!toolsData?.tools) return {};

    const filtered = toolsData.tools.filter((tool) => {
      const matchesSearch =
        !searchQuery ||
        tool.skill_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.skill_display_name?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = !selectedCategory || tool.skill_category === selectedCategory;
      return matchesSearch && matchesCategory;
    });

    return filtered.reduce(
      (acc, tool) => {
        const category = tool.skill_category || 'general';
        if (!acc[category]) acc[category] = [];
        acc[category].push(tool);
        return acc;
      },
      {} as Record<string, AgentToolInfo[]>
    );
  }, [toolsData?.tools, searchQuery, selectedCategory]);

  // Get unique categories
  const categories = useMemo(() => {
    if (!toolsData?.tools) return [];
    const cats = new Set(toolsData.tools.map((t) => t.skill_category || 'general'));
    return Array.from(cats).sort();
  }, [toolsData?.tools]);

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const handleToggleTool = (tool: AgentToolInfo) => {
    toggleMutation.mutate({ skillName: tool.skill_name, isEnabled: !tool.is_enabled });
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center gap-2 text-zinc-400">
          <Wrench className="w-5 h-5 animate-spin" />
          <span>Loading tools...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 text-red-400">
          <XCircle className="w-5 h-5" />
          <span>Failed to load tools</span>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Wrench className="w-5 h-5 text-purple-400" />
            <h3 className="font-semibold text-white">Agent Tools</h3>
            <Badge variant="purple" size="sm">
              {toolsData?.enabled_count || 0}/{toolsData?.total_count || 0}
            </Badge>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => enableAllMutation.mutate(selectedCategory || undefined)}
              disabled={enableAllMutation.isPending}
              className="px-2.5 py-1 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded-lg transition-colors disabled:opacity-50"
            >
              Enable All
            </button>
            <button
              onClick={() => disableAllMutation.mutate(selectedCategory || undefined)}
              disabled={disableAllMutation.isPending}
              className="px-2.5 py-1 text-xs font-medium text-zinc-400 bg-zinc-500/10 hover:bg-zinc-500/20 rounded-lg transition-colors disabled:opacity-50"
            >
              Disable All
            </button>
          </div>
        </div>

        {/* Search and filter */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tools..."
              className="w-full pl-8 pr-3 py-1.5 text-sm bg-zinc-800/50 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:border-purple-500"
            />
          </div>
          <div className="relative">
            <select
              value={selectedCategory || ''}
              onChange={(e) => setSelectedCategory(e.target.value || null)}
              className="appearance-none pl-7 pr-8 py-1.5 text-sm bg-zinc-800/50 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
            >
              <option value="">All Categories</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {getCategoryConfig(cat).label}
                </option>
              ))}
            </select>
            <Filter className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Tools list grouped by category */}
      <div className="max-h-[500px] overflow-y-auto">
        {Object.keys(toolsByCategory).length === 0 ? (
          <div className="p-6 text-center text-zinc-500">
            No tools match your search criteria
          </div>
        ) : (
          Object.entries(toolsByCategory)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([category, categoryTools]) => {
              const config = getCategoryConfig(category);
              const CategoryIcon = config.icon;
              const isExpanded = expandedCategories.has(category);
              const enabledCount = categoryTools.filter((t) => t.is_enabled).length;

              return (
                <div key={category} className="border-b border-zinc-800/50 last:border-b-0">
                  {/* Category header */}
                  <button
                    onClick={() => toggleCategory(category)}
                    className="w-full flex items-center justify-between p-3 hover:bg-zinc-800/30 transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      {isExpanded ? (
                        <ChevronDown className="w-4 h-4 text-zinc-500" />
                      ) : (
                        <ChevronRight className="w-4 h-4 text-zinc-500" />
                      )}
                      <CategoryIcon className={`w-4 h-4 ${config.color}`} />
                      <span className="font-medium text-white text-sm">{config.label}</span>
                      <Badge variant="default" size="sm">
                        {enabledCount}/{categoryTools.length}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          enableAllMutation.mutate(category);
                        }}
                        className="p-1 text-emerald-400 hover:bg-emerald-500/20 rounded transition-colors"
                        title={`Enable all ${config.label} tools`}
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          disableAllMutation.mutate(category);
                        }}
                        className="p-1 text-zinc-400 hover:bg-zinc-500/20 rounded transition-colors"
                        title={`Disable all ${config.label} tools`}
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </div>
                  </button>

                  {/* Category tools */}
                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-1">
                      {categoryTools.map((tool) => (
                        <ToolItem
                          key={tool.skill_id}
                          tool={tool}
                          onToggle={() => handleToggleTool(tool)}
                          isToggling={toggleMutation.isPending}
                        />
                      ))}
                    </div>
                  )}
                </div>
              );
            })
        )}
      </div>
    </Card>
  );
}

interface ToolItemProps {
  tool: AgentToolInfo;
  onToggle: () => void;
  isToggling: boolean;
}

function ToolItem({ tool, onToggle, isToggling }: ToolItemProps) {
  return (
    <div
      className={`flex items-center justify-between p-2 rounded-lg transition-colors ${
        tool.is_enabled ? 'bg-purple-500/10' : 'bg-zinc-800/30'
      }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        <button
          onClick={onToggle}
          disabled={isToggling}
          className={`relative w-10 h-5 rounded-full transition-colors ${
            tool.is_enabled ? 'bg-purple-500' : 'bg-zinc-700'
          } disabled:opacity-50`}
        >
          <span
            className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
              tool.is_enabled ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-medium text-white truncate">
              {tool.skill_display_name || tool.skill_name}
            </span>
            {tool.is_dangerous && (
              <span title="This tool requires extra caution">
                <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0" />
              </span>
            )}
          </div>
          {tool.required_permissions.length > 0 && (
            <div className="flex items-center gap-1 mt-0.5">
              {tool.required_permissions.slice(0, 3).map((perm) => (
                <span
                  key={perm}
                  className="text-[10px] px-1.5 py-0.5 bg-zinc-700/50 text-zinc-400 rounded"
                >
                  {perm}
                </span>
              ))}
              {tool.required_permissions.length > 3 && (
                <span className="text-[10px] text-zinc-500">
                  +{tool.required_permissions.length - 3}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      {tool.usage_count > 0 && (
        <div className="text-xs text-zinc-500 flex-shrink-0">
          {tool.usage_count} uses
        </div>
      )}
    </div>
  );
}

export default AgentToolsPanel;
