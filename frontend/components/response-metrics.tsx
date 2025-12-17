import { BarChart, Bot, FileText, Zap } from 'lucide-react';
import React from 'react';

interface ResponseMetricsProps {
    durationMs?: number;
    modelsUsed?: number;
    tokenCount?: number;
    stagesCompleted?: number;
}

export const ResponseMetrics: React.FC<ResponseMetricsProps> = ({
    durationMs,
    modelsUsed,
    tokenCount,
    stagesCompleted,
}) => {
    const metrics = [
        durationMs && {
            icon: Zap,
            value: durationMs < 1000 ? `${durationMs}ms` : `${(durationMs / 1000).toFixed(1)}s`,
            label: 'latency',
        },
        modelsUsed && {
            icon: Bot,
            value: modelsUsed,
            label: modelsUsed === 1 ? 'model' : 'models',
        },
        tokenCount && {
            icon: FileText,
            value: tokenCount > 1000 ? `${(tokenCount / 1000).toFixed(1)}k` : tokenCount,
            label: 'tokens',
        },
        stagesCompleted && {
            icon: BarChart,
            value: stagesCompleted,
            label: 'stages',
        },
    ].filter(Boolean);

    if (metrics.length === 0) return null;

    return (
        <div className="response-metrics flex items-center gap-4 mt-4 pt-3 border-t border-zinc-800/50">
            {metrics.map((metric: any, index) => (
                <div
                    key={index}
                    className="flex items-center gap-1.5 text-xs text-zinc-500"
                >
                    <metric.icon className="w-3 h-3" />
                    <span className="text-zinc-400 font-medium">{metric.value}</span>
                    <span>{metric.label}</span>
                </div>
            ))}
        </div>
    );
};

