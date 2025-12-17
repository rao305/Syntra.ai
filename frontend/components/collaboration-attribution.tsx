import { Bot, Brain, CheckCircle, ChevronDown, Code, FileText, Search } from 'lucide-react';
import React from 'react';

interface ModelContribution {
    model: string;
    role: string;
    provider: string;
    icon?: string;
}

interface CollaborationAttributionProps {
    contributions: ModelContribution[];
    isCollapsed?: boolean;
    onToggle?: () => void;
}

const MODEL_ICONS: Record<string, string> = {
    'gpt-4o': '🟢',
    'gpt-4': '🟢',
    'gemini': '🔵',
    'gemini-2.0-flash': '🔵',
    'gemini-2.5-flash': '🔵',
    'claude': '🟣',
    'perplexity': '🟠',
    'sonar': '🟠',
};

const ROLE_ICONS: Record<string, any> = {
    'analyst': Brain,
    'researcher': Search,
    'creator': Code,
    'critic': CheckCircle,
    'synthesizer': FileText,
    'judge': CheckCircle,
};

const getModelIcon = (model: string): string => {
    const lowerModel = (model || '').toLowerCase();
    for (const [key, icon] of Object.entries(MODEL_ICONS)) {
        if (lowerModel.includes(key)) return icon;
    }
    return '🤖';
};

export const CollaborationAttribution: React.FC<CollaborationAttributionProps> = ({
    contributions,
    isCollapsed = true,
    onToggle,
}) => {
    if (!contributions || contributions.length === 0) return null;

    return (
        <div className="collaboration-attribution mb-4 bg-zinc-900/30 rounded-lg border border-zinc-800/50 overflow-hidden">
            {/* Compact View */}
            <button
                onClick={onToggle}
                className="w-full flex items-center justify-between px-3 py-2 text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/30 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="flex -space-x-1.5">
                        {contributions.slice(0, 4).map((c, i) => (
                            <span
                                key={i}
                                className="relative z-10 w-5 h-5 flex items-center justify-center bg-zinc-900 rounded-full ring-2 ring-zinc-900 text-xs shadow-sm"
                                title={c.model}
                            >
                                {getModelIcon(c.model)}
                            </span>
                        ))}
                        {contributions.length > 4 && (
                            <span className="relative z-0 w-5 h-5 flex items-center justify-center bg-zinc-800 text-zinc-400 rounded-full ring-2 ring-zinc-900 text-[9px] font-medium">
                                +{contributions.length - 4}
                            </span>
                        )}
                    </div>
                    <div className="flex flex-col items-start">
                        <span className="font-medium text-zinc-300">
                            {contributions.length} models collaborated
                        </span>
                    </div>
                </div>
                <ChevronDown
                    className={`w-3.5 h-3.5 transition-transform duration-200 ${!isCollapsed ? 'rotate-180' : ''}`}
                />
            </button>

            {/* Expanded View */}
            {!isCollapsed && (
                <div className="p-3 bg-zinc-900/50 border-t border-zinc-800/50 space-y-3 animate-in slide-in-from-top-2 duration-200">
                    <div className="text-[10px] text-zinc-500 uppercase font-semibold tracking-wider px-1">
                        Collaboration Pipeline
                    </div>
                    <div className="space-y-2">
                        {contributions.map((contribution, index) => {
                            const RoleIcon = ROLE_ICONS[contribution.role.toLowerCase()] || Bot;

                            return (
                                <div
                                    key={index}
                                    className="flex items-center gap-3 p-2 rounded-md bg-zinc-800/30 border border-zinc-800/50 hover:bg-zinc-800/50 transition-colors"
                                >
                                    <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center bg-zinc-900 rounded-full border border-zinc-700/50 text-sm">
                                        {getModelIcon(contribution.model)}
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2">
                                            <span className="text-xs font-medium text-zinc-200 truncate">
                                                {contribution.model}
                                            </span>
                                            <div className="h-0.5 w-0.5 rounded-full bg-zinc-600" />
                                            <div className="flex items-center gap-1 text-xs text-zinc-400">
                                                <RoleIcon className="w-3 h-3" />
                                                <span className="capitalize">{contribution.role}</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
};

