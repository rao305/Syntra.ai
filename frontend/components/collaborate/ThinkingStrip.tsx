"use client";

import React, { useEffect, useState } from "react";
import { usePhaseCollaboration, Phase } from "@/hooks/use-phase-collaboration";
import { PHASE_LABELS, StanceCount } from "@/types/collaborate-events";

interface ThinkingStripProps {
  isVisible: boolean;
}

// Add custom animations via CSS
const animationStyle = `
  @keyframes slideInDown {
    from {
      opacity: 0;
      transform: translateY(-20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes pulse-scale {
    0%, 100% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.2);
      opacity: 0.8;
    }
  }

  @keyframes progress-shimmer {
    0% {
      background-position: -1000px 0;
    }
    100% {
      background-position: 1000px 0;
    }
  }

  .animate-slide-in {
    animation: slideInDown 0.5s ease-out;
  }

  .animate-pulse-scale {
    animation: pulse-scale 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  .phase-enter-0 {
    animation: slideInDown 0.5s ease-out 0s;
  }
  .phase-enter-1 {
    animation: slideInDown 0.5s ease-out 0.15s backwards;
  }
  .phase-enter-2 {
    animation: slideInDown 0.5s ease-out 0.3s backwards;
  }
  .phase-enter-3 {
    animation: slideInDown 0.5s ease-out 0.45s backwards;
  }
  .phase-enter-4 {
    animation: slideInDown 0.5s ease-out 0.6s backwards;
  }
`;

export function ThinkingStrip({ isVisible }: ThinkingStripProps) {
  const { phases, currentPhaseIndex, currentStage } = usePhaseCollaboration();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    // Inject animation styles
    const style = document.createElement("style");
    style.textContent = animationStyle;
    document.head.appendChild(style);
    return () => style.remove();
  }, []);

  if (!isVisible || !mounted) return null;

  const progressPercentage = currentPhaseIndex >= 0 ? ((currentPhaseIndex + 1) / 5) * 100 : 0;

  return (
    <div className="w-full bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30 border border-blue-200 dark:border-blue-800 rounded-lg p-6 space-y-4 animate-slide-in shadow-sm">
      {/* Header with animated icon */}
      <div className="flex items-center gap-3">
        <div className="relative h-6 w-6">
          <div className="absolute inset-0 bg-blue-600 dark:bg-blue-400 rounded-full opacity-20 animate-pulse-scale" />
          <div className="animate-spin h-6 w-6 text-blue-600 dark:text-blue-400 relative z-10">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-50">
            Multi-Model Collaboration in Progress
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {currentStage ? currentStage.loadingMessage : "Synthesizing insights from 5 AI models..."}
          </p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-blue-700 dark:from-blue-400 dark:via-blue-500 dark:to-blue-600 transition-all duration-300 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Phases with staggered animations */}
      <div className="space-y-2">
        {phases.map((phase, idx) => (
          <div key={phase.phase} className={`phase-enter-${idx}`}>
            <PhaseStep
              phase={phase}
              index={idx}
              isActive={idx === currentPhaseIndex}
              isCompleted={phase.status === "completed"}
            />
          </div>
        ))}
      </div>

      {/* Summary Stats with better styling */}
      <div className="pt-3 border-t border-blue-200 dark:border-blue-800">
        <div className="flex items-center justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-400">
              <span>Phase {Math.max(1, currentPhaseIndex + 1)}</span>
              <span className="text-slate-400 dark:text-slate-500">/</span>
              <span>5</span>
              <div className="h-1.5 flex-1 bg-slate-200 dark:bg-slate-700 rounded-full ml-2">
                <div
                  className="h-full bg-blue-600 dark:bg-blue-400 rounded-full transition-all duration-300"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>
          </div>
          <span className="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">
            <div className="h-2 w-2 rounded-full bg-blue-600 dark:bg-blue-400 animate-pulse" />
            Live
          </span>
        </div>
      </div>
    </div>
  );
}

interface PhaseStepProps {
  phase: Phase;
  index: number;
  isActive: boolean;
  isCompleted: boolean;
}

function PhaseStep({ phase, index, isActive, isCompleted }: PhaseStepProps) {
  const getStatusIcon = () => {
    if (isCompleted) {
      return (
        <div className="h-6 w-6 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0 ring-2 ring-green-300 dark:ring-green-700 ring-offset-2 dark:ring-offset-slate-900">
          <svg className="h-4 w-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      );
    }

    if (isActive) {
      return (
        <div className="relative h-6 w-6 flex items-center justify-center flex-shrink-0">
          {/* Outer glow ring */}
          <div className="absolute inset-0 rounded-full bg-blue-600 dark:bg-blue-400 opacity-30 animate-pulse" />
          {/* Middle ring with animation */}
          <div className="absolute inset-0.5 rounded-full border-2 border-blue-600 dark:border-blue-400 opacity-50" style={{
            animation: "spin 2s linear infinite"
          }} />
          {/* Inner dot */}
          <div className="h-2.5 w-2.5 rounded-full bg-blue-600 dark:bg-blue-400 relative z-10 animate-pulse-scale" />
        </div>
      );
    }

    return (
      <div className={`h-6 w-6 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
        isActive
          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-50"
          : "bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-400"
      }`}>
        <span className="text-xs font-semibold">{index + 1}</span>
      </div>
    );
  };

  return (
    <div className={`flex gap-3 transition-all duration-300 ${
      isActive ? "opacity-100" : "opacity-75 hover:opacity-90"
    }`}>
      {getStatusIcon()}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className={`text-sm font-medium transition-colors duration-300 ${
            isActive
              ? "text-slate-900 dark:text-slate-50 font-semibold"
              : "text-slate-700 dark:text-slate-300"
          }`}>
            {PHASE_LABELS[phase.phase]}
          </span>
          {isCompleted && phase.model && (
            <span className="text-xs text-slate-500 dark:text-slate-400 animate-fade-in">
              {phase.model}
              {phase.latency_ms && ` • ${phase.latency_ms}ms`}
            </span>
          )}
          {isActive && phase.council_summary && (
            <div className="animate-slide-in">
              <CouncilSummaryBadge summary={phase.council_summary} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CouncilSummaryBadge({ summary }: { summary: StanceCount }) {
  const total = summary.agree + summary.disagree + summary.mixed;
  const agreePercentage = total > 0 ? Math.round((summary.agree / total) * 100) : 0;

  return (
    <div className="flex items-center gap-1 text-xs">
      <span className="inline-flex items-center gap-0.5 px-2 py-1 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
        <span>✓</span>
        <span>{agreePercentage}%</span>
      </span>
      {summary.mixed > 0 && (
        <span className="inline-flex items-center gap-0.5 px-2 py-1 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300">
          <span>◆</span>
          <span>{summary.mixed}</span>
        </span>
      )}
      {summary.disagree > 0 && (
        <span className="inline-flex items-center gap-0.5 px-2 py-1 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300">
          <span>✗</span>
          <span>{summary.disagree}</span>
        </span>
      )}
    </div>
  );
}
