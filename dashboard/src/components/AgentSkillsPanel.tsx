import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Puzzle,
  ChevronDown,
  ChevronRight,
  Wrench,
  XCircle,
  Loader2,
  Power,
} from 'lucide-react';
import { agents } from '../services/api';
import { Badge } from './ui/Badge';
import { Card } from './ui/Card';
import type { SkillDetail } from '../types';

interface AgentSkillsPanelProps {
  agentId: number;
  agentName?: string;
}

// Skill icon and color config
const skillConfig: Record<string, { color: string; bgColor: string }> = {
  filesystem: { color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  git: { color: 'text-orange-400', bgColor: 'bg-orange-500/20' },
  code: { color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  shell: { color: 'text-red-400', bgColor: 'bg-red-500/20' },
  goals: { color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
  pipelines: { color: 'text-cyan-400', bgColor: 'bg-cyan-500/20' },
  tasks: { color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
  schedules: { color: 'text-pink-400', bgColor: 'bg-pink-500/20' },
  circles: { color: 'text-violet-400', bgColor: 'bg-violet-500/20' },
  ai: { color: 'text-fuchsia-400', bgColor: 'bg-fuchsia-500/20' },
  analysis: { color: 'text-teal-400', bgColor: 'bg-teal-500/20' },
  docs: { color: 'text-lime-400', bgColor: 'bg-lime-500/20' },
  deploy: { color: 'text-rose-400', bgColor: 'bg-rose-500/20' },
  http: { color: 'text-sky-400', bgColor: 'bg-sky-500/20' },
  database: { color: 'text-indigo-400', bgColor: 'bg-indigo-500/20' },
  test: { color: 'text-green-400', bgColor: 'bg-green-500/20' },
  web: { color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  projects: { color: 'text-yellow-400', bgColor: 'bg-yellow-500/20' },
};

function getSkillConfig(skillName: string) {
  return skillConfig[skillName] || { color: 'text-zinc-400', bgColor: 'bg-zinc-500/20' };
}

export function AgentSkillsPanel({ agentId }: AgentSkillsPanelProps) {
  const queryClient = useQueryClient();
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());
  const [showAddSkill, setShowAddSkill] = useState(false);

  // Fetch agent skills
  const { data: skillsData, isLoading, error } = useQuery({
    queryKey: ['agent-skills', agentId],
    queryFn: () => agents.getSkills(agentId),
    enabled: !!agentId,
  });

  // Add skill mutation
  const addSkillMutation = useMutation({
    mutationFn: (skillName: string) => agents.addSkill(agentId, skillName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
      setShowAddSkill(false);
    },
  });

  // Remove skill mutation
  const removeSkillMutation = useMutation({
    mutationFn: (skillName: string) => agents.removeSkill(agentId, skillName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agent-skills', agentId] });
    },
  });

  const toggleSkillExpand = (skillName: string) => {
    setExpandedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillName)) {
        next.delete(skillName);
      } else {
        next.add(skillName);
      }
      return next;
    });
  };

  // Get all skills (loaded + available to add)
  const loadedSkills = skillsData?.loaded_skills || [];
  const availableSkills = skillsData?.available_skills || [];

  // Build a map of all skills with their enabled status
  const allSkills = availableSkills.map(name => ({
    name,
    isEnabled: loadedSkills.includes(name),
    detail: skillsData?.skill_details.find(d => d.name === name),
  }));

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center gap-2 text-zinc-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Loading skills...</span>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2 text-red-400">
          <XCircle className="w-5 h-5" />
          <span>Failed to load skills</span>
        </div>
      </Card>
    );
  }

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Puzzle className="w-5 h-5 text-purple-400" />
            <h3 className="font-semibold text-white">Agent Skills</h3>
            <Badge variant="purple" size="sm">
              {loadedSkills.length}/{availableSkills.length} active
            </Badge>
            <Badge variant="default" size="sm">
              {skillsData?.tools_count || 0} tools
            </Badge>
          </div>
          <button
            onClick={() => setShowAddSkill(!showAddSkill)}
            className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
              showAddSkill
                ? 'text-zinc-400 bg-zinc-500/10 hover:bg-zinc-500/20'
                : 'text-purple-400 bg-purple-500/10 hover:bg-purple-500/20'
            }`}
          >
            {showAddSkill ? 'Hide inactive' : 'Show all'}
          </button>
        </div>
      </div>

      {/* Skills list */}
      <div className="max-h-[500px] overflow-y-auto">
        {allSkills.length === 0 ? (
          <div className="p-6 text-center text-zinc-500">
            No skills available
          </div>
        ) : (
          allSkills
            .filter(skill => showAddSkill || skill.isEnabled)
            .sort((a, b) => {
              // Enabled skills first, then alphabetically
              if (a.isEnabled !== b.isEnabled) return a.isEnabled ? -1 : 1;
              return a.name.localeCompare(b.name);
            })
            .map((skill) => (
              <SkillItem
                key={skill.name}
                name={skill.name}
                detail={skill.detail}
                isEnabled={skill.isEnabled}
                isExpanded={expandedSkills.has(skill.name)}
                onToggleExpand={() => toggleSkillExpand(skill.name)}
                onToggleEnabled={() => {
                  if (skill.isEnabled) {
                    removeSkillMutation.mutate(skill.name);
                  } else {
                    addSkillMutation.mutate(skill.name);
                  }
                }}
                isToggling={addSkillMutation.isPending || removeSkillMutation.isPending}
              />
            ))
        )}
      </div>
    </Card>
  );
}

interface SkillItemProps {
  name: string;
  detail?: SkillDetail;
  isEnabled: boolean;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleEnabled: () => void;
  isToggling: boolean;
}

function SkillItem({
  name,
  detail,
  isEnabled,
  isExpanded,
  onToggleExpand,
  onToggleEnabled,
  isToggling
}: SkillItemProps) {
  const config = getSkillConfig(name);

  return (
    <div className={`border-b border-zinc-800/50 last:border-b-0 transition-opacity ${
      isEnabled ? 'opacity-100' : 'opacity-60'
    }`}>
      {/* Skill header */}
      <div className="flex items-center justify-between p-3 hover:bg-zinc-800/30 transition-colors">
        <button
          onClick={onToggleExpand}
          disabled={!isEnabled}
          className="flex items-center gap-2 flex-1 text-left disabled:cursor-default"
        >
          {isEnabled ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-zinc-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-zinc-500" />
            )
          ) : (
            <div className="w-4 h-4" />
          )}
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            isEnabled ? config.bgColor : 'bg-zinc-700/50'
          }`}>
            <Puzzle className={`w-4 h-4 ${isEnabled ? config.color : 'text-zinc-500'}`} />
          </div>
          <div>
            <span className={`font-medium text-sm capitalize ${
              isEnabled ? 'text-white' : 'text-zinc-500'
            }`}>
              {name}
            </span>
            {detail && (
              <p className="text-xs text-zinc-500">
                {detail.description || `${detail.tools_count} tools`}
              </p>
            )}
          </div>
        </button>

        <div className="flex items-center gap-2">
          {isEnabled && detail && (
            <>
              <Badge variant="default" size="sm">
                {detail.tools_count} tools
              </Badge>
              <Badge variant="purple" size="sm">
                v{detail.version}
              </Badge>
            </>
          )}

          {/* Toggle switch */}
          <button
            onClick={onToggleEnabled}
            disabled={isToggling}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              isEnabled ? 'bg-purple-500' : 'bg-zinc-700'
            } disabled:opacity-50`}
            title={isEnabled ? 'Disable skill' : 'Enable skill'}
          >
            {isToggling ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              </div>
            ) : (
              <span
                className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow flex items-center justify-center transition-transform ${
                  isEnabled ? 'translate-x-5' : 'translate-x-0'
                }`}
              >
                <Power className={`w-3 h-3 ${isEnabled ? 'text-purple-500' : 'text-zinc-400'}`} />
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Skill tools (only show if enabled and expanded) */}
      {isEnabled && isExpanded && detail && (
        <div className="px-4 pb-3">
          <div className="p-3 bg-zinc-800/30 rounded-lg">
            <p className="text-xs text-zinc-400 mb-2 flex items-center gap-1">
              <Wrench className="w-3 h-3" />
              Available tools ({detail.tools.length}):
            </p>
            <div className="flex flex-wrap gap-1.5">
              {detail.tools.map((tool) => (
                <span
                  key={tool}
                  className="px-2 py-0.5 text-xs bg-zinc-700/50 text-zinc-300 rounded-md font-mono"
                >
                  {tool}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentSkillsPanel;
